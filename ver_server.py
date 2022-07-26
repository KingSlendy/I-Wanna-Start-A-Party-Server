import asyncio, os
from tcp_server import *
from enum import IntEnum

PORT = 33320
VERSION = ""
SIZE = 0
BYTES = None
SEND_SIZE = 500_000

class ClientVER(IntEnum):
    SendVersion = 0
    Executable = 1


async def send_buffer(buffer, writer: asyncio.StreamWriter, header = True):
    if header:
        buffer = header_buffer_add(buffer)
    
    if not isinstance(buffer, bytes):
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


async def handle_version(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    global VERSION, SIZE, BYTES
    
    # Handshake start
    writer.write(HANDSHAKE_BEGIN)
    await writer.drain()
    buffer = await reader.read(BUFFER_SIZE)

    if buffer[:8] != HANDSHAKE_ENSURE:
        print(f"Unexpected handshake message: {buffer[:8]}\nExpected: {HANDSHAKE_ENSURE}")
        writer.close()
        return

    # Handshake response
    await send_buffer(HANDSHAKE_RESPONSE, writer, header = False)
    detect_version()

    main_buffer_ver.seek_begin()
    main_buffer_ver.write_action(ClientVER.SendVersion)
    main_buffer_ver.write(BUFFER_U64, SIZE)
    main_buffer_ver.write(BUFFER_STRING, VERSION)
    main_buffer_ver.write(BUFFER_U8, 0)
    await send_buffer(main_buffer_ver, writer)

    try:
        for i in range(0, SIZE, SEND_SIZE):
            main_buffer_ver.seek_begin()
            main_buffer_ver.write_action(ClientVER.Executable)
            main_buffer_ver.write(BUFFER_STRING, BYTES[i:i + SEND_SIZE])
            await send_buffer(main_buffer_ver, writer)
            #await asyncio.sleep(1)
    except ConnectionResetError:
        pass

    writer.close()


async def start_server():
    detect_version()
    server = await asyncio.start_server(handle_version, IP, VER_PORT)
    print(f"VER server started on address: {(IP if IP != '' else 'localhost')}:{VER_PORT}")

    async with server:
        await server.serve_forever()