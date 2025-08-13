#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
端口和网络诊断脚本
"""

import socket
import subprocess
import sys
import time

def check_port(host, port):
    """检查端口是否可用"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception as e:
        print(f"检查端口时出错: {e}")
        return False

def test_ports():
    """测试常用端口"""
    ports_to_test = [5000, 8080, 8000, 3000, 9000]
    
    print("🔍 端口可用性检测:")
    print("-" * 40)
    
    for port in ports_to_test:
        # 检查端口是否被占用
        is_occupied = check_port('127.0.0.1', port)
        status = "❌ 被占用" if is_occupied else "✅ 可用"
        print(f"端口 {port}: {status}")
    
    return ports_to_test

def find_free_port():
    """找到一个可用端口"""
    sock = socket.socket()
    sock.bind(('', 0))
    port = sock.getsockname()[1]
    sock.close()
    return port

def test_network():
    """测试网络连接"""
    print("\n🌐 网络连接测试:")
    print("-" * 40)
    
    # 测试本地回环
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        sock.connect(('127.0.0.1', 80))
        sock.close()
        print("✅ 本地回环连接正常")
    except:
        print("❌ 本地回环连接异常")
    
    # 获取本机IP
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        print(f"📍 本机IP: {local_ip}")
    except:
        print("❌ 无法获取本机IP")

def create_simple_server(port=None):
    """创建一个超简单的HTTP服务器测试"""
    if port is None:
        port = find_free_port()
    
    print(f"\n🚀 启动测试服务器 (端口 {port})...")
    print("-" * 40)
    
    try:
        from http.server import HTTPServer, SimpleHTTPRequestHandler
        import threading
        import webbrowser
        
        class TestHandler(SimpleHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                
                html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>网络连接测试成功</title>
                    <meta charset="UTF-8">
                    <style>
                        body {{ font-family: Arial, sans-serif; text-align: center; margin-top: 50px; }}
                        .success {{ color: green; font-size: 24px; }}
                        .info {{ color: #666; margin-top: 20px; }}
                    </style>
                </head>
                <body>
                    <h1 class="success">🎉 网络连接测试成功！</h1>
                    <p>如果您能看到这个页面，说明基础网络连接正常。</p>
                    <div class="info">
                        <p>服务器端口: {port}</p>
                        <p>访问时间: {time.strftime('%Y-%m-%d %H:%M:%S')}</p>
                        <p>现在可以尝试运行主程序了</p>
                    </div>
                </body>
                </html>
                """
                self.wfile.write(html.encode('utf-8'))
        
        server = HTTPServer(('', port), TestHandler)
        
        def open_browser():
            time.sleep(1)
            try:
                webbrowser.open(f'http://localhost:{port}')
                print(f"✅ 浏览器已打开: http://localhost:{port}")
            except Exception as e:
                print(f"❌ 自动打开浏览器失败: {e}")
                print(f"   请手动访问: http://localhost:{port}")
        
        # 启动浏览器
        browser_thread = threading.Thread(target=open_browser)
        browser_thread.daemon = True
        browser_thread.start()
        
        print(f"✅ 测试服务器启动成功")
        print(f"📍 请访问: http://localhost:{port}")
        print("🛑 按 Ctrl+C 停止服务器")
        
        server.serve_forever()
        
    except Exception as e:
        print(f"❌ 启动测试服务器失败: {e}")

if __name__ == "__main__":
    print("🔧 ArXiv Crawler 网络诊断工具")
    print("=" * 50)
    
    # 测试端口
    test_ports()
    
    # 测试网络
    test_network()
    
    # 询问是否启动测试服务器
    print("\n" + "=" * 50)
    try:
        response = input("是否启动测试服务器？(y/n): ").lower().strip()
        if response in ['y', 'yes', '是', '']:
            create_simple_server()
        else:
            print("诊断完成。建议:")
            print("1. 尝试更换端口 (如5000)")
            print("2. 检查防火墙设置") 
            print("3. 确保没有代理软件干扰")
    except KeyboardInterrupt:
        print("\n👋 诊断结束")
    except Exception as e:
        print(f"输入处理错误: {e}")
