import asyncio
import json
import logging
import socket
import ssl
import sys
from exposehost.impl import packets

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.info("Starting")

class Server(packets.ProtocolHandler):
    sock4: socket.socket = None
    ssock4: socket.socket = None
    host: str = None
    port: int = None
    protocol: str = None 

    def __init__(self, host, port):
        self.host = host
        self.port = port
        logger.info("Starting listener on %s:%s", host, port)
    
    async def handleAsyncConnection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        super().__init__(reader, writer)

        logging.debug("Received new connection.")
        packet_id, length = await self.recv_header()

        packet = await self.recv_packet([packet_id, length])

        logger.debug("Received Packet: %s", packet.packet_json)


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
        loop = asyncio.new_event_loop()
        loop.run_until_complete(self.startAsync())
        loop.run_forever()


