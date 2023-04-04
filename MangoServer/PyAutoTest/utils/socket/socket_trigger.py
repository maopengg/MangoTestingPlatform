import json
from socket import *


def main(msg: str):
    """
    发送消息
    @param msg:
    @return:
    """
    tcp_client_socket = socket(AF_INET, SOCK_STREAM)
    server_ip = "127.0.0.1"
    server_port = 14479
    tcp_client_socket.connect((server_ip, server_port))
    tcp_client_socket.send(msg.encode("utf-8"))
    recv_data = tcp_client_socket.recv(1024)
    print("接收数据：", recv_data.decode("utf-8"))
    # 关闭套接字
    tcp_client_socket.close()


if __name__ == '__main__':
    msg = {"name": 'web_obj', 'data': ''}
    main(json.dumps(msg))
