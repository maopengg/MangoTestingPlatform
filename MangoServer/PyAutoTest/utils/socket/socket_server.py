import json
import socketserver
import subprocess
import time
from socket import *
from threading import Thread


# 使用socketserver进行多进程
class RequestHandle(socketserver.BaseRequestHandler):

    def handle(self):
        # while True:
        #     # 5.数据传输
        #     try:
        #         data = self.request.recv(1024 * 4)
        #     except ConnectionAbortedError:
        #         break
        #     if not data:
        #         break
        #     data = data.decode('utf-8')
        #     print('客服端发过来的数据：', data)
        #
        #     self.request.send(data.upper().encode('utf-8'))
        while True:
            msg = input('请输入：').strip()
            # self.request.send(msg.encode('utf-8'))
            if not msg:
                continue
            if msg == 'q':
                break
            self.send(name='CMD命令', data_size=len(msg), data=msg)

    def send(self, name, data_size, data):
        """发送数据"""
        header = {
            'name': name,
            'size': data_size
        }
        header_json = json.dumps(header)
        header_bayes = header_json.encode('utf-8')
        header_h = bytes(str(len(header_bayes)), 'utf-8').zfill(4)
        # 先发送请求头的长度
        self.request.send(header_h)
        # 再发送请求头的内容
        self.request.send(header_bayes)
        # 再发送实际的数据
        self.request.send(str(data).encode('utf-8'))

    def recv(self):
        """接收数据"""
        header_size = int(self.request.recv(4).decode('gbk'))
        header_json = self.request.recv(header_size).decode('gbk')
        header = json.loads(header_json)
        data_size = header['size']
        recv_size = 0
        data = b''
        while recv_size < data_size:
            res = self.request.recv(1024)
            recv_size += len(res)
            data += res
        print(len(data))
        print(data)
        return data

    def business(self, cmd):
        obj = subprocess.Popen(cmd.decode('utf-8'),
                               shell=True,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
        out_res = obj.stdout.read()
        err_res = obj.stderr.read()
        data_size = len(out_res) + len(err_res)
        data = out_res + err_res
        return data, data_size


class RequestManager:
    """
    管理客户端socket连接和触发端socket连接的类
    """

    def __init__(self):
        self.client_sockets = []
        self.msg = ''

    def handle_request(self, client_socket, client_addr):
        """
        处理客户端请求的函数，在线程中执行
        """
        self.client_sockets.append(client_socket)
        recv_data = client_socket.recv(1024)  # 接收1024个字节
        msg = recv_data.decode("utf-8")
        print("客户端发过来的消息:", msg)

    def handle_action(self, client_socket, client_addr):
        """
        处理触发端请求的函数，在线程中执行
        """
        recv_data = client_socket.recv(1024)  # 接收1024个字节
        msg = recv_data.decode("utf-8")
        self.msg = msg
        print("触发端发过来的消息：", self.msg)
        ret = "server get your action msg"
        self.send_msg()
        client_socket.send(ret.encode("utf-8"))
        client_socket.close()

    def close_connect(self):
        """
        关闭所有的客户端连接
        """
        for client_socket in self.client_sockets:
            client_socket.close()

    def send_msg(self):
        """
        触发后发送信息给所有的客户端
        """
        print("DEBUG  self.client_sockets:", self.client_sockets, "连接数量：", len(self.client_sockets))
        header_json = json.dumps(self.msg)
        for client_socket in self.client_sockets:
            try:
                client_socket.send(header_json.encode("utf-8"))
            except ConnectionResetError as e:
                # 若信息发送失败，去除该连接
                print("ERROR ConnectionResetError:", e)
                self.client_sockets.remove(client_socket)


def client_loop(manger):
    """
    连接客户端的循环
    """
    port = 14478
    tcp_server_socket = socket(AF_INET, SOCK_STREAM)
    address = ('', port)
    tcp_server_socket.bind(address)
    tcp_server_socket.listen(128)
    while True:
        # 等待客户端的链接
        print("服务成功启动，等待客户端链接中......")
        client_socket, client_addr = tcp_server_socket.accept()
        Thread(target=manger.handle_request, args=(client_socket, client_addr)).start()
    tcp_server_socket.close()


def action_loop(manger):
    """
    连接触发端的循环
    """
    port = 14479
    tcp_server_socket = socket(AF_INET, SOCK_STREAM)
    address = ('', port)
    tcp_server_socket.bind(address)
    tcp_server_socket.listen(128)
    while True:
        # 等待触发请求
        client_socket, client_addr = tcp_server_socket.accept()
        Thread(target=manger.handle_action, args=(client_socket, client_addr)).start()
    tcp_server_socket.close()


def main():
    # print("服务成功启动")
    manger = RequestManager()
    Thread(target=client_loop, args=(manger,)).start()
    Thread(target=action_loop, args=(manger,)).start()
    while True:
        # 死循阻塞程序
        time.sleep(5)


if __name__ == '__main__':
    # sk = socketserver.ThreadingTCPServer(('0.0.0.0', 14477), RequestHandle)
    # sk.serve_forever()
    main()
