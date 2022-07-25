import asyncio, os
from tcp_server import *
from enum import IntEnum

PORT = 33320

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


async def handle_version(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
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

    filename = [f for f in os.listdir(".") if f.endswith(".zip")][0]

    with open(filename, "rb") as file:
        binary = file.read()

    main_buffer_ver.seek_begin()
    main_buffer_ver.write_action(ClientVER.SendVersion)
    main_buffer_ver.write(BUFFER_U64, len(binary))
    main_buffer_ver.write(BUFFER_STRING, filename[:-4])
    await send_buffer(main_buffer_ver, writer)

    #index = 0

    try:
        lines = 0

        with open(filename, "rb") as file:
            for line in file:
                if lines == 0:
                    main_buffer_ver.seek_begin()
                    main_buffer_ver.write_action(ClientVER.Executable)

                for byte in line:
                    main_buffer_ver.write(BUFFER_U8, byte)
                
                lines += 1

                if lines == 3_000:
                    await send_buffer(main_buffer_ver, writer)
                    await asyncio.sleep(0.1)
                    lines = 0

            if lines < 3_000:
                await send_buffer(main_buffer_ver, writer)

        #while True:
        #    main_buffer_ver.seek_begin()
        #    main_buffer_ver.write_action(ClientVER.Executable)

        #    for _ in range(5000):
        #        data = binary[index:index + 8]

        #        if data == b"":
        #            print("Done")
        #            await send_buffer(main_buffer_ver, writer)
        #            raise ConnectionResetError()

        #        main_buffer_ver.write(BUFFER_U64, int.from_bytes(data, "little"))
        #        index += 8

        #    await send_buffer(main_buffer_ver, writer)
        #    await asyncio.sleep(1)
    except ConnectionResetError:
        pass

    writer.close()


async def start_server():
    server = await asyncio.start_server(handle_version, IP, VER_PORT)
    print(f"VER server started on address: {(IP if IP != '' else 'localhost')}:{VER_PORT}")

    async with server:
        await server.serve_forever()