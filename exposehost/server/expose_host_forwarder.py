from exposehost.impl import packets 
import asyncio
from exposehost.helpers import random_string
from exposehost.server.constants import *
import socket


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
                logger.debug("Closing server: %s", self.expostHostClassInstance.exposed_port)
            await writer.wait_closed()


class ExposeHostForwarder(packets.ProtocolHandler):
    protocol: str = None        # Can be TCP/HTTP (UDP in future)
    exposed_port: int = None
    serverConnectionClassInstance = None
    sock4 = None
    serverSocket: asyncio.Server = None
    tcp_servers: list[TCPProtocolHandler] = []
    sock_name: list = None

    def __init__(self, serverConnectionClassInstance, protocol, exposed_port):
        self.serverConnectionClassInstance = serverConnectionClassInstance
        self.protocol = protocol
        self.exposed_port = exposed_port


    async def handleTCPClientConnection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        client_handler = TCPProtocolHandler(self)
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
        self.sock_name = sock_name
        return sock_name

    async def stop_server(self):
        for client in self.tcp_servers:
            await client.kill_client()

        self.tcp_servers = []

        # Close the forwarder server
        if self.serverSocket:
            logger.debug("Stopped server at port: %s", self.sock_name[1])
            self.serverSocket.close()
        
        # Remove the forwarder instance from the server connection class instance
        self.serverConnectionClassInstance.forwarders.remove(self)