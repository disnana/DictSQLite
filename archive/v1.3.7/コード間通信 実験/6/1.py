import socket

# サーバー側
def server():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('localhost', 5000))
    s.listen(1)
    conn, addr = s.accept()
    print('Connected by', addr)
    data = conn.recv(1024)
    print('Received', data.decode())
    conn.sendall(b'Hello from server')
    conn.close()

# クライアント側
def client():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(('localhost', 5000))
    s.sendall(b'Hello from client')
    data = s.recv(1024)
    print('Received', data.decode())
    s.close()

if __name__ == '__main__':
    from multiprocessing import Process

    server_process = Process(target=server)
    client_process = Process(target=client)

    server_process.start()
    client_process.start()

    server_process.join()
    client_process.join()