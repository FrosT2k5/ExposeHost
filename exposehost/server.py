import asyncio
import json
import logging
import socket
import ssl
import sys
from exposehost.impl import packets
from exposehost.helpers import random_string, \
    add_new_nginx_config, \
    remove_old_nginx_config, \
    clean_all_nginx_configs

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.info("Starting")


MAX_TIMEOUT = 5
DOMAIN_NAME = 'exposehost.local'
CURRENT_DOMAINS: set = set()


class ExposeHostForwarder(packets.ProtocolHandler):
    class TCPProtocolHandler:
        connection_id: str = None
        expostHostClassInstance = None
        is_forwarding: bool = False
        is_host_connected: bool = False
        server_host_reader: asyncio.StreamReader = None
        server_host_writer: asyncio.StreamWriter = None
        client_reader: asyncio.StreamReader = None
        client_writer: asyncio.StreamWriter = None

        def __init__(self, exposeHostClassInstance):
            self.expostHostClassInstance = exposeHostClassInstance
            self.connection_id = random_string(32)
        
        async def forward(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
            try:
                while True:
                    data = await reader.read(4096)
                    if not data:
                        break
                    writer.write(data)
                    await writer.drain()

            finally:
                writer.close()
                await writer.wait_closed()
        
        async def set_host_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
            self.server_host_reader = reader
            self.server_host_writer = writer
            self.is_host_connected = True
            writer.write(b"\x01")
            await writer.drain()

        async def kill_client(self):
            # Kill the client connection
            self.client_writer.close()
            await self.client_writer.wait_closed()

        async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
            self.client_reader = reader
            self.client_writer = writer
            
            try:
                # Send tunnel ID over the control plane
                await self.expostHostClassInstance.serverConnectionClassInstance.new_tunnel_connection(self.connection_id)

                # Wait for 5 seconds for hosting server to connect back
                timeoutCounter = 0
                while self.is_host_connected != True:
                    # Sleep for 10ms until we get a connection from the client
                    await asyncio.sleep(0.01)

                    # If timeout is reached, break and close connection
                    if timeoutCounter >= round(MAX_TIMEOUT / 0.01):
                        return
                    timeoutCounter += 1

                # If we reach here, host connection is set by set_server call
                # Forward forvever
                self.is_forwarding = True
                await asyncio.gather(
                    self.forward(self.client_reader, self.server_host_writer),
                    self.forward(self.server_host_reader, self.client_writer)
                    )
                
            except Exception as e:
                logger.error("Error at TCP Procotol handler: %s", e)
            finally:
                if self.is_host_connected:
                    self.server_host_writer.close()
                    await self.server_host_writer.wait_closed()
                if not self.is_forwarding:
                    # If is_forwarding is not set, means host did not respond,
                    # close the forwarder server
                    await self.expostHostClassInstance.stop_server()
                await writer.wait_closed()

    protocol: str = None        # Can be TCP/HTTP (UDP in future)
    exposed_port: int = None
    serverConnectionClassInstance = None
    sock4 = None
    serverSocket: asyncio.Server = None
    tcp_servers: list[TCPProtocolHandler] = []

    def __init__(self, serverConnectionClassInstance, protocol, exposed_port):
        self.serverConnectionClassInstance = serverConnectionClassInstance
        self.protocol = protocol
        self.exposed_port = exposed_port


    async def handleTCPClientConnection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        client_handler = self.TCPProtocolHandler(self)
        self.tcp_servers.append(client_handler)
        await client_handler.handle_client(reader, writer)

    
    async def startExposedServer(self):
        self.sock4 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock4.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock4.bind(("0.0.0.0", self.exposed_port))
        self.sock4.listen(5)
        self.sock4.setblocking(False)

        self.serverSocket = await asyncio.start_server(self.handleTCPClientConnection, sock=self.sock4)
        sock_name = self.serverSocket.sockets[0].getsockname()
        logger.debug("Started to listen client exposed request on port: %s", sock_name[1])
        return sock_name

    async def stop_server(self):
        for client in self.tcp_servers:
            await client.kill_client()

        self.tcp_servers = []

        # Close the forwarder server
        if self.serverSocket:
            self.serverSocket.close()
        
        # Remove the forwarder instance from the server connection class instance
        self.serverConnectionClassInstance.forwarders.remove(self)

        # Close the control server        
        await self.serverConnectionClassInstance.kill_server("Host Did Not Respond within Timeout.")

        
class ServerConnection(packets.ProtocolHandler):
    forwarders: list[ExposeHostForwarder] = [] # List of ExposeHostForwarder Objects
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
        self.forwarders.append(forwarder_instance)

        tunnel_response_packet.status = "success"
        tunnel_response_packet.port = exposed_server[1] 
        tunnel_response_packet.url = self.full_domain

        if self.protocol == "http":
            # Add nginx config if protocol is http
            # add_new_nginx_config restarts nginx internally
            add_new_nginx_config(self.full_domain, exposed_server[1])
            tunnel_response_packet.url = "https://" + self.full_domain

        # Send successful tunnel resp
        await self.send_packet(tunnel_response_packet)
        logger.debug("Sent tunnel response packet for %s", self.full_domain)


class Server(packets.ProtocolHandler):
    sock4: socket.socket = None
    ssock4: socket.socket = None
    host: str = None
    port: int = None
    protocol: str = None
    clients: list[ServerConnection] = [] 

    def __init__(self, host, port):
        self.host = host
        self.port = port
        logger.info("Starting listener on %s:%s", host, port)
    
    async def handleAsyncConnection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        super().__init__(reader, writer)

        logging.debug("Received new connection.")

        # Receive the packet
        packet = await self.recv_packet()

        logger.debug("Received Packet: %s", packet.packet_json)

        if isinstance(packet, packets.TunnelRequestPacket):
            server_connection = ServerConnection(
                packet.subdomain,
                packet.c_session_key,
                packet.protocol,
                packet.port,
                reader,
                writer,
                self
            )

            self.clients.append(server_connection)
            await server_connection.start_control_server()
            return

        if isinstance(packet, packets.NewConnectionHostResponsePacket):
            for control_server in self.clients:
                for forwarder in control_server.forwarders:
                    for client in forwarder.tcp_servers:
                       if client.connection_id == packet.connection_id:
                           # Received connection request
                           # set_host_connection will send byte 0x01 to
                           # indicate server has been set
                           # after that, all the data from the clients will
                           # be forwarded
                           await client.set_host_connection(reader, writer)
                           return

        # If the packet received is invalid
        # or client is not found, close the connection
        writer.close()    
        await writer.wait_closed()
        return

    async def startAsync(self):
        # Create SSL Context
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain('./exposehost/keys/test_certificate.pem', './exposehost/keys/test_private_key.pem')

        # Create new SSL Socket
        self.sock4 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock4.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock4.bind((self.host, self.port))
        self.sock4.listen(5)
        self.sock4.setblocking(False)

        logger.info("Starting TCP Server Listener at %s", self.port)

        await asyncio.start_server(self.handleAsyncConnection, sock=self.sock4, ssl=context)

    def start(self):
        # Clean existing nginx configs on startup
        clean_all_nginx_configs()

        loop = asyncio.new_event_loop()
        loop.run_until_complete(self.startAsync())
        loop.run_forever()