# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2025-03-25 22:22
# @Author : 毛鹏
import socket
import socks

# 设置全局代理
socks.set_default_proxy(socks.SOCKS5, "127.0.0.1", 1080)
socket.socket = socks.socksocket

# 测试连接
try:
    s = socket.socket()
    s.connect(("example.com", 80))
    s.sendall(b"GET / HTTP/1.1\r\nHost: example.com\r\n\r\n")
    print(s.recv(4096))
finally:
    s.close()
