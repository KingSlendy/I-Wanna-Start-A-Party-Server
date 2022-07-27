import asyncio, os
from tcp_server import *
from enum import IntEnum

PORT = 33320
VERSION = ""
SIZE = 0
BYTES = None

class ClientVER(IntEnum):
    SendVersion = 0
    Executable = 1


async def send_buffer(buffer, writer: asyncio.StreamWriter):
    buffer = bytes(buffer)
    writer.write(buffer)
    await writer.drain()


def detect_version():
    global VERSION, SIZE, BYTES

    filename = [f for f in os.listdir(".") if f.endswith(".zip")][0]
    version = filename[:-4]

    if VERSION != version:
        VERSION = version

        with open(filename, "rb") as file:
            BYTES = file.read()
            SIZE = len(BYTES)


async def handle_version(_: asyncio.StreamReader, writer: asyncio.StreamWriter):
    global VERSION, SIZE, BYTES

    detect_version()

    try:
        main_buffer_ver.seek_begin()
        main_buffer_ver.write(BUFFER_STRING, VERSION)
        main_buffer_ver.write(BUFFER_U8, 0)
        main_buffer_ver.write(BUFFER_U64, SIZE)
        await send_buffer(main_buffer_ver, writer)

        main_buffer_ver.seek_begin()
        main_buffer_ver.write(BUFFER_STRING, BYTES)
        await send_buffer(main_buffer_ver, writer)
    except ConnectionResetError:
        pass

    writer.close()


async def start_server():
    detect_version()
    server = await asyncio.start_server(handle_version, IP, VER_PORT, limit=1024)
    print(f"VER server started on address: {(IP if IP != '' else 'localhost')}:{VER_PORT}")

    async with server:
        await server.serve_forever()