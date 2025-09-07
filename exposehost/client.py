import asyncio
import logging
import socket
import ssl
import sys

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging.getLogger(__name__)

class Client:
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

    async def server_connect(self):
        ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE


        logger.info("Connecting to server %s:%s", self.serverHost, self.serverPort)
        reader, writer = await asyncio.open_connection(self.serverHost, self.serverPort, ssl=ssl_ctx)
        
        packetID = 1
        packet_length = 222
        # Send 1 for connection
        writer.write(packetID.to_bytes(1, byteorder="big"))
        writer.write(packet_length.to_bytes(4, byteorder="big"))

        logger.debug("Packet info sent")
        await writer.drain()
        writer.close()
        await writer.wait_closed()

    def start(self):
        loop = asyncio.new_event_loop()
        loop.run_until_complete(self.server_connect())
        