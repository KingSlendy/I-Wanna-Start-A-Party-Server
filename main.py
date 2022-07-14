import asyncio, threading, tcp_server, udp_server

async def main():
    #await asyncio.gather(tcp_server.start_server(), udp_server.start_server())
    thread = threading.Thread(target = udp_server.start_server)
    thread.start()
    
    await tcp_server.start_server()


if __name__ == "__main__":
    asyncio.run(main())