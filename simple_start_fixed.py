#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复版简化启动脚本 - 解决端口连接问题
"""

import os
import sys
import json
import socket
import time
import threading
import webbrowser
import platform
from flask import Flask, request, jsonify

def find_free_port(start_port=5000):
    """找到一个可用端口"""
    for port in range(start_port, start_port + 100):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('127.0.0.1', port))
            sock.close()
            return port
        except OSError:
            continue
    return None

def test_port_connection(port):
    """测试端口是否可以连接"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex(('127.0.0.1', port))
        sock.close()
        return result == 0
    except:
        return False

def open_browser_cross_platform(url):
    """跨平台打开浏览器"""
    system = platform.system().lower()
    try:
        if system == "linux":
            # Linux环境，尝试多种方式
            try:
                os.system(f'xdg-open "{url}" 2>/dev/null &')
                print(f"✅ 已尝试打开浏览器: {url}")
            except:
                try:
                    os.system(f'firefox "{url}" 2>/dev/null &')
                    print(f"✅ 已用Firefox打开: {url}")
                except:
                    print(f"❌ 自动打开浏览器失败，请手动访问: {url}")
        elif system == "darwin":  # macOS
            os.system(f'open "{url}"')
            print(f"✅ 已打开浏览器: {url}")
        elif system == "windows":
            os.system(f'start "{url}"')
            print(f"✅ 已打开浏览器: {url}")
        else:
            # 通用方式
            webbrowser.open(url)
            print(f"✅ 已打开浏览器: {url}")
    except Exception as e:
        print(f"❌ 打开浏览器失败: {e}")
        print(f"   请手动访问: {url}")

def create_app():
    app = Flask(__name__)
    
    # 加载测试数据
    papers = []
    if os.path.exists("test_papers.json"):
        try:
            with open("test_papers.json", 'r', encoding='utf-8') as f:
                papers = json.load(f)
        except Exception as e:
            print(f"加载论文数据失败: {e}")
    
    @app.route('/')
    def home():
        return f'''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ArXiv论文智能问答系统</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{ 
            max-width: 900px; 
            margin: 0 auto; 
            background: rgba(255,255,255,0.95); 
            border-radius: 15px; 
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{ 
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            color: white; 
            padding: 30px; 
            text-align: center; 
        }}
        .header h1 {{ font-size: 2.5em; margin-bottom: 10px; }}
        .header p {{ font-size: 1.1em; opacity: 0.9; }}
        .content {{ padding: 30px; }}
        .config-section {{ 
            background: #f8f9fa; 
            border-radius: 10px; 
            padding: 25px; 
            margin-bottom: 25px;
            border-left: 4px solid #4facfe;
        }}
        .config-section h3 {{ color: #333; margin-bottom: 20px; }}
        .input-group {{ margin-bottom: 15px; }}
        .input-group label {{ 
            display: block; 
            margin-bottom: 5px; 
            font-weight: 600; 
            color: #555; 
        }}
        .input-group input, .input-group select {{ 
            width: 100%; 
            padding: 12px; 
            border: 2px solid #e1e5e9; 
            border-radius: 8px; 
            font-size: 14px;
            transition: border-color 0.3s;
        }}
        .input-group input:focus, .input-group select:focus {{ 
            outline: none; 
            border-color: #4facfe; 
        }}
        .btn {{ 
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            color: white; 
            border: none; 
            padding: 12px 25px; 
            border-radius: 8px; 
            cursor: pointer; 
            font-size: 16px;
            font-weight: 600;
            transition: transform 0.2s;
        }}
        .btn:hover {{ transform: translateY(-2px); }}
        .chat-section {{ 
            background: white; 
            border-radius: 10px; 
            padding: 25px;
            border: 1px solid #e1e5e9;
        }}
        .chat-messages {{ 
            height: 400px; 
            overflow-y: auto; 
            border: 1px solid #e1e5e9; 
            border-radius: 8px; 
            padding: 15px;
            margin-bottom: 15px;
            background: #fafafa;
        }}
        .message {{ 
            margin-bottom: 15px; 
            padding: 10px; 
            border-radius: 8px; 
        }}
        .user-message {{ 
            background: #e3f2fd; 
            text-align: right; 
        }}
        .bot-message {{ 
            background: #f1f8e9; 
        }}
        .input-area {{ 
            display: flex; 
            gap: 10px; 
        }}
        .input-area input {{ 
            flex: 1; 
            padding: 12px; 
            border: 2px solid #e1e5e9; 
            border-radius: 8px;
        }}
        .status {{ 
            padding: 10px; 
            border-radius: 8px; 
            margin-top: 15px; 
            text-align: center;
        }}
        .status.success {{ background: #d4edda; color: #155724; }}
        .status.error {{ background: #f8d7da; color: #721c24; }}
        .status.warning {{ background: #fff3cd; color: #856404; }}
        .connection-test {{ 
            background: #e8f5e8; 
            border: 1px solid #4caf50; 
            border-radius: 8px; 
            padding: 15px; 
            margin: 20px 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 ArXiv论文智能问答</h1>
            <p>已加载 {len(papers)} 篇论文 | 连接状态: 正常</p>
        </div>
        
        <div class="content">
            <div class="connection-test">
                <h4>✅ 网络连接测试成功</h4>
                <p>如果您能看到这个页面，说明Flask服务器运行正常！</p>
                <p>当前时间: <span id="current-time"></span></p>
            </div>
            
            <div class="config-section">
                <h3>🔧 LLM配置</h3>
                <div class="input-group">
                    <label>API基础URL:</label>
                    <input type="text" id="api-base" value="http://localhost:11434/v1" placeholder="如: http://localhost:11434/v1">
                </div>
                <div class="input-group">
                    <label>API密钥:</label>
                    <input type="password" id="api-key" value="ollama" placeholder="输入API密钥">
                </div>
                <div class="input-group">
                    <label>模型名称:</label>
                    <input type="text" id="model-name" value="qwen2.5:14b" placeholder="如: qwen2.5:14b">
                </div>
                <button class="btn" onclick="testConnection()">🔗 测试连接</button>
                <div id="config-status"></div>
            </div>
            
            <div class="chat-section">
                <h3>💬 智能问答</h3>
                <div class="chat-messages" id="chat-messages">
                    <div class="message bot-message">
                        <strong>助手:</strong> 你好！我是ArXiv论文智能助手。请先配置LLM连接，然后就可以开始提问了！
                    </div>
                </div>
                <div class="input-area">
                    <input type="text" id="question-input" placeholder="输入您的问题..." onkeypress="handleKeyPress(event)">
                    <button class="btn" onclick="askQuestion()">发送</button>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // 显示当前时间
        document.getElementById('current-time').textContent = new Date().toLocaleString();
        
        function testConnection() {{
            const apiBase = document.getElementById('api-base').value;
            const apiKey = document.getElementById('api-key').value;
            const modelName = document.getElementById('model-name').value;
            
            if (!apiBase || !modelName) {{
                showStatus('config-status', 'error', '请填写完整的配置信息');
                return;
            }}
            
            showStatus('config-status', 'warning', '正在测试连接...');
            
            fetch('/test_llm', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{
                    api_base: apiBase,
                    api_key: apiKey,
                    model_name: modelName
                }})
            }})
            .then(response => response.json())
            .then(data => {{
                if (data.success) {{
                    showStatus('config-status', 'success', '✅ 连接成功！可以开始提问了');
                }} else {{
                    showStatus('config-status', 'error', '❌ 连接失败: ' + data.error);
                }}
            }})
            .catch(error => {{
                showStatus('config-status', 'error', '❌ 网络错误: ' + error.message);
            }});
        }}
        
        function askQuestion() {{
            const question = document.getElementById('question-input').value.trim();
            if (!question) return;
            
            addMessage('user', question);
            document.getElementById('question-input').value = '';
            
            const apiBase = document.getElementById('api-base').value;
            const apiKey = document.getElementById('api-key').value;
            const modelName = document.getElementById('model-name').value;
            
            addMessage('bot', '正在思考中...');
            
            fetch('/ask', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{
                    question: question,
                    api_base: apiBase,
                    api_key: apiKey,
                    model_name: modelName
                }})
            }})
            .then(response => response.json())
            .then(data => {{
                const messages = document.getElementById('chat-messages');
                messages.removeChild(messages.lastChild); // 移除"思考中"消息
                addMessage('bot', data.answer || '抱歉，处理您的问题时出现错误');
            }})
            .catch(error => {{
                const messages = document.getElementById('chat-messages');
                messages.removeChild(messages.lastChild);
                addMessage('bot', '网络错误: ' + error.message);
            }});
        }}
        
        function addMessage(type, content) {{
            const messages = document.getElementById('chat-messages');
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message ' + (type === 'user' ? 'user-message' : 'bot-message');
            messageDiv.innerHTML = '<strong>' + (type === 'user' ? '您' : '助手') + ':</strong> ' + content;
            messages.appendChild(messageDiv);
            messages.scrollTop = messages.scrollHeight;
        }}
        
        function showStatus(elementId, type, message) {{
            const element = document.getElementById(elementId);
            element.className = 'status ' + type;
            element.textContent = message;
        }}
        
        function handleKeyPress(event) {{
            if (event.key === 'Enter') {{
                askQuestion();
            }}
        }}
    </script>
</body>
</html>
        '''
    
    @app.route('/test_llm', methods=['POST'])
    def test_llm():
        """测试LLM连接"""
        try:
            return jsonify({{"success": True, "message": "模拟连接成功"}})
        except Exception as e:
            return jsonify({{"success": False, "error": str(e)}})
    
    @app.route('/ask', methods=['POST'])
    def ask_question():
        """处理问题"""
        try:
            data = request.json
            question = data.get('question', '')
            
            # 模拟回答
            answer = f"感谢您的问题：'{question}'。这是一个演示回答，说明连接正常工作。在实际使用中，这里会连接到配置的LLM服务。"
            
            return jsonify({{"answer": answer}})
        except Exception as e:
            return jsonify({"answer": f"处理问题时出错: {str(e)}"})
    
    return app

def main():
    print("🔧 ArXiv Crawler - 修复版启动")
    print("=" * 50)
    
    # 查找可用端口
    print("🔍 寻找可用端口...")
    port = find_free_port(5000)
    
    if port is None:
        print("❌ 无法找到可用端口，尝试使用默认端口5000")
        port = 5000
    else:
        print(f"✅ 找到可用端口: {port}")
    
    # 创建应用
    app = create_app()
    
    # 启动信息
    print(f"🚀 启动ArXiv智能问答系统...")
    print(f"📍 服务地址: http://localhost:{port}")
    print(f"📍 或访问: http://127.0.0.1:{port}")
    print("🔧 在网页中配置LLM连接后即可使用")
    print("🛑 按 Ctrl+C 退出")
    print("-" * 50)
    
    # 延迟打开浏览器
    def delayed_browser_open():
        time.sleep(2)  # 等待服务器启动
        url = f"http://localhost:{port}"
        
        # 再次测试端口
        print(f"🔍 测试端口连接...")
        if test_port_connection(port):
            print(f"✅ 端口 {port} 连接正常")
        else:
            print(f"⚠️ 端口 {port} 可能未完全启动，稍后再试")
        
        open_browser_cross_platform(url)
    
    # 启动浏览器线程
    browser_thread = threading.Thread(target=delayed_browser_open)
    browser_thread.daemon = True
    browser_thread.start()
    
    try:
        # 启动Flask服务器
        app.run(
            host='0.0.0.0',  # 监听所有接口
            port=port,
            debug=False,
            use_reloader=False,
            threaded=True
        )
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        print("\n🔧 故障排除建议:")
        print("1. 检查端口是否被其他程序占用")
        print("2. 尝试更换端口号")
        print("3. 检查防火墙设置")
        print("4. 运行网络诊断: python network_diagnosis.py")

if __name__ == '__main__':
    main()
