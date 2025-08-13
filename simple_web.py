#!/usr/bin/env python3
"""
简化的ArXiv论文网页版问答模块
支持动态LLM配置
"""

import json
import os
import webbrowser
import threading
import time
from flask import Flask, render_template, request, jsonify, render_template_string
from typing import List, Dict, Optional

try:
    from openai import OpenAI
except ImportError:
    print("Warning: openai库未安装。请运行: pip install openai")
    OpenAI = None


class SimpleWebChatBot:
    def __init__(self, web_port=8080, chat_file=None):
        """
        初始化简化版网页聊天机器人
        """
        self.web_port = web_port
        self.chat_file = chat_file
        self.papers = []
        self.skipped_papers = set()
        self.max_load_files = 10
        
        # LLM配置
        self.client = None
        self.llm_model = None
        self.llm_port = None
        self.is_configured = False
        
        # 加载论文数据
        self.load_papers()
    
    def load_papers(self):
        """加载论文数据"""
        if self.chat_file and os.path.exists(self.chat_file):
            file_path = self.chat_file
        elif os.path.exists("test_papers.json"):
            file_path = "test_papers.json"
        else:
            print("⚠️ 未找到论文数据文件")
            return
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.papers = json.load(f)
            print(f"📚 成功加载 {len(self.papers)} 篇论文")
        except Exception as e:
            print(f"❌ 加载论文失败: {e}")
    
    def configure_llm(self, model_name, port):
        """配置LLM连接"""
        try:
            self.llm_model = model_name
            self.llm_port = port
            self.client = OpenAI(
                base_url=f"http://localhost:{port}/v1",
                api_key="your-key-here"
            )
            # 测试连接
            self.client.models.list()
            self.is_configured = True
            return True, f"✅ 成功连接到 {model_name} (端口: {port})"
        except Exception as e:
            self.is_configured = False
            return False, f"❌ 连接失败: {str(e)}"
    
    def get_papers_for_display(self):
        """获取用于显示的论文列表"""
        return [
            {
                'id': i+1,
                'title': paper.get('title', '未知标题'),
                'authors': ', '.join(paper.get('authors', [])),
                'skipped': (i+1) in self.skipped_papers
            }
            for i, paper in enumerate(self.papers)
        ]
    
    def skip_papers(self, skip_ids_str):
        """跳过指定的论文"""
        if not skip_ids_str.strip():
            # 清空跳过列表
            self.skipped_papers.clear()
            return True, "已恢复所有论文"
        
        try:
            skip_ids = [int(x.strip()) for x in skip_ids_str.split(',') if x.strip()]
            for paper_id in skip_ids:
                if 1 <= paper_id <= len(self.papers):
                    self.skipped_papers.add(paper_id)
            
            active_count = len(self.papers) - len(self.skipped_papers)
            return True, f"已跳过 {len(skip_ids)} 篇论文，当前活跃: {active_count} 篇"
        except ValueError:
            return False, "请输入有效的论文编号（如：1,3,5）"
    
    def ask_question(self, question):
        """处理问题"""
        if not self.is_configured:
            return [{"type": "error", "response": "请先配置LLM连接"}]
        
        if not self.papers:
            return [{"type": "error", "response": "未找到论文数据"}]
        
        try:
            # 获取活跃的论文
            active_papers = [
                self.papers[i] for i in range(len(self.papers))
                if (i+1) not in self.skipped_papers
            ]
            
            if not active_papers:
                return [{"type": "error", "response": "所有论文都已被跳过"}]
            
            # 构造对话内容
            papers_text = ""
            for i, paper in enumerate(active_papers[:self.max_load_files], 1):
                papers_text += f"\\n\\n论文 {i}:\\n"
                papers_text += f"标题: {paper.get('title', '')}\\n"
                papers_text += f"摘要: {paper.get('abstract_cn', paper.get('abstract', ''))}\\n"
            
            prompt = f"""基于以下论文信息回答问题：

{papers_text}

问题: {question}

请提供准确、有用的回答。如果问题涉及特定论文，请明确指出。"""

            response = self.client.chat.completions.create(
                model=self.llm_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=2000
            )
            
            answer = response.choices[0].message.content
            
            return [{
                "type": "all_papers",
                "response": answer
            }]
            
        except Exception as e:
            return [{"type": "error", "response": f"处理失败: {str(e)}"}]


def create_simple_app(chatbot):
    """创建简化的Flask应用"""
    app = Flask(__name__)
    
    @app.route('/')
    def home():
        """主页"""
        return render_template_string(get_html_template(), 
                                      paper_count=len(chatbot.papers),
                                      max_load_files=chatbot.max_load_files,
                                      is_configured=chatbot.is_configured,
                                      llm_model=chatbot.llm_model or "",
                                      llm_port=chatbot.llm_port or 9000)
    
    @app.route('/configure', methods=['POST'])
    def configure_llm():
        """配置LLM"""
        data = request.get_json()
        model_name = data.get('model_name', '')
        port = data.get('port', 9000)
        
        success, message = chatbot.configure_llm(model_name, port)
        return jsonify({'success': success, 'message': message, 'is_configured': chatbot.is_configured})
    
    @app.route('/chat', methods=['POST'])
    def chat():
        """处理聊天请求"""
        data = request.get_json()
        question = data.get('message', '')
        
        if not question:
            return jsonify({'error': '请输入问题'})
        
        results = chatbot.ask_question(question)
        active_papers = len(chatbot.papers) - len(chatbot.skipped_papers)
        
        return jsonify({
            'results': results,
            'active_papers': active_papers
        })
    
    @app.route('/papers')
    def get_papers():
        """获取论文列表"""
        return jsonify({'papers': chatbot.get_papers_for_display()})
    
    @app.route('/skip', methods=['POST'])
    def skip_papers():
        """跳过论文"""
        data = request.get_json()
        skip_ids = data.get('skip_ids', '')
        
        success, message = chatbot.skip_papers(skip_ids)
        active_papers = len(chatbot.papers) - len(chatbot.skipped_papers)
        
        return jsonify({
            'success': success,
            'message': message,
            'active_papers': active_papers
        })
    
    return app


def get_html_template():
    """获取HTML模板"""
    return '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ArXiv论文智能问答系统</title>
    <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🤖</text></svg>">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
            min-height: 100vh;
            padding: 10px;
            line-height: 1.6;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            box-shadow: 0 25px 50px rgba(0,0,0,0.15);
            overflow: hidden;
            height: calc(100vh - 20px);
            display: flex;
            flex-direction: column;
            backdrop-filter: blur(10px);
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px;
            text-align: center;
            position: relative;
            overflow: hidden;
        }
        
        .header h1 {
            font-size: 2.2em;
            margin-bottom: 10px;
            font-weight: 700;
        }
        
        .config-section {
            background: rgba(255,255,255,0.1);
            padding: 20px;
            border-radius: 12px;
            margin-top: 15px;
        }
        
        .config-form {
            display: flex;
            gap: 15px;
            align-items: center;
            flex-wrap: wrap;
            justify-content: center;
        }
        
        .config-input {
            padding: 12px 16px;
            border: 2px solid rgba(255,255,255,0.3);
            border-radius: 8px;
            background: rgba(255,255,255,0.1);
            color: white;
            min-width: 200px;
        }
        
        .config-input::placeholder {
            color: rgba(255,255,255,0.7);
        }
        
        .config-btn {
            padding: 12px 24px;
            border: none;
            border-radius: 8px;
            background: rgba(255,255,255,0.2);
            color: white;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.3s ease;
        }
        
        .config-btn:hover {
            background: rgba(255,255,255,0.3);
        }
        
        .config-status {
            margin-top: 15px;
            text-align: center;
        }
        
        .status-configured {
            color: #4CAF50;
            font-weight: bold;
        }
        
        .status-not-configured {
            color: #FFC107;
            font-weight: bold;
        }
        
        .main-content {
            flex: 1;
            display: flex;
            overflow: hidden;
        }
        
        .chat-area {
            flex: 1;
            display: flex;
            flex-direction: column;
            border-right: 2px solid #eee;
        }
        
        .messages {
            flex: 1;
            overflow-y: auto;
            padding: 25px;
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        }
        
        .message {
            margin-bottom: 20px;
            animation: fadeInUp 0.4s ease-out;
        }
        
        @keyframes fadeInUp {
            from { 
                opacity: 0; 
                transform: translateY(20px); 
            }
            to { 
                opacity: 1; 
                transform: translateY(0); 
            }
        }
        
        .user-message {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 18px 24px;
            border-radius: 25px 25px 8px 25px;
            margin-left: 15%;
            word-wrap: break-word;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
        }
        
        .ai-message {
            background: white;
            border: 2px solid #e9ecef;
            padding: 18px 24px;
            border-radius: 25px 25px 25px 8px;
            margin-right: 15%;
            word-wrap: break-word;
            box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        }
        
        .error-message {
            background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%);
            border: 1px solid #f5c6cb;
            color: #721c24;
            padding: 18px 24px;
            border-radius: 12px;
            margin-bottom: 12px;
            box-shadow: 0 2px 8px rgba(220, 53, 69, 0.2);
        }
        
        .input-area {
            padding: 25px;
            background: white;
            border-top: 2px solid #eee;
        }
        
        .input-group {
            display: flex;
            gap: 12px;
            margin-bottom: 18px;
        }
        
        .input-group input {
            flex: 1;
            padding: 18px 24px;
            border: 2px solid #dee2e6;
            border-radius: 30px;
            font-size: 16px;
            outline: none;
            transition: all 0.3s ease;
            background: #f8f9fa;
        }
        
        .input-group input:focus {
            border-color: #667eea;
            background: white;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        
        .btn {
            padding: 18px 32px;
            border: none;
            border-radius: 30px;
            font-size: 16px;
            cursor: pointer;
            transition: all 0.3s ease;
            font-weight: 600;
        }
        
        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
        }
        
        .btn-primary:hover:not(:disabled) {
            transform: translateY(-3px);
            box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
        }
        
        .btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none !important;
        }
        
        .sidebar {
            width: 320px;
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            padding: 25px;
            overflow-y: auto;
        }
        
        .welcome-message {
            background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
            border: 2px solid #2196f3;
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 20px;
            text-align: center;
        }
        
        .warning-message {
            background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%);
            border: 2px solid #ffc107;
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 20px;
            text-align: center;
        }
        
        .loading {
            text-align: center;
            padding: 30px;
            color: #6c757d;
        }
        
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            width: 50px;
            height: 50px;
            animation: spin 1s linear infinite;
            margin: 0 auto 15px;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 ArXiv论文智能问答系统</h1>
            <p>基于AI的学术论文智能分析平台</p>
            
            <div class="config-section">
                <h3>🔧 LLM配置</h3>
                <div class="config-form">
                    <input type="text" class="config-input" id="modelName" placeholder="模型名称 (如: gpt-3.5-turbo)" value="{{ llm_model }}">
                    <input type="number" class="config-input" id="modelPort" placeholder="端口号" value="{{ llm_port }}">
                    <button class="config-btn" onclick="configureLLM()">🔗 连接</button>
                </div>
                <div class="config-status" id="configStatus">
                    {% if is_configured %}
                        <span class="status-configured">✅ 已连接到 {{ llm_model }}</span>
                    {% else %}
                        <span class="status-not-configured">⚠️ 请先配置LLM连接</span>
                    {% endif %}
                </div>
            </div>
        </div>
        
        <div class="main-content">
            <div class="chat-area">
                <div class="messages" id="messages">
                    {% if is_configured %}
                        <div class="welcome-message">
                            <h3>🎉 欢迎使用ArXiv论文智能问答系统！</h3>
                            <p>💡 您可以询问关于已加载论文的任何问题</p>
                            <p>📚 已加载 {{ paper_count }} 篇论文</p>
                        </div>
                    {% else %}
                        <div class="warning-message">
                            <h3>⚠️ 需要配置LLM连接</h3>
                            <p>请在上方配置LLM模型和端口后开始使用</p>
                            <p>📚 已准备 {{ paper_count }} 篇论文数据</p>
                        </div>
                    {% endif %}
                </div>
                
                <div class="input-area">
                    <div class="input-group">
                        <input type="text" id="messageInput" placeholder="请输入您的问题..." onkeypress="handleKeyPress(event)">
                        <button class="btn btn-primary" onclick="sendMessage()" id="sendBtn">发送</button>
                    </div>
                </div>
            </div>
            
            <div class="sidebar">
                <h3>📚 论文列表</h3>
                <div id="papersList">
                    <div class="loading">
                        <div class="spinner"></div>
                        正在加载...
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let isConfigured = {{ is_configured|lower }};
        let isLoading = false;

        function handleKeyPress(event) {
            if (event.key === 'Enter' && !isLoading && isConfigured) {
                sendMessage();
            }
        }

        async function configureLLM() {
            const modelName = document.getElementById('modelName').value.trim();
            const port = parseInt(document.getElementById('modelPort').value) || 9000;
            
            if (!modelName) {
                alert('请输入模型名称');
                return;
            }
            
            try {
                const response = await fetch('/configure', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({model_name: modelName, port: port})
                });
                
                const data = await response.json();
                const statusEl = document.getElementById('configStatus');
                
                if (data.success) {
                    statusEl.innerHTML = '<span class="status-configured">✅ ' + data.message + '</span>';
                    isConfigured = true;
                    
                    // 更新欢迎消息
                    const messages = document.getElementById('messages');
                    messages.innerHTML = `
                        <div class="welcome-message">
                            <h3>🎉 欢迎使用ArXiv论文智能问答系统！</h3>
                            <p>💡 您可以询问关于已加载论文的任何问题</p>
                            <p>📚 已加载论文数据，开始智能问答吧！</p>
                        </div>
                    `;
                } else {
                    statusEl.innerHTML = '<span class="status-not-configured">❌ ' + data.message + '</span>';
                    isConfigured = false;
                }
            } catch (error) {
                document.getElementById('configStatus').innerHTML = '<span class="status-not-configured">❌ 连接失败: ' + error.message + '</span>';
            }
        }

        async function sendMessage() {
            if (isLoading || !isConfigured) return;
            
            const input = document.getElementById('messageInput');
            const message = input.value.trim();
            
            if (!message) return;
            
            addMessage(message, 'user');
            input.value = '';
            
            setLoading(true);
            addLoadingMessage();
            
            try {
                const response = await fetch('/chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({message: message})
                });
                
                const data = await response.json();
                removeLoadingMessage();
                
                if (data.error) {
                    addMessage(data.error, 'error');
                } else {
                    data.results.forEach(result => {
                        if (result.type === 'all_papers') {
                            addMessage(result.response, 'ai');
                        } else if (result.type === 'error') {
                            addMessage(result.response, 'error');
                        }
                    });
                }
            } catch (error) {
                removeLoadingMessage();
                addMessage('❌ 发送失败: ' + error.message, 'error');
            }
            
            setLoading(false);
        }

        function addMessage(content, type) {
            const messages = document.getElementById('messages');
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message';
            
            if (type === 'user') {
                messageDiv.innerHTML = `<div class="user-message">${content}</div>`;
            } else if (type === 'error') {
                messageDiv.innerHTML = `<div class="error-message">${content}</div>`;
            } else {
                messageDiv.innerHTML = `<div class="ai-message">${content.replace(/\\n/g, '<br>')}</div>`;
            }
            
            messages.appendChild(messageDiv);
            messages.scrollTop = messages.scrollHeight;
        }

        function addLoadingMessage() {
            const messages = document.getElementById('messages');
            const loadingDiv = document.createElement('div');
            loadingDiv.className = 'message';
            loadingDiv.id = 'loading-message';
            loadingDiv.innerHTML = `
                <div class="loading">
                    <div class="spinner"></div>
                    🤔 AI正在分析您的问题...
                </div>
            `;
            messages.appendChild(loadingDiv);
            messages.scrollTop = messages.scrollHeight;
        }

        function removeLoadingMessage() {
            const loadingMsg = document.getElementById('loading-message');
            if (loadingMsg) {
                loadingMsg.remove();
            }
        }

        function setLoading(loading) {
            isLoading = loading;
            const sendBtn = document.getElementById('sendBtn');
            const messageInput = document.getElementById('messageInput');
            
            sendBtn.disabled = loading || !isConfigured;
            messageInput.disabled = loading || !isConfigured;
            sendBtn.textContent = loading ? '处理中...' : '发送';
        }

        async function loadPapers() {
            try {
                const response = await fetch('/papers');
                const data = await response.json();
                
                const papersList = document.getElementById('papersList');
                papersList.innerHTML = '';
                
                data.papers.forEach(paper => {
                    const paperDiv = document.createElement('div');
                    paperDiv.style.cssText = `
                        background: white;
                        border: 2px solid #dee2e6;
                        border-radius: 12px;
                        padding: 15px;
                        margin-bottom: 12px;
                        font-size: 0.9em;
                    `;
                    paperDiv.innerHTML = `
                        <div style="font-weight: bold; color: #667eea;">📄 论文 ${paper.id}</div>
                        <div style="font-weight: 600; margin: 8px 0 5px 0;">${paper.title}</div>
                        <div style="color: #6c757d; font-size: 0.85em;">${paper.authors}</div>
                    `;
                    papersList.appendChild(paperDiv);
                });
            } catch (error) {
                document.getElementById('papersList').innerHTML = '<div style="color: #dc3545;">❌ 加载失败</div>';
            }
        }

        // 页面加载时初始化
        document.addEventListener('DOMContentLoaded', function() {
            loadPapers();
            document.getElementById('messageInput').focus();
        });
    </script>
</body>
</html>'''


def start_simple_web_chat(args):
    """启动简化的Web聊天界面"""
    print(f"\n{'='*60}")
    print(f"🚀 ArXiv论文智能问答系统")
    print(f"{'='*60}")
    
    # 创建聊天机器人
    chatbot = SimpleWebChatBot(
        web_port=getattr(args, 'web_port', 8080),
        chat_file=getattr(args, 'chat_file', None)
    )
    
    # 创建Flask应用
    app = create_simple_app(chatbot)
    
    print(f"📱 网页地址: http://localhost:{chatbot.web_port}")
    print(f"📚 已准备 {len(chatbot.papers)} 篇论文")
    print(f"🔧 请在网页中配置LLM连接")
    print(f"{'='*60}")
    print(f"🌟 浏览器即将自动打开...")
    print(f"⚠️  如未自动打开，请手动访问上述地址")
    print(f"🛑 按 Ctrl+C 退出")
    print(f"{'='*60}")
    
    # 延迟后自动打开浏览器
    def open_browser():
        time.sleep(2)
        url = f"http://localhost:{chatbot.web_port}"
        try:
            webbrowser.open(url)
            print(f"✅ 浏览器已打开: {url}")
        except Exception as e:
            print(f"⚠️ 无法自动打开浏览器: {e}")
            print(f"📌 请手动访问: {url}")
    
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()
    
    # 启动Flask应用
    try:
        app.run(host='0.0.0.0', port=chatbot.web_port, debug=False)
    except KeyboardInterrupt:
        print(f"\n🛑 用户终止程序")
    except Exception as e:
        print(f"❌ 启动失败: {e}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--web_port', type=int, default=8080)
    parser.add_argument('--chat_file', default=None)
    args = parser.parse_args()
    start_simple_web_chat(args)
