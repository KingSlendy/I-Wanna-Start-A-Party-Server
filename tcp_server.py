import socket, threading
from xmlrpc.client import ProtocolError
from data import *
from enum import IntEnum

HANDSHAKE_BEGIN = b"GM:Studio-Connect\x00"
HANDSHAKE_ENSURE = b"\xBE\xBA\xFE\xCA\x0B\xB0\xAD\xDE"
HANDSHAKE_RESPONSE = b"\xAD\xBE\xAF\xDE\xEB\xBE\x0D\xF0\x0C\x00\x00\x00"
HASH_EMPTY_PASSWORD = "da39a3ee5e6b4b0d3255bfef95601890afd80709"

class Client():
    def __init__(self, socket):
        self.socket = socket
        self.address = None
        self.lobby = None


    def free(self):
        if self.lobby != None:
            self.lobby.remove(self)

            for i, client in enumerate(self.lobby.clients):
                main_buffer_tcp.seek_begin()
                main_buffer_tcp.write_action(ClientTCP.ResendID)
                main_buffer_tcp.write(BUFFER_U8, i + 1)
                send_buffer(main_buffer_tcp, client.socket)

            self.lobby = None

    
    def __repr__(self):
        return f"TCP: {self.socket} | UDP: {self.address}"


class ClientTCP(IntEnum):
    ReceiveMasterID = 0
    ReceiveID = 1
    ResendID = 2
    PlayerConnect = 3
    PlayerDisconnect = 4
    CreateLobby = 5
    JoinLobby = 6
    LeaveLobby = 7
    LobbyList = 8
    LobbyStart = 9


def send_buffer_all(buffer, socket, to_me = False, sanity = True, header = True):
    global clients

    for client in clients.values():
        if client.socket == socket:
            if client.lobby == None:
                return

            if sanity:
                sanity_buffer_add(buffer, True)

            for c in client.lobby.clients:
                if to_me or c.socket != socket:
                    send_buffer(buffer, c.socket, sanity = False, header = header)

            break


def send_buffer(buffer, socket, sanity = True, header = True):
    if sanity:
        sanity_buffer_add(buffer, True)

    if header:
        buffer = header_buffer_add(buffer)

    if not isinstance(buffer, bytes):
        buffer = bytes(buffer)

    socket.send(buffer)


def handle_buffer(buffer, socket):
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
            send_buffer(main_buffer_tcp, socket)

            main_buffer_tcp.seek_begin()
            main_buffer_tcp.write_action(ClientTCP.PlayerConnect)
            main_buffer_tcp.write(BUFFER_U8, client_id)
            send_buffer_all(main_buffer_tcp, socket)

        case ClientTCP.CreateLobby:
            client = clients[int.from_bytes(buffer[18:26], "little")]
            name, password = buffer[26:].decode("utf-8").split("|")
            lobby = Lobby(name, password)
            same_name = any([l.name == name for l in lobbies.values()])

            if not same_name:
                lobbies[lobby_count] = lobby
                lobby.clients.append(client)
                client.lobby = lobby
                #print(lobbies)
                lobby_count += 1

            main_buffer_tcp.seek_begin()
            main_buffer_tcp.write_action(data_id)
            main_buffer_tcp.write(BUFFER_BOOL, same_name)
            send_buffer(main_buffer_tcp, socket)

        case ClientTCP.JoinLobby:
            client = clients[int.from_bytes(buffer[18:26], "little")]
            name, password = buffer[26:].decode("utf-8").split("|")
            state = 0

            for lobby in lobbies.values():
                if lobby.name == name and (lobby.password == password or lobby.password == HASH_EMPTY_PASSWORD):
                    if len(lobby.clients) == 4:
                        state = 2
                        break

                    if lobby.started:
                        state = 3
                        break

                    lobby.clients.append(client)
                    client.lobby = lobby
                    state = 1
                    break

            main_buffer_tcp.seek_begin()
            main_buffer_tcp.write_action(data_id)
            main_buffer_tcp.write(BUFFER_U8, state)
            send_buffer(main_buffer_tcp, socket)

        case ClientTCP.LeaveLobby:
            client = clients[int.from_bytes(buffer[18:26], "little")]
            main_buffer_tcp.seek_begin()
            main_buffer_tcp.write_action(ClientTCP.PlayerDisconnect)
            main_buffer_tcp.write(BUFFER_U8, client.lobby.clients.index(client) + 1)
            send_buffer_all(main_buffer_tcp, socket)

            client.free()
            main_buffer_tcp.seek_begin()
            main_buffer_tcp.write_action(data_id)
            send_buffer(main_buffer_tcp, socket)

        case ClientTCP.LobbyList:
            main_buffer_tcp.seek_begin()
            main_buffer_tcp.write_action(data_id)

            for lobby in lobbies.values():
                main_buffer_tcp.write(BUFFER_STRING, f"{lobby.name}|{(lobby.password != HASH_EMPTY_PASSWORD)}|{len(lobby.clients)}|{lobby.started}.")

            main_buffer_tcp.write(BUFFER_STRING, "null")
            send_buffer(main_buffer_tcp, socket)

        case ClientTCP.LobbyStart:
            client = clients[int.from_bytes(buffer[18:26], "little")]
            client.lobby.started = True
            main_buffer_tcp.seek_begin()
            main_buffer_tcp.write_action(data_id)
            send_buffer_all(main_buffer_tcp, socket, to_me = True)
            
        case _:
            send_buffer_all(buffer, socket, sanity = False, header = False)


def handle_client(socket, address):
    global clients, client_count, lobbies

    print(f"TCP connection with address: {address}")

    # Handshake start
    socket.send(HANDSHAKE_BEGIN)
    buffer = socket.recv(BUFFER_SIZE)

    if buffer[:8] != HANDSHAKE_ENSURE:
        raise ProtocolError(f"Received unexpected handshake message: {buffer}")

    # Handshake response
    send_buffer(HANDSHAKE_RESPONSE, socket, header = False)

    # Send back the ID to the connected client
    clients[client_count] = Client(socket)
    main_buffer_tcp.seek_begin()
    main_buffer_tcp.write_action(ClientTCP.ReceiveMasterID)
    main_buffer_tcp.write(BUFFER_U64, client_count)
    send_buffer(main_buffer_tcp, socket)
    client_count += 1
    connected = True

    try:
        while connected:
            buffer = socket.recv(BUFFER_SIZE)

            if not buffer:
                continue

            handle_buffer(buffer, socket)
    except ConnectionResetError:
        print(f"TCP disconnection with address: {address}")

    # Send back the ID of the disconnecting client

    for spot, client in clients.items():
        if client.socket == socket:
            if client.lobby != None:
                main_buffer_tcp.seek_begin()
                main_buffer_tcp.write_action(ClientTCP.PlayerDisconnect)
                main_buffer_tcp.write(BUFFER_U8, client.lobby.clients.index(client) + 1)
                send_buffer_all(main_buffer_tcp, socket)

            client.free()
            del clients[spot]
            break

    socket.close()
    #print(clients)
    #print(lobbies)


def handle_server(server):
    print(f"TCP server started on address: {(IP if IP != '' else 'localhost')}:{PORT}")
    server.listen()

    while True:
        socket, address = server.accept()
        thread = threading.Thread(target = handle_client, args = (socket, address))
        thread.start()


def start_server():
    #while True:
        #try:
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((IP, PORT))
    handle_server(server)
        #except:
            #continue