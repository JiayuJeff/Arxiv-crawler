#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最简化的Flask测试脚本
用于诊断Flask连接问题
"""

from flask import Flask
import webbrowser
import threading
import time

app = Flask(__name__)

@app.route('/')
def home():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Flask测试</title>
        <meta charset="UTF-8">
    </head>
    <body>
        <h1>Flask测试成功！</h1>
        <p>如果您能看到这个页面，说明Flask服务器运行正常。</p>
        <p>时间: <span id="time"></span></p>
        <script>
            document.getElementById('time').textContent = new Date().toLocaleString();
        </script>
    </body>
    </html>
    '''

def open_browser():
    """延迟打开浏览器"""
    time.sleep(1.5)
    try:
        webbrowser.open('http://localhost:5000')
        print("浏览器已打开")
    except Exception as e:
        print(f"打开浏览器失败: {e}")

if __name__ == '__main__':
    print("启动Flask测试服务器...")
    print("服务器地址: http://localhost:5000")
    
    # 启动浏览器线程
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()
    
    try:
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=False,
            use_reloader=False,
            threaded=True
        )
    except Exception as e:
        print(f"Flask启动失败: {e}")
        input("按回车键退出...")
