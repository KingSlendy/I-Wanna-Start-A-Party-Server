BUFFER_INT = 0
BUFFER_BOOL = 0
BUFFER_STRING = 0

class Buffer:
    def __init__(self, bytes: bytes):
        self.bytes = list(bytes)
        self.offset = 0

    
    def read(self, type):
        pass