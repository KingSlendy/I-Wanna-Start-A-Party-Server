import socket
from data import *
from enum import IntEnum

class Client_UDP(IntEnum):
    Heartbeat = 0
    PlayerMove = 1
    LessRoll = 2
    SendSound = 3


def send_buffer_all(server, buffer, address, to_me = False):
    sanity_buffer_add(buffer, False)

    for client in udp_clients:
        if client != None and (to_me or client != address):
            send_buffer(server, buffer, client, sanity = False)


def send_buffer(server, buffer, address, sanity = True):
    if sanity:
        sanity_buffer_add(buffer, False)

    if not isinstance(buffer, bytes):
        buffer = bytes(buffer)

    server.sendto(buffer, address)


def handle_buffer(server, buffer, address):
    data_id = int.from_bytes(buffer[4:5], "little")

    match data_id:
        case Client_UDP.Heartbeat:
            if address not in udp_clients:
                player_id = buffer[6]
                udp_clients[player_id - 1] = address

            main_buffer.seek_begin()
            main_buffer.write_action(Client_UDP.Heartbeat)
            send_buffer(server, main_buffer, address)

        case _:
            send_buffer_all(server, buffer, address)


def handle_server(server):
    print(f"UDP server started on address: {(IP if IP != '' else 'localhost')}:{PORT}")

    try:
        while True:
            buffer, address = server.recvfrom(BUFFER_SIZE)
            handle_buffer(server, buffer, address)
    except ConnectionResetError:
        pass


def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server.bind((IP, PORT))
    handle_server(server)