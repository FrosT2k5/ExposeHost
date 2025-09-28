import asyncio
import logging
import ssl
import sys
from exposehost.impl import packets
from exposehost import helpers

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Global ssl context
ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE


class Client(packets.ProtocolHandler):
    host = None
    port = None
    serverHost = None
    serverPort = None
    protocol = None

    def __init__(self, host, port, serverHost, serverPort, protocol):
        self.host = host
        self.port = port
        self.serverHost = serverHost
        self.serverPort = serverPort
        self.protocol = protocol

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
        logger.info("Connecting to server %s:%s", self.serverHost, self.serverPort)
        reader, writer = await asyncio.open_connection(self.serverHost, self.serverPort, ssl=ssl_ctx)
        super().__init__(reader, writer)

        # Send Connection Request Packet
        req_packet = packets.TunnelRequestPacket()
        
        req_packet.jwt_token = helpers.random_string(32)
        req_packet.c_session_key = helpers.random_string(32)
        req_packet.port = self.serverPort
        req_packet.subdomain = 'test_hardcoded_val'
        req_packet.protocol = self.protocol
        
        await self.send_packet(req_packet)
        logger.debug("Packet info sent")

        # await self.close()
        # Receive the tunnel response packet
        received_packet = await self.recv_packet()
        
        if isinstance(received_packet, packets.TunnelResponsePacket):
            if received_packet.status == "success":
                logger.debug("Tunneling server listening opened port: %s", received_packet.port)
                logger.debug("Test URL: http://localhost:%s", received_packet.port)
            else:
                logger.debug("Tunnel server failed to open port, reason: %s", received_packet.error)
                return 

            while True: 
                # Wait for new connection packet, asynchronously 
                new_connection_packet = await self.recv_packet()

                if isinstance(new_connection_packet, packets.NewClientConnectionPacket):
                    # A new connection is received, create new server connection
                    # and forward forever
                    await self.forward_tcp(new_connection_packet.connection_id)

    def start(self):
        loop = asyncio.new_event_loop()
        loop.run_until_complete(self.server_connect())
        