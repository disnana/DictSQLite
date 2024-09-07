import socket
import threading


def start_server():
    # ソケットを作成
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # SO_REUSEADDRオプションを設定
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # サーバーのアドレスとポートを指定
    server_address = ('localhost', 65432)
    server_socket.bind(server_address)

    # クライアントからの接続を待機
    server_socket.listen(1)
    print('Server is waiting for a connection...')

    while True:
        # クライアントからの接続を受け入れる
        connection, client_address = server_socket.accept()
        print(f'Connected to {client_address}')

        # 接続を処理するスレッドを開始
        client_thread = threading.Thread(target=handle_client, args=(connection,))
        client_thread.start()


def handle_client(connection):
    try:
        # データを受信して送信するループ
        while True:
            data = connection.recv(1024)
            if not data:
                break
            print(f'Received: {data.decode()}')
            connection.sendall(data)
    finally:
        # 接続を閉じる
        connection.close()


if __name__ == "__main__":
    server_thread = threading.Thread(target=start_server)
    server_thread.start()
