import tcp_server, threading, udp_server

def main():
    tcp_thread = threading.Thread(target = tcp_server.start_server)
    tcp_thread.start()

    udp_thread = threading.Thread(target = udp_server.start_server)
    udp_thread.start()


if __name__ == "__main__":
    main()