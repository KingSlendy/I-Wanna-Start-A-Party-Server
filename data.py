import random, struct, sys

IP = ""
MAIN_PORT = 33321
HANDSHAKE_BEGIN = b"GM:Studio-Connect\x00" # Server
HANDSHAKE_ENSURE = b"\xBE\xBA\xFE\xCA\x0B\xB0\xAD\xDE" # Client
HANDSHAKE_RESPONSE = b"\xAD\xBE\xAF\xDE\xEB\xBE\x0D\xF0\x0C\x00\x00\x00" # Server


clients = {}
client_count = 1
lobbies = {}
lobby_count = 1

BUFFER_SIZE = 1024
BUFFER_HEADER = b"\xDE\xC0\xAD\xDE\x0C\x00\x00\x00"
# HEADER_SIZE = 12
FAILCHECK_ID = 121

# Buffer data types
BUFFER_U8 = "B"
BUFFER_U16 = "H"
BUFFER_U32 = "I"
BUFFER_U64 = "Q"
BUFFER_S8 = "b"
BUFFER_S16 = "h"
BUFFER_S32 = "i"
BUFFER_BOOL = "?"
BUFFER_STRING = "s"

class Buffer:
    def __init__(self):
        self.seek_begin()

    
    def seek_begin(self):
        self.types = []
        self.data = []


    def write(self, type, data, index = -1):
        if type == BUFFER_STRING:
            if not isinstance(data, bytes):
                data = data.encode("utf-8")

            type = f"{len(data)}s"

        if index == -1:
            self.types.append(type)
            self.data.append(data)
        else:
            self.types.insert(index, type)
            self.data.insert(index, data)

    
    def write_action(self, data, index = -1):
        self.write(BUFFER_U16, data, index)


    def __bytes__(self):
        return struct.pack("".join(["<"] + self.types), *self.data)


    def __len__(self):
        return len(bytes(self))


    def __repr__(self):
        return f"Data: {self.data} | Types: {self.types}"


main_buffer_tcp = Buffer()
main_buffer_udp = Buffer()
main_buffer_ver = Buffer()

def header_buffer_add(buffer):
    if isinstance(buffer, Buffer):
        buffer = bytes(buffer)

    buffer_size = len(buffer).to_bytes(4, "little")
    header = BUFFER_HEADER + buffer_size
    return header + buffer


def sanity_buffer_add(buffer, is_tcp):
    if isinstance(buffer, Buffer):
        data_size = len(buffer) + 4
        buffer.write(BUFFER_U8, FAILCHECK_ID, index = 0)
        buffer.write(BUFFER_U16, data_size, index = 1)
        buffer.write(BUFFER_BOOL, is_tcp, index = 2)