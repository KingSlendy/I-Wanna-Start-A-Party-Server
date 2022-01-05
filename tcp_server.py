import socket, threading
from data import *
from enum import IntEnum

clients = [None] * 4

class Client_TCP(IntEnum):
    ReceiveID = 0
    PlayerConnect = 1
    PlayerDisconnect = 2

def send_buffer_all(buffer, socket, to_me = False):
    sanity_buffer_add(buffer, True)

    for client in clients:
        if client != None and (to_me or client != socket):
            send_buffer(buffer, client, sanity = False)


def send_buffer(buffer, socket, sanity = True):
    if sanity:
        sanity_buffer_add(buffer, True)

    if not isinstance(buffer, bytes):
        buffer = bytes(buffer)

    if int(buffer[4] + buffer[5]) == 15:
        print(buffer)

    socket.send(buffer)


def handle_client(socket, address):
    print(f"TCP connection with address: {address}")

    # Send back the ID to the connected client
    player_id = clients.index(None)
    clients[player_id] = socket
    main_buffer.seek_begin()
    main_buffer.write_action(Client_TCP.ReceiveID)
    main_buffer.write(BUFFER_U8, player_id + 1)
    send_buffer(main_buffer, socket)

    # Send back the ID of the connecting client
    main_buffer.seek_begin()
    main_buffer.write_action(Client_TCP.PlayerConnect)
    main_buffer.write(BUFFER_U8, player_id + 1)
    send_buffer_all(main_buffer, socket)

    connected = True

    try:
        while connected:
            buffer = socket.recv(BUFFER_SIZE)

            if not buffer or not sanity_checks(buffer):
                continue

            send_buffer_all(buffer, socket)
    except ConnectionResetError:
        print(f"TCP disconnection with address: {address}")

    # Send back the ID of the disconnecting client
    clients[clients.index(socket)] = None
    main_buffer.seek_begin()
    main_buffer.write_action(Client_TCP.PlayerDisconnect)
    main_buffer.write(BUFFER_U8, player_id + 1)
    send_buffer_all(main_buffer, socket)
    socket.close()


def handle_server(server):
    print(f"TCP server started on address: {IP}:{PORT}")
    server.listen()

    while True:
        socket, address = server.accept()
        thread = threading.Thread(target = handle_client, args = (socket, address))
        thread.start()


def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((IP, PORT))
    handle_server(server)