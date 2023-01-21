import asyncio
from data import *
from enum import IntEnum

HASH_EMPTY_PASSWORD = "da39a3ee5e6b4b0d3255bfef95601890afd80709"

class Client():
    def __init__(self, writer):
        self.writer = writer
        self.address = None
        self.name = ""
        self.lobby = None


    def free(self):
        if self.lobby != None:
            self.lobby.remove(self)
            self.lobby = None

    
    def __repr__(self):
        return f"[Address: {self.address} | Name: {self.name} | Lobby: {self.lobby}]"


class ClientTCP(IntEnum):
    ReceiveMasterID = 0
    ReceiveID = 1
    ReceiveName = 2
    Heartbeat = 3
    PlayerConnect = 4
    PlayerDisconnect = 5
    CreateLobby = 6
    JoinLobby = 7
    LeaveLobby = 8
    LobbyList = 9
    LobbyPlayers = 10
    LobbyStart = 11


async def send_buffer_all(buffer, writer: asyncio.StreamWriter, to_me = False, sanity = True, header = True):
    global clients

    for client in clients.values():
        if client.writer == writer:
            if client.lobby == None:
                return

            if sanity:
                sanity_buffer_add(buffer, True)

            for c in client.lobby.clients:
                if c != None and (to_me or c.writer != writer):
                    await send_buffer(buffer, c.writer, sanity = False, header = header)

            break


async def send_buffer(buffer, writer: asyncio.StreamWriter, sanity = True, header = True):
    if sanity:
        sanity_buffer_add(buffer, True)

    if header:
        buffer = header_buffer_add(buffer)

    if not isinstance(buffer, bytes):
        buffer = bytes(buffer)

    writer.write(buffer)
    await writer.drain()


async def handle_buffer(buffer, writer: asyncio.StreamWriter):
    global clients, lobbies, lobby_count

    #print(buffer)
    data_id = int.from_bytes(buffer[16:18], "little")

    match data_id:
        case ClientTCP.ReceiveID:
            client = clients[int.from_bytes(buffer[18:26], "little")]
            client_id = 0

            for i, c in enumerate(client.lobby.clients):
                if c is client:
                    client_id = i + 1
                    break

            main_buffer_tcp.seek_begin()
            main_buffer_tcp.write_action(data_id)
            main_buffer_tcp.write(BUFFER_U8, client_id)
            await send_buffer(main_buffer_tcp, writer)

            main_buffer_tcp.seek_begin()
            main_buffer_tcp.write_action(ClientTCP.PlayerConnect)
            main_buffer_tcp.write(BUFFER_U8, client_id)
            main_buffer_tcp.write(BUFFER_STRING, client.name)
            await send_buffer_all(main_buffer_tcp, writer)

            main_buffer_tcp.seek_begin()
            main_buffer_tcp.write_action(ClientTCP.LobbyPlayers)

            for name in client.lobby.client_names():
                main_buffer_tcp.write(BUFFER_STRING, name)

            await send_buffer_all(main_buffer_tcp, writer, to_me = True)

        case ClientTCP.Heartbeat:
            pass

        case ClientTCP.CreateLobby:
            client = clients[int.from_bytes(buffer[18:26], "little")]
            name, password = buffer[26:].decode("utf-8").split("|")
            lobby = Lobby(name, password)
            same_name = any([l.name == name for l in lobbies.values()])

            if not same_name:
                lobbies[lobby_count] = lobby
                lobby.clients[0] = client
                client.lobby = lobby
                #print(lobbies)
                lobby_count += 1

            main_buffer_tcp.seek_begin()
            main_buffer_tcp.write_action(data_id)
            main_buffer_tcp.write(BUFFER_BOOL, same_name)
            main_buffer_tcp.write(BUFFER_U64, lobby.seed)
            await send_buffer(main_buffer_tcp, writer)

        case ClientTCP.JoinLobby:
            client = clients[int.from_bytes(buffer[18:26], "little")]
            name, password = buffer[26:].decode("utf-8").split("|")
            state = 0

            for lobby in lobbies.values():
                if lobby.name == name and (lobby.password == password or lobby.password == HASH_EMPTY_PASSWORD):
                    if lobby.clients.count(None) == 0:
                        state = 2
                        break

                    if lobby.started:
                        state = 3
                        break

                    lobby.clients[lobby.clients.index(None)] = client
                    client.lobby = lobby
                    state = 1
                    break

            main_buffer_tcp.seek_begin()
            main_buffer_tcp.write_action(data_id)
            main_buffer_tcp.write(BUFFER_U8, state)
            main_buffer_tcp.write(BUFFER_U64, lobby.seed)
            await send_buffer(main_buffer_tcp, writer)


        case ClientTCP.LeaveLobby:
            client = clients[int.from_bytes(buffer[18:26], "little")]
            client_id = client.lobby.clients.index(client)
            main_buffer_tcp.seek_begin()
            main_buffer_tcp.write_action(ClientTCP.PlayerDisconnect)
            main_buffer_tcp.write(BUFFER_U8, client_id + 1)
            await send_buffer_all(main_buffer_tcp, writer)
            client.free()

            main_buffer_tcp.seek_begin()
            main_buffer_tcp.write_action(data_id)
            await send_buffer(main_buffer_tcp, writer)

        case ClientTCP.LobbyList:
            main_buffer_tcp.seek_begin()
            main_buffer_tcp.write_action(data_id)

            for lobby in lobbies.values():
                main_buffer_tcp.write(BUFFER_STRING, f"{lobby.name}|{(lobby.password != HASH_EMPTY_PASSWORD)}|{len(lobby.clients) - lobby.clients.count(None)}|{lobby.started}.")

            main_buffer_tcp.write(BUFFER_STRING, "null")
            await send_buffer(main_buffer_tcp, writer)

        case ClientTCP.LobbyStart:
            client = clients[int.from_bytes(buffer[18:26], "little")]
            client.lobby.started = True
            main_buffer_tcp.seek_begin()
            main_buffer_tcp.write_action(data_id)
            await send_buffer_all(main_buffer_tcp, writer, to_me = True)
            
        case _:
            await send_buffer_all(buffer, writer, sanity = False, header = False)


async def connect_client(writer: asyncio.StreamWriter, reader: asyncio.StreamReader):
    global client_count

    clients[client_count] = Client(writer)
    main_buffer_tcp.seek_begin()
    main_buffer_tcp.write_action(ClientTCP.ReceiveMasterID)
    main_buffer_tcp.write(BUFFER_U64, client_count)
    await send_buffer(main_buffer_tcp, writer)

    main_buffer_tcp.seek_begin()
    main_buffer_tcp.write_action(ClientTCP.ReceiveName)
    await send_buffer(main_buffer_tcp, writer)

    buffer = await asyncio.wait_for(reader.read(BUFFER_SIZE), 12)
    client = clients[int.from_bytes(buffer[18:26], "little")]
    client.name = buffer[26:].decode()

    client_count += 1


async def disconnect_client(writer: asyncio.StreamWriter):
    for spot, client in clients.items():
        if client.writer != None and client.writer is writer:
            if client.lobby != None:
                # Send the disconnecting player to everyone else in the lobby
                client_id = client.lobby.clients.index(client)
                main_buffer_tcp.seek_begin()
                main_buffer_tcp.write_action(ClientTCP.PlayerDisconnect)
                main_buffer_tcp.write(BUFFER_U8, client_id + 1)
                await send_buffer_all(main_buffer_tcp, writer)

                # Update the player names for everyone else in the lobby
                main_buffer_tcp.seek_begin()
                main_buffer_tcp.write_action(ClientTCP.LobbyPlayers)

                for name in client.lobby.client_names():
                    main_buffer_tcp.write(BUFFER_STRING, name)

                await send_buffer_all(main_buffer_tcp, writer)

            client.free()
            print(f"Client disconnected: {client}")
            del clients[spot]
            break


async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    global clients, lobbies

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

    try:
        # Send back the master ID to the connected client
        await connect_client(writer, reader)

        while True:
            buffer = await asyncio.wait_for(reader.read(BUFFER_SIZE), 12)

            if buffer == b"" or not buffer:
                break

            await handle_buffer(buffer, writer)
    except (ConnectionError, TimeoutError):
        pass

    # Client has left the server, disconnect
    await disconnect_client(writer = writer)
    writer.close()


async def start_server():
    server = await asyncio.start_server(handle_client, IP, MAIN_PORT)
    print(f"TCP server started on address: {(IP if IP != '' else 'localhost')}:{MAIN_PORT}")

    async with server:
        await server.serve_forever()