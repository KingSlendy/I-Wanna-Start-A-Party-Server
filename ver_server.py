import asyncio, os
from tcp_server import *
from enum import IntEnum

PORT = 33320
VERSION = ""

class ClientVER(IntEnum):
    SendVersion = 0
    Executable = 1


async def send_buffer(buffer, writer: asyncio.StreamWriter):
    buffer = bytes(buffer)
    writer.write(buffer)
    await writer.drain()


def detect_version():
    global VERSION

    try:
        filename = [f for f in os.listdir(".") if f.endswith(".ver")][0]
        VERSION = filename[:-4]
    except:
        pass


async def handle_version(_: asyncio.StreamReader, writer: asyncio.StreamWriter):
    global VERSION

    detect_version()

    try:
        main_buffer_ver.seek_begin()
        main_buffer_ver.write(BUFFER_STRING, VERSION)
        await send_buffer(main_buffer_ver, writer)
    except ConnectionResetError:
        pass

    writer.close()


async def start_server():
    detect_version()
    server = await asyncio.start_server(handle_version, IP, VER_PORT)
    print(f"VER server started on address: {(IP if IP != '' else 'localhost')}:{VER_PORT}")

    async with server:
        await server.serve_forever()