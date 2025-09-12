import asyncio
import json
        

class Packet:
    packet_id: int = None
    packet_length: int = None
    packet_json: dict = None
    packet_bytes: bytes = None

    def serialize_json_bytes(self):
        serialized_data = json.dumps(self.packet_json)
        serialized_bytes = serialized_data.encode()
        self.packet_bytes = serialized_bytes
        self.packet_length = len(self.packet_bytes)
        return serialized_bytes
    
    def deserialize_json_bytes(self):
        self.packet_length = len(self.packet_bytes)
        packet_string = self.packet_bytes.decode()
        packet_json = json.loads(packet_string)
        self.packet_json = packet_json
        return packet_json
    
    def pack_data() -> int:
        pass

    def unpack_data():
        pass
    

class TunnelRequestPacket(Packet):
    packet_id = 1
    jwt_token: str = None
    subdomain: str = None
    protocol: str = None
    c_session_key: str = None
    port: int = None

    def pack_data(self) -> int:
        # Pack the packet and return the header bytes
        self.packet_json = {
            "jwt_token": self.jwt_token,
            "subdomain": self.subdomain,
            "protocol": self.protocol,
            "c_session_key": self.c_session_key,
            "port": self.port
        }
        
        self.serialize_json_bytes()
        return self.packet_length
    
    def unpack_data(self, buffer: bytes):
        self.packet_bytes = buffer
        packet_json = self.deserialize_json_bytes()

        self.jwt_token = packet_json['jwt_token']
        self.subdomain = packet_json['subdomain']
        self.protocol = packet_json['protocol']
        self.c_session_key = packet_json['c_session_key']
        self.port = packet_json['port']


class ProtocolHandler:
    reader: asyncio.StreamReader = None
    writer: asyncio.StreamWriter = None

    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self.reader = reader
        self.writer = writer

    async def recv(self, size: int):
        data = await self.reader.read(size)
        return data

    async def send(self, bytes: bytes):
        self.writer.write(bytes)
        await self.writer.drain()
        return True
    
    async def close(self):
        self.writer.close()
        await self.writer.wait_closed()
        return True

    async def send_header(self, packet: Packet):
        packet_len: int = packet.pack_data()
        # header = self.packet_id.to_bytes(1, byteorder="big") + self.packet_length.to_bytes(4, byteorder="big")
        # return header
        # pack_len_bytes = self.packet_length.to_bytes(4, byteorder="big")

        pack_id_b = packet.packet_id.to_bytes(1, byteorder="big")
        pack_len_b = packet_len.to_bytes(4, byteorder="big")
        
        header = pack_id_b + pack_len_b
        await self.send(header)

    async def send_packet(self, packet: Packet, send_header = True):
        if send_header:
            await self.send_header(packet)
        
        # convert packet to bytes
        packet.pack_data()
        if packet.packet_length > 0:
            await self.send(packet.packet_bytes)

    async def recv_header(self) -> list[int, int]:
        header = await self.recv(5)

        packet_id = int.from_bytes(header[0:1], byteorder='big')
        json_length = int.from_bytes(header[1:5], byteorder='big')

        return [packet_id, json_length]

    async def recv_packet(self, header: list[int, int] = None) -> Packet:
        recv_header = header
        if not recv_header:
            recv_header = await self.recv_header()

        packet_id, packet_length = recv_header

        recv_packet_class = packetList[packet_id]
        recv_packet = recv_packet_class()
        packet_bytes: bytes = None

        if packet_length > 0:
            packet_bytes = await self.recv(packet_length)
        
        recv_packet.unpack_data(packet_bytes)
        
        return recv_packet
        
            

packetList = {
    1: TunnelRequestPacket,
}