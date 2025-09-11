import asyncio
import json


class ProtocolHandler:
    reader: asyncio.StreamReader = None
    writer: asyncio.StreamWriter = None

    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self.reader = reader
        self.writer = writer


class Packet:
    packet_id: int = None
    recv_packet_length: int = None           # This is network received packet length
    packet_length: int = None                # This should be original packet length
    packet_json: dict = None
    packet_bytes: bytes = None

    def serialize_json_bytes(self):
        serialized_data = json.dumps(self.packet_json)
        serialized_bytes = serialized_data.encode()
        self.packet_bytes = serialized_bytes
        self.packet_length = len(self.packet_bytes)
        return serialized_bytes
    
    def deserialize_json_bytes(self):
        self.recv_packet_length = len(self.packet_bytes)
        packet_string = self.packet_bytes.decode()
        packet_json = json.loads(packet_string)
        self.packet_json = packet_json
        return packet_json
    
class TunnelRequestPacket(Packet):
    packet_id = 1
    jwt_token: str = None
    subdomain: str = None
    protocol: str = None
    c_session_key: str = None
    port: int = None

    def pack_data(self) -> bytes:
        # Pack the packet and return the header bytes
        self.packet_json = {
            "jwt_token": self.jwt_token,
            "subdomain": self.subdomain,
            "protocol": self.protocol,
            "c_session_key": self.c_session_key,
            "port": self.port
        }
        
        self.serialize_json_bytes()
        header = self.packet_id.to_bytes(1, byteorder="big") + self.packet_length.to_bytes(4, byteorder="big")
        return header
    
    def unpack_data(self, buffer: bytes):
        self.packet_bytes = buffer
        packet_json = self.deserialize_json_bytes()

        self.jwt_token = packet_json['jwt_token']
        self.subdomain = packet_json['subdomain']
        self.protocol = packet_json['protocol']
        self.c_session_key = packet_json['c_session_key']
        self.port = packet_json['port']


packetList = {
    1: TunnelRequestPacket,
}