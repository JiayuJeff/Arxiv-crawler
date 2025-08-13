#!/usr/bin/env python3
"""
ArXiv论文网页版问答模块
提供基于Flask的网页聊天界面
"""

import json
import os
from flask import Flask, render_template, request, jsonify
from typing import List, Dict, Optional
import threading
import time

try:
    from openai import OpenAI
except ImportError:
    print("Warning: openai库未安装。请运行: pip install openai")
    OpenAI = None


class WebArxivChatBot:
    def __init__(self, model_name: str, port: int, host: str = "0.0.0.0"):
        """
        初始化网页版问答机器人
        
        Args:
            model_name: LLM模型名称
            port: 服务端口
            host: 服务地址
        """
        if OpenAI is None:
            raise ImportError("openai库未安装。请运行: pip install openai")
            
        self.model_name = model_name
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}/v1"
        
        # 初始化OpenAI客户端
        self.client = OpenAI(
            api_key="EMPTY",
            base_url=self.base_url
        )
        
        self.papers = []
        self.file_path = ""
        self.skipped_papers = set()  # 存储被跳过的论文ID
        
    def load_papers(self, file_path: str) -> None:
        """
        加载文章数据
        
        Args:
            file_path: 论文JSON文件路径
        """
        self.file_path = file_path
        with open(file_path, 'r', encoding='utf-8') as f:
            self.papers = json.load(f)
        
        # 为每篇论文初始化conversation字段
        for i, paper in enumerate(self.papers):
            if 'conversation' not in paper:
                paper['conversation'] = []
            # 确保每篇论文有唯一且稳定的ID
            paper['_paper_id'] = i + 1
        
        print(f"已加载 {len(self.papers)} 篇文章")
        
    def save_papers(self) -> None:
        """保存论文数据到文件"""
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(self.papers, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存文件失败: {e}")
    
    def get_system_prompt(self) -> str:
        """获取系统提示词"""
        return """你是一个专业的学术论文分析助手。你的任务是基于提供的ArXiv论文摘要来回答用户的问题。

请遵循以下原则：
1. 仅基于提供的论文摘要内容回答问题
2. 如果问题无法从提供的摘要中找到答案，请明确说明
3. 回答时保持专业、准确、有条理的风格
4. 支持中英文问答
5. 根据论文内容进行深入分析和见解提供"""

    def build_single_paper_context(self, paper: Dict, include_history: bool = True) -> str:
        """
        构建单篇论文的上下文
        
        Args:
            paper: 论文数据
            include_history: 是否包含历史对话
            
        Returns:
            上下文字符串
        """
        context_parts = []
        context_parts.append("以下是相关的学术论文信息：\n")
        
        context_parts.append(f"标题: {paper.get('title', 'No title')}")
        context_parts.append(f"ArXiv ID: {paper.get('arxiv_id', 'No ID')}")
        context_parts.append(f"作者: {', '.join(paper.get('authors', []))}")
        context_parts.append(f"分类: {', '.join(paper.get('categories', []))}")
        context_parts.append(f"发布时间: {paper.get('published', 'No date')}")
        
        # 优先使用中文摘要
        abstract = paper.get('abstract_cn') or paper.get('abstract', 'No abstract')
        context_parts.append(f"摘要: {abstract}")
        
        # 添加历史对话
        if include_history and paper.get('conversation'):
            context_parts.append("\n--- 历史对话 ---")
            for conv in paper.get('conversation', []):
                context_parts.append(f"用户: {conv.get('question', '')}")
                context_parts.append(f"助手: {conv.get('response', '')}")
            context_parts.append("--- 历史对话结束 ---\n")
        
        return "\n".join(context_parts)
    
    def build_all_papers_context(self) -> str:
        """
        构建所有论文的上下文（不包含历史对话）
        
        Returns:
            包含所有论文信息的上下文字符串
        """
        context_parts = []
        context_parts.append("以下是相关的学术论文摘要信息，请基于这些内容回答用户的问题：\n")
        
        for paper in self.papers:
            if paper.get('_paper_id') in self.skipped_papers:
                continue
                
            context_parts.append(f"=== 论文 {paper.get('_paper_id')} ===")
            context_parts.append(f"标题: {paper.get('title', 'No title')}")
            context_parts.append(f"ArXiv ID: {paper.get('arxiv_id', 'No ID')}")
            context_parts.append(f"作者: {', '.join(paper.get('authors', []))}")
            context_parts.append(f"分类: {', '.join(paper.get('categories', []))}")
            context_parts.append(f"发布时间: {paper.get('published', 'No date')}")
            
            # 优先使用中文摘要
            abstract = paper.get('abstract_cn') or paper.get('abstract', 'No abstract')
            context_parts.append(f"摘要: {abstract}")
            context_parts.append("")  # 空行分隔
            
        return "\n".join(context_parts)
    
    def chat_single_paper(self, paper: Dict, user_input: str) -> str:
        """
        与单篇论文进行对话
        
        Args:
            paper: 论文数据
            user_input: 用户输入
            
        Returns:
            AI回复
        """
        try:
            messages = [
                {"role": "system", "content": self.get_system_prompt()},
                {"role": "user", "content": self.build_single_paper_context(paper, include_history=True)},
                {"role": "user", "content": user_input}
            ]
            
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.7,
                max_tokens=2048
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            return f"请求失败: {str(e)}"
    
    def chat_all_papers(self, user_input: str) -> str:
        """
        基于所有论文进行对话（不包含历史）
        
        Args:
            user_input: 用户输入
            
        Returns:
            AI回复
        """
        try:
            messages = [
                {"role": "system", "content": self.get_system_prompt()},
                {"role": "user", "content": self.build_all_papers_context()},
                {"role": "user", "content": user_input}
            ]
            
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.7,
                max_tokens=4096
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            return f"请求失败: {str(e)}"
    
    def process_question(self, user_input: str, max_load_files: int) -> List[Dict]:
        """
        处理用户问题
        
        Args:
            user_input: 用户输入
            max_load_files: 最大同时加载文件数
            
        Returns:
            回复列表，每个回复包含论文信息和AI回答
        """
        results = []
        
        # 过滤掉被跳过的论文
        active_papers = [p for p in self.papers if p.get('_paper_id') not in self.skipped_papers]
        
        if len(active_papers) <= max_load_files:
            # 小于等于阈值：一次性处理所有论文
            try:
                ai_response = self.chat_all_papers(user_input)
                results.append({
                    'type': 'all_papers',
                    'response': ai_response,
                    'paper_count': len(active_papers)
                })
                
                # 为所有论文添加对话记录
                for paper in active_papers:
                    paper['conversation'].append({
                        'question': user_input,
                        'response': ai_response
                    })
                    
            except Exception as e:
                results.append({
                    'type': 'error',
                    'response': f"处理失败: {str(e)}",
                    'paper_count': len(active_papers)
                })
        else:
            # 大于阈值：逐篇处理
            for paper in active_papers:
                try:
                    ai_response = self.chat_single_paper(paper, user_input)
                    results.append({
                        'type': 'single_paper',
                        'paper_id': paper.get('_paper_id'),
                        'paper_title': paper.get('title', 'No title'),
                        'response': ai_response
                    })
                    
                    # 添加对话记录
                    paper['conversation'].append({
                        'question': user_input,
                        'response': ai_response
                    })
                    
                except Exception as e:
                    results.append({
                        'type': 'error',
                        'paper_id': paper.get('_paper_id'),
                        'paper_title': paper.get('title', 'No title'),
                        'response': f"请求失败: {str(e)}"
                    })
        
        # 保存对话记录
        self.save_papers()
        
        return results


def create_app(chatbot: WebArxivChatBot, max_load_files: int):
    """创建Flask应用"""
    app = Flask(__name__)
    
    @app.route('/')
    def index():
        """主页"""
        return render_template('chat.html', 
                             paper_count=len(chatbot.papers),
                             max_load_files=max_load_files)
    
    @app.route('/chat', methods=['POST'])
    def chat():
        """处理聊天请求"""
        data = request.json
        user_input = data.get('message', '').strip()
        
        if not user_input:
            return jsonify({'error': '请输入问题'})
        
        # 处理问题
        results = chatbot.process_question(user_input, max_load_files)
        
        return jsonify({
            'results': results,
            'active_papers': len([p for p in chatbot.papers if p.get('_paper_id') not in chatbot.skipped_papers])
        })
    
    @app.route('/skip', methods=['POST'])
    def skip_papers():
        """跳过指定论文"""
        data = request.json
        skip_ids = data.get('skip_ids', '')
        
        if skip_ids:
            try:
                # 解析跳过的论文ID
                ids = [int(id.strip()) for id in skip_ids.split(',') if id.strip()]
                chatbot.skipped_papers.update(ids)
                
                return jsonify({
                    'success': True,
                    'message': f'已跳过论文: {", ".join(map(str, ids))}',
                    'active_papers': len([p for p in chatbot.papers if p.get('_paper_id') not in chatbot.skipped_papers])
                })
            except ValueError:
                return jsonify({'error': '请输入有效的论文编号'})
        else:
            # 清空跳过列表
            chatbot.skipped_papers.clear()
            return jsonify({
                'success': True,
                'message': '已清空跳过列表',
                'active_papers': len(chatbot.papers)
            })
    
    @app.route('/papers')
    def get_papers():
        """获取论文列表"""
        papers_info = []
        for paper in chatbot.papers:
            papers_info.append({
                'id': paper.get('_paper_id'),
                'title': paper.get('title', 'No title'),
                'authors': ', '.join(paper.get('authors', [])),
                'skipped': paper.get('_paper_id') in chatbot.skipped_papers
            })
        
        return jsonify({'papers': papers_info})
    
    return app


def start_web_chat(args):
    """
    启动网页版聊天
    
    Args:
        args: 包含配置参数的对象
    """
    print(f"\n=== 启动网页版问答模式 ===")
    print(f"读取文件: {args.output}")
    print(f"使用模型: {args.translate_llm}")
    print(f"LLM服务地址: http://0.0.0.0:{args.port}")
    print(f"最大同时加载: {args.max_load_files} 篇论文")
    
    try:
        # 创建聊天机器人
        chatbot = WebArxivChatBot(
            model_name=args.translate_llm,
            port=args.port
        )
        
        # 加载文章数据
        chatbot.load_papers(args.output)
        
        # 创建Flask应用
        app = create_app(chatbot, args.max_load_files)
        
        # 创建模板目录和文件
        create_templates()
        
        print(f"\n🚀 网页版问答界面已启动!")
        print(f"📱 请访问: http://localhost:{args.web_port}")
        print(f"🔄 当前模式: {'批量处理' if len(chatbot.papers) <= args.max_load_files else '逐篇处理'}")
        print(f"📚 已加载 {len(chatbot.papers)} 篇论文")
        print(f"⚠️  按 Ctrl+C 退出")
        
        # 启动Flask服务器
        app.run(host='0.0.0.0', port=args.web_port, debug=False)
        
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        return


def create_templates():
    """创建HTML模板"""
    os.makedirs('templates', exist_ok=True)
    
    html_content = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ArXiv论文问答系统</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
            height: calc(100vh - 40px);
            display: flex;
            flex-direction: column;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            text-align: center;
        }
        
        .header h1 {
            font-size: 2em;
            margin-bottom: 10px;
        }
        
        .status {
            background: rgba(255,255,255,0.2);
            padding: 10px;
            border-radius: 8px;
            margin-top: 10px;
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
            padding: 20px;
            background: #f8f9fa;
        }
        
        .message {
            margin-bottom: 20px;
            animation: fadeIn 0.3s ease-in;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .user-message {
            background: #667eea;
            color: white;
            padding: 15px 20px;
            border-radius: 20px 20px 5px 20px;
            margin-left: 20%;
            word-wrap: break-word;
        }
        
        .ai-message {
            background: white;
            border: 2px solid #e9ecef;
            padding: 15px 20px;
            border-radius: 20px 20px 20px 5px;
            margin-right: 20%;
            word-wrap: break-word;
        }
        
        .paper-info {
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            padding: 10px;
            border-radius: 8px;
            margin-bottom: 10px;
            font-size: 0.9em;
        }
        
        .error-message {
            background: #f8d7da;
            border: 1px solid #f5c6cb;
            color: #721c24;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 10px;
        }
        
        .input-area {
            padding: 20px;
            background: white;
            border-top: 2px solid #eee;
        }
        
        .input-group {
            display: flex;
            gap: 10px;
            margin-bottom: 15px;
        }
        
        .input-group input {
            flex: 1;
            padding: 15px;
            border: 2px solid #dee2e6;
            border-radius: 25px;
            font-size: 16px;
            outline: none;
            transition: border-color 0.3s;
        }
        
        .input-group input:focus {
            border-color: #667eea;
        }
        
        .btn {
            padding: 15px 30px;
            border: none;
            border-radius: 25px;
            font-size: 16px;
            cursor: pointer;
            transition: all 0.3s;
            font-weight: 600;
        }
        
        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }
        
        .btn-secondary {
            background: #6c757d;
            color: white;
        }
        
        .btn-secondary:hover {
            background: #5a6268;
        }
        
        .btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }
        
        .sidebar {
            width: 300px;
            background: #f8f9fa;
            padding: 20px;
            overflow-y: auto;
        }
        
        .sidebar h3 {
            margin-bottom: 15px;
            color: #495057;
        }
        
        .skip-section {
            margin-bottom: 30px;
        }
        
        .skip-input {
            width: 100%;
            padding: 10px;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            margin-bottom: 10px;
        }
        
        .papers-list {
            max-height: 400px;
            overflow-y: auto;
        }
        
        .paper-item {
            background: white;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            padding: 10px;
            margin-bottom: 10px;
            font-size: 0.9em;
        }
        
        .paper-item.skipped {
            background: #f8d7da;
            border-color: #f5c6cb;
        }
        
        .paper-id {
            font-weight: bold;
            color: #667eea;
        }
        
        .paper-title {
            font-weight: 600;
            margin-bottom: 5px;
        }
        
        .loading {
            text-align: center;
            padding: 20px;
            color: #6c757d;
        }
        
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 10px;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        @media (max-width: 768px) {
            .main-content {
                flex-direction: column;
            }
            
            .sidebar {
                width: 100%;
                border-right: none;
                border-top: 2px solid #eee;
            }
            
            .user-message, .ai-message {
                margin-left: 5%;
                margin-right: 5%;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 ArXiv论文问答系统</h1>
            <div class="status">
                <div>📚 已加载: <span id="paperCount">{{ paper_count }}</span> 篇论文</div>
                <div>🔄 处理模式: <span id="processMode">{{ '批量处理' if paper_count <= max_load_files else '逐篇处理' }}</span></div>
                <div>✅ 活跃论文: <span id="activePapers">{{ paper_count }}</span> 篇</div>
            </div>
        </div>
        
        <div class="main-content">
            <div class="chat-area">
                <div class="messages" id="messages">
                    <div class="ai-message">
                        👋 欢迎使用ArXiv论文问答系统！<br>
                        💬 您可以询问关于已加载论文的任何问题<br>
                        🔍 支持主题搜索、论文对比、技术分析等<br>
                        📝 在右侧可以跳过不感兴趣的论文
                    </div>
                </div>
                
                <div class="input-area">
                    <div class="input-group">
                        <input type="text" id="messageInput" placeholder="请输入您的问题..." onkeypress="handleKeyPress(event)">
                        <button class="btn btn-primary" onclick="sendMessage()" id="sendBtn">发送</button>
                    </div>
                    <button class="btn btn-secondary" onclick="clearChat()">清空对话</button>
                </div>
            </div>
            
            <div class="sidebar">
                <div class="skip-section">
                    <h3>📋 论文管理</h3>
                    <input type="text" class="skip-input" id="skipInput" placeholder="输入要跳过的论文编号(逗号分隔)">
                    <button class="btn btn-secondary" onclick="skipPapers()" style="width: 100%; margin-bottom: 10px;">跳过选中论文</button>
                    <button class="btn btn-secondary" onclick="clearSkipped()" style="width: 100%;">清空跳过列表</button>
                </div>
                
                <div>
                    <h3>📚 论文列表</h3>
                    <div class="papers-list" id="papersList">
                        <div class="loading">加载中...</div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let isLoading = false;

        function handleKeyPress(event) {
            if (event.key === 'Enter' && !isLoading) {
                sendMessage();
            }
        }

        async function sendMessage() {
            if (isLoading) return;
            
            const input = document.getElementById('messageInput');
            const message = input.value.trim();
            
            if (!message) return;
            
            // 显示用户消息
            addMessage(message, 'user');
            input.value = '';
            
            // 显示加载状态
            setLoading(true);
            addLoadingMessage();
            
            try {
                const response = await fetch('/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ message: message })
                });
                
                const data = await response.json();
                
                // 移除加载消息
                removeLoadingMessage();
                
                if (data.error) {
                    addMessage(data.error, 'error');
                } else {
                    // 显示回复
                    data.results.forEach(result => {
                        if (result.type === 'all_papers') {
                            addMessage(result.response, 'ai');
                        } else if (result.type === 'single_paper') {
                            const paperInfo = `论文 ${result.paper_id}: ${result.paper_title}`;
                            addMessage(result.response, 'ai', paperInfo);
                        } else if (result.type === 'error') {
                            const errorInfo = result.paper_id ? `论文 ${result.paper_id}: ${result.paper_title}` : '';
                            addMessage(result.response, 'error', errorInfo);
                        }
                    });
                    
                    // 更新活跃论文数量
                    document.getElementById('activePapers').textContent = data.active_papers;
                }
            } catch (error) {
                removeLoadingMessage();
                addMessage('发送失败: ' + error.message, 'error');
            }
            
            setLoading(false);
        }

        function addMessage(content, type, paperInfo = null) {
            const messages = document.getElementById('messages');
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message';
            
            if (type === 'user') {
                messageDiv.innerHTML = `<div class="user-message">${content}</div>`;
            } else if (type === 'error') {
                messageDiv.innerHTML = `
                    ${paperInfo ? `<div class="paper-info">${paperInfo}</div>` : ''}
                    <div class="error-message">${content}</div>
                `;
            } else {
                messageDiv.innerHTML = `
                    ${paperInfo ? `<div class="paper-info">${paperInfo}</div>` : ''}
                    <div class="ai-message">${content.replace(/\\n/g, '<br>')}</div>
                `;
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
                    正在处理您的问题...
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
            
            sendBtn.disabled = loading;
            messageInput.disabled = loading;
            sendBtn.textContent = loading ? '处理中...' : '发送';
        }

        async function skipPapers() {
            const skipInput = document.getElementById('skipInput');
            const skipIds = skipInput.value.trim();
            
            try {
                const response = await fetch('/skip', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ skip_ids: skipIds })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    addMessage(data.message, 'ai');
                    document.getElementById('activePapers').textContent = data.active_papers;
                    skipInput.value = '';
                    loadPapers(); // 重新加载论文列表
                } else {
                    addMessage(data.error, 'error');
                }
            } catch (error) {
                addMessage('操作失败: ' + error.message, 'error');
            }
        }

        async function clearSkipped() {
            try {
                const response = await fetch('/skip', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ skip_ids: '' })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    addMessage(data.message, 'ai');
                    document.getElementById('activePapers').textContent = data.active_papers;
                    loadPapers(); // 重新加载论文列表
                } else {
                    addMessage(data.error, 'error');
                }
            } catch (error) {
                addMessage('操作失败: ' + error.message, 'error');
            }
        }

        async function loadPapers() {
            try {
                const response = await fetch('/papers');
                const data = await response.json();
                
                const papersList = document.getElementById('papersList');
                papersList.innerHTML = '';
                
                data.papers.forEach(paper => {
                    const paperDiv = document.createElement('div');
                    paperDiv.className = `paper-item ${paper.skipped ? 'skipped' : ''}`;
                    paperDiv.innerHTML = `
                        <div class="paper-id">论文 ${paper.id}</div>
                        <div class="paper-title">${paper.title}</div>
                        <div style="color: #6c757d; font-size: 0.8em;">${paper.authors}</div>
                        ${paper.skipped ? '<div style="color: #721c24; font-size: 0.8em; margin-top: 5px;">已跳过</div>' : ''}
                    `;
                    papersList.appendChild(paperDiv);
                });
            } catch (error) {
                document.getElementById('papersList').innerHTML = '<div class="error-message">加载失败</div>';
            }
        }

        function clearChat() {
            const messages = document.getElementById('messages');
            messages.innerHTML = `
                <div class="ai-message">
                    👋 欢迎使用ArXiv论文问答系统！<br>
                    💬 您可以询问关于已加载论文的任何问题<br>
                    🔍 支持主题搜索、论文对比、技术分析等<br>
                    📝 在右侧可以跳过不感兴趣的论文
                </div>
            `;
        }

        // 页面加载时初始化
        document.addEventListener('DOMContentLoaded', function() {
            loadPapers();
            document.getElementById('messageInput').focus();
        });
    </script>
</body>
</html>'''
    
    with open('templates/chat.html', 'w', encoding='utf-8') as f:
        f.write(html_content)


if __name__ == "__main__":
    # 测试用
    import argparse
    
    class Args:
        def __init__(self):
            self.output = "tool-rl/output.json"
            self.translate_llm = "Qwen/Qwen3-32B"
            self.port = 10006
            self.max_load_files = 10
            self.web_port = 8080
    
    args = Args()
    start_web_chat(args)
