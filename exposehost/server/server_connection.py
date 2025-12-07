from exposehost.impl import packets 
from exposehost.server import ExposeHostForwarder
from exposehost.helpers import remove_old_nginx_config, add_new_nginx_config
from exposehost.server.constants import *
import asyncio


class ServerConnection(packets.ProtocolHandler):
    forwarders: list[ExposeHostForwarder]  = [] # List of ExposeHostForwarder Objects
    forwarders_port_mapping: dict[int, ExposeHostForwarder] = {}
    subdomain: str = None
    full_domain: str = None
    c_session_key: str = None
    protocol: str = None                       # for now http/tcp
    exposed_port: int = 0                      # port to be exposed
    serverClassInstance = None

    def __init__(self, subdomain: str, c_session_key: str, protocol: str, exposed_port: int, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, serverClassInstance):
        self.subdomain = subdomain
        self.c_session_key = c_session_key
        self.protocol = protocol
        self.exposed_port = exposed_port
        self.serverClassInstance = serverClassInstance
        super().__init__(reader, writer)


    async def new_tunnel_connection(self, connection_id):
        connection_packet = packets.NewClientConnectionPacket()
        connection_packet.connection_id = connection_id
        connection_packet.c_session_key = self.c_session_key

        # Send new connection packet over the control server
        res = await self.send_packet(connection_packet)
        if not res:
            # The connection is closed, close the server connection too
            await self.kill_server("Connection closed by client")

    
    async def heartbeat_check(self, exposed_server_port):
        while True:
            heartbeatPacket = packets.HeartBeatPacket()
            response = await self.send_packet(heartbeatPacket)
            
            if response == False:
                logger.debug("Sent heartbeat packet to: %s, response: %s", self.subdomain, response)

                # False response means connection was closed, stop forwarder that uses
                # exposed_server_port
                print(self.forwarders, self.forwarders_port_mapping)
                forwarder = self.forwarders_port_mapping.get(exposed_server_port)
                if forwarder:
                    logger.debug("Stopping forwarder at port: %s", exposed_server_port)
                    await forwarder.stop_server()
                    print("Remaining forwarders: ", self.forwarders)
                    self.forwarders_port_mapping.pop(exposed_server_port)

                # Also stop the server connection
                await self.kill_server("Connection closed during heartbeat check")

                return 
            await asyncio.sleep(5)   # wait for 5 seconds
    

    async def kill_server(self, reason: str):
        kill_connection_packet = packets.KillServerConnectionPacket()
        kill_connection_packet.reason = reason

        logger.debug("Closing server connection with: %s Reason: %s", self.full_domain, reason)
        await self.send_packet(kill_connection_packet)
        
        # Remove Server Connection from Server Class Instance
        self.serverClassInstance.clients.remove(self)

        # If protocol is http then just remove the nginx config
        if self.protocol == "http":
            remove_old_nginx_config(self.full_domain)
            CURRENT_DOMAINS.remove(self.full_domain)

        # Close the Connection
        await self.close()


    async def start_control_server(self):
        # Things to do here:
        # Validate subdomain
        # make nginx conf, restart nginx
        # Validate auth
        # Do checks and validation of received info

        forwarder_instance = ExposeHostForwarder(self, self.protocol, 0) 
        tunnel_response_packet = packets.TunnelResponsePacket()
        
        self.full_domain = self.subdomain + "." + DOMAIN_NAME

        if self.full_domain in CURRENT_DOMAINS:
            tunnel_response_packet.status = "error"
            tunnel_response_packet.error = "Subdomain already in use"
            await self.send_packet(tunnel_response_packet)
            await self.close()
            return
        
        CURRENT_DOMAINS.add(self.full_domain)

        # Start the forwarder server
        exposed_server = await forwarder_instance.startExposedServer()
        exposed_port = exposed_server[1]

        # Append the forwarder with exposed_port as key
        self.forwarders.append(forwarder_instance)
        self.forwarders_port_mapping[exposed_port] = forwarder_instance

        tunnel_response_packet.status = "success"
        tunnel_response_packet.port = exposed_port
        tunnel_response_packet.url = self.full_domain

        if self.protocol == "http":
            # Add nginx config if protocol is http
            # add_new_nginx_config restarts nginx internally
            add_new_nginx_config(self.full_domain, exposed_port)
            tunnel_response_packet.url = "https://" + self.full_domain

        # Send successful tunnel resp
        await self.send_packet(tunnel_response_packet)
        logger.debug("Sent tunnel response packet for %s", self.full_domain)
        
        # Start the heartbeat check task, schedule background task
        heartbeat_packet_task = asyncio.create_task(self.heartbeat_check(exposed_port))