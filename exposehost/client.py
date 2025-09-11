import asyncio
import binascii
import json
import logging
import os
import socket
import ssl
import sys
from exposehost.impl import packets
from exposehost import helpers

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
        
        # Send Connection Request Packet
        req_packet = packets.TunnelRequestPacket()
        
        req_packet.jwt_token = helpers.random_string(32)
        req_packet.c_session_key = helpers.random_string(32)
        req_packet.port = self.serverPort
        req_packet.subdomain = 'test_hardcoded_val'
        req_packet.protocol = self.protocol

        packet_header = req_packet.pack_data()

        # Send tunnel request packet
        writer.write(packet_header)
        # writer.write()

        logger.debug("Packet info sent")
        await writer.drain()

        # Send the json
        writer.write(req_packet.packet_bytes)
        await writer.drain()

        writer.close()
        await writer.wait_closed()

    def start(self):
        loop = asyncio.new_event_loop()
        loop.run_until_complete(self.server_connect())
        