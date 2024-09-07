import socket


def start_client():
    # ソケットを作成
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # サーバーのアドレスとポートに接続
    server_address = ('localhost', 65432)
    client_socket.connect(server_address)

    try:
        # サーバーにメッセージを送信
        message = 'Hello, Server!'
        client_socket.sendall(message.encode())

        # サーバーからのレスポンスを受信
        data = client_socket.recv(1024)
        print(f'Received from server: {data.decode()}')

    finally:
        # ソケットを閉じる
        client_socket.close()


if __name__ == "__main__":
    start_client()
