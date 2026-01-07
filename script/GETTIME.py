import socket  # 导入 socket 模块以进行网络通信
import time  # 导入 time 模块以处理时间
import threading  # 导入 threading 模块以支持多线程

# 设置目标 ESP32 端口
ESP32_PORT = 12345  # 定义 ESP32 监听的端口号
ESP32_IP = None  # 初始 ESP32_IP 为 None，稍后将通过接收到的数据包设置

# 创建 UDP 套接字
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # 创建一个 UDP 套接字

# 绑定到接收端口，准备接收来自 ESP32 的请求
sock.bind(('0.0.0.0', ESP32_PORT))  # 绑定到所有可用的网络接口和指定端口

# 定义发送时间戳的标志
sending = False  # 用于控制是否发送时间戳的标志
current_addr = None  # 存储当前发送时间戳的地址


def listen_for_udp():
    global ESP32_IP, current_addr, sending  # 声明全局变量
    while True:  # 持续监听
        # 等待接收来自 ESP32 的请求
        data, addr = sock.recvfrom(1024)  # 接收最多 1024 字节的数据
        message = data.decode()

        if message == "Get time":
            ESP32_IP = addr  # 获取发送包的 IP 地址
            current_addr = addr  # 存储当前地址
            print(f"Received 'Get time' request from: {ESP32_IP}")  # 显示接收到的请求
            start_sending()  # 启动发送时间戳

        elif message == "Get OK" and current_addr == addr:
            print(f"Received 'Get OK' from: {addr}")
            stop_sending()  # 停止发送时间戳，但继续监听


def send_timestamp(addr):
    current_time = time.time()
    timestamp = int(round(current_time * 1000))
    sock.sendto(str(timestamp).encode(), addr)  # 发送时间戳
    print(f"Sent timestamp: {timestamp}")  # 打印发送的时间戳


def sending_thread():
    while sending:
        if current_addr:  # 确保当前地址已设置
            send_timestamp(current_addr)  # 发送时间戳
            time.sleep(1)  # 每秒发送一次


def start_sending():
    global sending  # 声明 sending 为全局变量
    if not sending:  # 仅在未发送时启动
        sending = True  # 设置发送标志为 True
        threading.Thread(target=sending_thread, daemon=True).start()  # 启动发送线程


def stop_sending():
    global sending  # 声明 sending 为全局变量
    sending = False  # 设置发送标志为 False


# 启动 UDP 监听线程
threading.Thread(target=listen_for_udp, daemon=True).start()  # 创建并启动监听线程

# 保持主线程运行
try:
    while True:
        time.sleep(1)  # 主线程保持运行
except KeyboardInterrupt:
    print("程序已终止")