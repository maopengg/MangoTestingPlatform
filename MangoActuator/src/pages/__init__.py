# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-08-20 20:22
# @Author : 毛鹏
# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, messagebox


class LoginWindow:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("芒果测试平台 - 登录")
        self.window.geometry("400x500")
        self.window.resizable(False, False)

        # 设置背景色
        self.window.configure(bg="#f0f0f0")

        # 添加间距
        tk.Label(self.window, bg="#f0f0f0").pack(pady=20)

        # IP 和端口输入框
        ip_frame = tk.Frame(self.window, bg="#f0f0f0")
        ip_frame.pack(fill=tk.X, padx=20, pady=5)

        tk.Label(ip_frame, text="IP", bg="#f0f0f0").pack(side=tk.LEFT)
        self.ip_entry = ttk.Entry(ip_frame)
        self.ip_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        self.ip_entry.insert(0, "请输入后端服务IP")

        tk.Label(ip_frame, text="端口", bg="#f0f0f0").pack(side=tk.LEFT, padx=(20, 0))
        self.port_entry = ttk.Entry(ip_frame, width=10)
        self.port_entry.pack(side=tk.LEFT)
        self.port_entry.insert(0, "请输入后端服务端口")

        # 账号输入框
        account_frame = tk.Frame(self.window, bg="#f0f0f0")
        account_frame.pack(fill=tk.X, padx=20, pady=5)

        tk.Label(account_frame, text="账号", bg="#f0f0f0").pack(side=tk.LEFT)
        self.username_entry = ttk.Entry(account_frame)
        self.username_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        self.username_entry.insert(0, "请输入登录账号")

        # 密码输入框
        password_frame = tk.Frame(self.window, bg="#f0f0f0")
        password_frame.pack(fill=tk.X, padx=20, pady=5)

        tk.Label(password_frame, text="密码", bg="#f0f0f0").pack(side=tk.LEFT)
        self.password_entry = ttk.Entry(password_frame, show="*")
        self.password_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        self.password_entry.insert(0, "请输入登录密码")

        # 记住密码复选框
        self.remember_var = tk.IntVar()
        self.remember_check = ttk.Checkbutton(
            self.window,
            text="记住密码",
            variable=self.remember_var
        )
        self.remember_check.pack(pady=10)

        # 登录按钮
        self.login_button = ttk.Button(
            self.window,
            text="登录",
            command=self.on_login
        )
        self.login_button.pack(pady=20, ipadx=20, ipady=5)

        # 注册按钮
        self.register_button = ttk.Button(
            self.window,
            text="注册",
            style="Link.TButton",
            command=self.on_register
        )
        self.register_button.pack(pady=10)

        # 添加样式
        self.setup_styles()

    def setup_styles(self):
        style = ttk.Style()
        style.configure("TButton", padding=6)
        style.configure("Link.TButton", foreground="blue", borderwidth=0)
        style.map("Link.TButton",
                  foreground=[("active", "blue"), ("pressed", "darkblue")])

    def on_login(self):
        ip = self.ip_entry.get()
        port = self.port_entry.get()
        username = self.username_entry.get()
        password = self.password_entry.get()
        remember = self.remember_var.get()

        # 这里添加登录逻辑
        messagebox.showinfo("登录信息",
                            f"IP: {ip}\n端口: {port}\n账号: {username}\n密码: {password}\n记住密码: {remember}")

    def on_register(self):
        messagebox.showinfo("注册", "跳转到注册页面")

    def run(self):
        self.window.mainloop()


if __name__ == "__main__":
    app = LoginWindow()
    app.run()