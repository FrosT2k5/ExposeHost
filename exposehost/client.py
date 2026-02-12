import asyncio
import logging
import ssl
import sys
from exposehost.impl import packets
from exposehost import helpers
import threading

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Global ssl context
# ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
# ssl_ctx.check_hostname = False
# ssl_ctx.verify_mode = ssl.CERT_NONE
ssl_ctx = ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH)
ssl_ctx.check_hostname = True
ssl_ctx.verify_mode = ssl.CERT_REQUIRED

"""
Function to:
get status
get url
get port
"""

def loop_thread(loop: asyncio.AbstractEventLoop):
    asyncio.set_event_loop(loop)
    loop.run_forever()


class Client(packets.ProtocolHandler):
    host = None
    port = None
    serverHost = None
    serverPort = None
    protocol = None
    subdomain: str = None
    status: str = 'stopped'            # stopped, connecting, connected, failed
    url: str = None

    def __init__(self, host, port, serverHost, serverPort, protocol, subdomain,
                 auth_enabled=False, auth_user=None, auth_pass=None):
        self.host = host
        self.actual_port = port  # Store original service port
        self.port = port
        self.serverHost = serverHost
        self.serverPort = serverPort
        self.protocol = protocol
        self.subdomain = subdomain
        self.auth_proxy = None
        
        # Store auth configuration for later initialization
        if auth_enabled and protocol == 'http':
            self.auth_proxy_config = {
                'username': auth_user,
                'password': auth_pass,
                'actual_port': port
            }
        else:
            self.auth_proxy_config = None

    def get_status(self):
        return self.status

    def get_url(self):
        return self.url

    def get_port(self):
        return self.serverPort

    async def forward(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        try:
            while True:
                data = await reader.read(4096)
                if not data:
                    break
                writer.write(data)
                await writer.drain()
        except Exception as e:
            logger.error("Error occured at forwarder: %s", e)
        finally:
            writer.close()
            await writer.wait_closed()

    async def forward_tcp(self, connection_id: str):
        # Create a connection with server
        reader, writer = await asyncio.open_connection(self.serverHost, self.serverPort, ssl=ssl_ctx)
        new_conn_handler = packets.ProtocolHandler(reader, writer)

        new_conn_resp_packet = packets.NewConnectionHostResponsePacket()
        new_conn_resp_packet.connection_id = connection_id
        await new_conn_handler.send_packet(new_conn_resp_packet)

        resp = await new_conn_handler.recv(1)

        if not resp == b'\x01':
            logger.debug("Error: Server did not respond with acknowledgement.")
            return 
        
        # After successful server connection, create localhosted service conn
        local_reader, local_writer = await asyncio.open_connection(self.host, self.port)

        # Forward forever
        await asyncio.gather(
            self.forward(reader, local_writer),
            self.forward(local_reader, writer)
        )

    async def server_connect(self):
        # If auth proxy is configured, start it first
        if self.auth_proxy_config:
            from exposehost.auth_proxy import AuthProxyServer
            
            self.auth_proxy = AuthProxyServer(
                self.auth_proxy_config['username'],
                self.auth_proxy_config['password'],
                self.auth_proxy_config['actual_port']
            )
            
            auth_proxy_port = await self.auth_proxy.start()
            logger.info("Auth proxy started on port: %s", auth_proxy_port)
            
            # Replace forwarding port with auth proxy port
            # This is the port that will be forwarded through the tunnel
            self.port = auth_proxy_port
        
        logger.info("Connecting to server %s:%s", self.serverHost, self.serverPort)
        self.status = 'connecting'
        reader, writer = await asyncio.open_connection(self.serverHost, self.serverPort, ssl=ssl_ctx)

        super().__init__(reader, writer)

        # Send Connection Request Packet
        req_packet = packets.TunnelRequestPacket()
        
        req_packet.jwt_token = helpers.random_string(32)
        req_packet.c_session_key = helpers.random_string(32)
        req_packet.port = self.serverPort
        req_packet.subdomain = self.subdomain
        req_packet.protocol = self.protocol
        
        await self.send_packet(req_packet)
        logger.debug("Packet info sent")

        # await self.close()
        # Receive the tunnel response packet
        received_packet = await self.recv_packet()

        if isinstance(received_packet, packets.LoadbalanceResponsePacket):
            new_port = received_packet.new_port
            self.serverPort = new_port
            reader, writer = await asyncio.open_connection(self.serverHost, new_port, ssl=ssl_ctx)

            super().__init__(reader, writer)


            await self.send_packet(req_packet)
            logger.debug("Packet info sent on loadbalanced port: %s", new_port)
            received_packet = await self.recv_packet()


        if isinstance(received_packet, packets.TunnelResponsePacket):
            if received_packet.status == "success":
                self.status = 'connected'
                self.url = received_packet.url
                logger.debug("Tunneling server listening opened port: %s", received_packet.port)
                logger.debug("Test URL: http://localhost:%s", received_packet.port)
                logger.debug("Received URL: %s", received_packet.url)
            else:
                logger.debug("Tunnel server failed to open port, reason: %s", received_packet.error)
                return 

            while True: 
                # Wait for new connection packet, asynchronously 
                new_connection_packet = await self.recv_packet()

                if isinstance(new_connection_packet, packets.NewClientConnectionPacket):
                    # A new connection is received, create new server connection
                    # and forward forever
                    logger.info("Received new packet")
                    logger.debug("Connection ID: %s", new_connection_packet.connection_id)
                    await self.forward_tcp(new_connection_packet.connection_id)

                if isinstance(new_connection_packet, packets.HeartBeatPacket):
                    # logger.debug("Received heartbeat packet from server")
                    # do nothing as packet isn't meant to do anything
                    pass
        
    def start(self):
        loop = asyncio.new_event_loop()
        loop.run_until_complete(self.server_connect())

    def start_non_blocking(self):    
        loop = asyncio.new_event_loop()

        t = threading.Thread(target=loop_thread, args=(loop,), daemon=True)
        t.start()

        return asyncio.run_coroutine_threadsafe(self.server_connect(), loop)