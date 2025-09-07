import asyncio
import logging
import socket
import ssl
import sys

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.info("Starting")

class Server:
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
        logging.debug("Received new connection.")
        header = await reader.read(5)
        connection_type = int.from_bytes(header[0:1], byteorder='big')
        json_length = int.from_bytes(header[1:5], byteorder='big')
        logging.debug("Id: %s, json len: %s", connection_type, json_length)

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


