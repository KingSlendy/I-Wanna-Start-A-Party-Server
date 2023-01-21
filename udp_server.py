import socket
from data import *
from enum import IntEnum

class ClientUDP(IntEnum):
    Initialize = 0
    Heartbeat = 1


def send_buffer_all(server, buffer, address, to_me = False):
    global clients

    for client in clients.values():
        if client.address == address:
            if client.lobby == None:
                return

            sanity_buffer_add(buffer, True)

            for c in client.lobby.clients:
                if c != None and (to_me or c.address != address):
                    send_buffer(server, buffer, c.address, sanity = False)

            break


def send_buffer(server, buffer, address, sanity = True):
    if sanity:
        sanity_buffer_add(buffer, False)

    if not isinstance(buffer, bytes):
        buffer = bytes(buffer)

    server.sendto(buffer, address)


def handle_buffer(server, buffer, address):
    global clients

    data_id = int.from_bytes(buffer[4:6], "little")

    match data_id:
        case ClientUDP.Initialize:
            client = clients[int.from_bytes(buffer[6:14], "little")]
            client.address = address
            print(f"Client connected: {client}")
            main_buffer_udp.seek_begin()
            main_buffer_udp.write_action(ClientUDP.Initialize)
            send_buffer(server, main_buffer_udp, address)

        case ClientUDP.Heartbeat:
            client_id = int.from_bytes(buffer[6:14], "little")

            if client_id in clients:
                main_buffer_udp.seek_begin()
                main_buffer_udp.write_action(ClientUDP.Heartbeat)
                send_buffer(server, main_buffer_udp, address)

        case _:
            send_buffer_all(server, buffer, address)


def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server.bind((IP, MAIN_PORT))
    print(f"UDP server started on address: {(IP if IP != '' else 'localhost')}:{MAIN_PORT}")

    while True:
        try:
            buffer, address = server.recvfrom(BUFFER_SIZE)
            handle_buffer(server, buffer, address)
        except ConnectionError:
            pass