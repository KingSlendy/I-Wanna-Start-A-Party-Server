import os, struct

IP = "0.0.0.0"
PORT = int(os.environ.get('PORT') or "33321")
BUFFER_SIZE = 1024
FAILCHECK_ID = 121

# Buffer data types
BUFFER_U8 = "B"
BUFFER_U16 = "H"
BUFFER_U32 = "I"
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


main_buffer = Buffer()

def sanity_checks(buffer):
    if len(buffer) == 0:
        return False

    match_id = buffer[0]

    if match_id != FAILCHECK_ID:
        return False

    match_size = int(buffer[1] + buffer[2])

    if match_size != len(buffer):
        return False

    return True


def sanity_buffer_add(buffer, is_tcp):
    if isinstance(buffer, Buffer):
        data_size = len(buffer) + 4
        buffer.write(BUFFER_U8, FAILCHECK_ID, index = 0)
        buffer.write(BUFFER_U16, data_size, index = 1)
        buffer.write(BUFFER_BOOL, is_tcp, index = 2)