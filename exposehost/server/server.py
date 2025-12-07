import asyncio
import logging
import socket
import ssl
from exposehost.impl import packets
from exposehost.helpers import clean_all_nginx_configs
from exposehost.server import ServerConnection
from exposehost.server.constants import *

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