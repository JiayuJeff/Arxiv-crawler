#!/usr/bin/env python3
"""
ArXiv论文智能问答系统 - 简化Web版本
完全重构，确保UI功能正常
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

# 导入爬虫功能
try:
    from crawl import ArxivCrawler
    from translate import ArxivTranslator
except ImportError as e:
    print(f"Warning: 导入失败 {e}")
    ArxivCrawler = None
    ArxivTranslator = None


class SimpleWebChatBot:
    def __init__(self, web_port=8080, chat_file=None):
        self.web_port = web_port
        self.chat_file = chat_file
        self.papers = []
        self.skipped_papers = set()
        self.max_load_files = 10
        self.current_file_path = None
        
        # LLM配置
        self.client = None
        self.llm_model = None
        self.llm_port = None
        self.is_configured = False
        
        # 创建papers目录
        if not os.path.exists('papers'):
            os.makedirs('papers')
    
    def get_available_files(self):
        """获取可用的论文文件列表"""
        files = []
        
        papers_dir = "papers"
        if os.path.exists(papers_dir):
            for file in os.listdir(papers_dir):
                if file.endswith('.json'):
                    file_path = os.path.join(papers_dir, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            if isinstance(data, list) and len(data) > 0:
                                files.append({
                                    'name': file,
                                    'path': file_path,
                                    'count': len(data),
                                    'display_name': file.replace('.json', '').replace('_', ' ')
                                })
                    except Exception as e:
                        continue
        
        # 也检查根目录的文件
        for file in ['test_papers.json', 'papers.json']:
            if os.path.exists(file):
                try:
                    with open(file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if isinstance(data, list) and len(data) > 0:
                            files.append({
                                'name': file,
                                'path': file,
                                'count': len(data),
                                'display_name': file.replace('.json', '').replace('_', ' ')
                            })
                except Exception:
                    continue
        
        return files
    
    def load_papers_from_file(self, file_path):
        """从指定文件加载论文"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                papers_data = json.load(f)
            
            if not isinstance(papers_data, list):
                return False, "文件格式错误：不是论文列表"
            
            self.papers = papers_data
            self.current_file_path = file_path
            return True, f"成功加载 {len(papers_data)} 篇论文"
            
        except Exception as e:
            return False, f"加载失败: {str(e)}"
    
    def configure_llm(self, model_name, port=9000):
        """配置LLM连接"""
        try:
            self.client = OpenAI(
                api_key="sk-no-key-required",
                base_url=f"http://localhost:{port}/v1"
            )
            
            # 测试连接
            response = self.client.chat.completions.create(
                model=model_name, messages=[{"role": "user", "content": "test"}], max_tokens=1
            )
            
            self.llm_model = model_name
            self.llm_port = port
            self.is_configured = True
            return True, f"✅ 成功连接到 {model_name} (端口: {port})"
            
        except Exception as e:
            self.is_configured = False
            return False, f"❌ 连接失败: {str(e)}"
    
    def chat(self, message):
        """发送消息到LLM"""
        if not self.is_configured or not self.client:
            return [{"type": "error", "response": "请先配置LLM连接"}]
        
        if not self.papers:
            return [{"type": "error", "response": "请先加载论文数据"}]
        
        try:
            # 构建上下文
            papers_context = ""
            for i, paper in enumerate(self.papers[:10]):  # 限制论文数量
                papers_context += f"\n论文{i+1}: {paper.get('title', '无标题')}\n"
                if 'abstract' in paper:
                    papers_context += f"摘要: {paper['abstract'][:200]}...\n"
            
            prompt = f"""你是一个专业的AI助手，帮助用户理解和分析ArXiv论文。

论文数据库:
{papers_context}

用户问题: {message}

请基于提供的论文信息回答用户的问题。如果问题与论文内容相关，请引用具体的论文。"""

            response = self.client.chat.completions.create(
                model=self.llm_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000,
                temperature=0.7
            )
            
            return [{"type": "ai", "response": response.choices[0].message.content}]
            
        except Exception as e:
            return [{"type": "error", "response": f"AI回复错误: {str(e)}"}]


def crawl_new_papers(search_params):
    """爬取新论文"""
    try:
        # 创建爬虫实例
        crawler = ArxivCrawler()
        
        # 设置搜索参数
        search_query = []
        if search_params.get('abstract_keywords'):
            search_query.append(f"abs:{search_params['abstract_keywords']}")
        if search_params.get('title_keywords'):
            search_query.append(f"ti:{search_params['title_keywords']}")
        if search_params.get('author'):
            search_query.append(f"au:{search_params['author']}")
        if search_params.get('categories'):
            search_query.append(f"cat:{search_params['categories']}")
        
        query = " AND ".join(search_query) if search_query else "cat:cs.AI"
        
        # 爬取论文
        papers = crawler.search_papers(
            query=query,
            max_results=int(search_params.get('max_results', 10)),
            start_date=search_params.get('start_date'),
            end_date=search_params.get('end_date')
        )
        
        if not papers:
            return {"success": False, "message": "未找到符合条件的论文"}
        
        # 翻译处理
        if search_params.get('translate', False) and ArxivTranslator:
            translator = ArxivTranslator()
            for paper in papers:
                if 'title' in paper:
                    paper['title_cn'] = translator.translate_single_abstract(paper['title'])
                if 'abstract' in paper:
                    paper['abstract_cn'] = translator.translate_single_abstract(paper['abstract'])
        
        # 保存到文件
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"papers/arxiv_papers_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(papers, f, ensure_ascii=False, indent=2)
        
        return {
            "success": True,
            "message": f"成功爬取 {len(papers)} 篇论文",
            "filename": filename,
            "paper_count": len(papers)
        }
        
    except Exception as e:
        return {"success": False, "message": f"爬取失败: {str(e)}"}


def create_simple_app(chatbot):
    """创建Flask应用"""
    app = Flask(__name__)
    
    @app.route('/')
    def index():
        template = get_html_template()
        return render_template_string(template, 
                                    llm_configured=chatbot.is_configured,
                                    llm_model=chatbot.llm_model,
                                    has_papers=len(chatbot.papers) > 0,
                                    paper_count=len(chatbot.papers))
    
    @app.route('/configure', methods=['POST'])
    def configure():
        data = request.json
        model_name = data.get('model_name')
        port = data.get('port', 9000)
        
        success, message = chatbot.configure_llm(model_name, port)
        return jsonify({"success": success, "message": message})
    
    @app.route('/chat', methods=['POST'])
    def chat():
        data = request.json
        message = data.get('message')
        response = chatbot.chat(message)
        return jsonify({"response": response})
    
    @app.route('/files')
    def files():
        files = chatbot.get_available_files()
        return jsonify({"files": files})
    
    @app.route('/load', methods=['POST'])
    def load():
        data = request.json
        file_path = data.get('file_path')
        success, message = chatbot.load_papers_from_file(file_path)
        return jsonify({"success": success, "message": message})
    
    @app.route('/crawl', methods=['POST'])
    def crawl():
        data = request.json
        result = crawl_new_papers(data)
        return jsonify(result)
    
    @app.route('/papers')
    def papers():
        return jsonify({"papers": chatbot.papers[:20]})  # 限制返回数量
    
    return app


def get_html_template():
    """获取HTML模板"""
    return '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ArXiv论文智能问答系统</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(45deg, #4facfe 0%, #00f2fe 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            font-weight: 300;
        }
        
        .main-content {
            display: flex;
            min-height: 600px;
        }
        
        .sidebar {
            width: 400px;
            background: #f8f9fa;
            border-right: 1px solid #dee2e6;
            padding: 20px;
            overflow-y: auto;
        }
        
        .chat-area {
            flex: 1;
            display: flex;
            flex-direction: column;
        }
        
        .config-section, .data-section {
            margin-bottom: 30px;
            padding: 20px;
            background: white;
            border-radius: 12px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        .section-title {
            font-size: 1.2em;
            font-weight: 600;
            margin-bottom: 15px;
            color: #333;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .input-group {
            margin-bottom: 15px;
        }
        
        .input-group label {
            display: block;
            margin-bottom: 5px;
            font-weight: 500;
            color: #555;
        }
        
        .input-group input, .input-group select {
            width: 100%;
            padding: 10px;
            border: 2px solid #e9ecef;
            border-radius: 8px;
            transition: border-color 0.3s;
        }
        
        .input-group input:focus, .input-group select:focus {
            outline: none;
            border-color: #4facfe;
        }
        
        .config-btn, .load-btn, .crawl-btn {
            width: 100%;
            padding: 12px;
            border: none;
            border-radius: 8px;
            font-weight: 600;
            font-size: 1em;
            cursor: pointer;
            transition: all 0.3s;
            margin-top: 10px;
        }
        
        .config-btn {
            background: linear-gradient(45deg, #4facfe 0%, #00f2fe 100%);
            color: white;
        }
        
        .load-btn {
            background: linear-gradient(45deg, #43e97b 0%, #38f9d7 100%);
            color: white;
        }
        
        .crawl-btn {
            background: linear-gradient(45deg, #fa709a 0%, #fee140 100%);
            color: white;
        }
        
        .config-btn:hover, .load-btn:hover, .crawl-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }
        
        .status-configured {
            color: #28a745;
            font-weight: 600;
        }
        
        .status-not-configured {
            color: #dc3545;
            font-weight: 600;
        }
        
        .tabs {
            display: flex;
            margin-bottom: 20px;
        }
        
        .tab {
            flex: 1;
            padding: 10px;
            background: #e9ecef;
            border: none;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .tab.active {
            background: #4facfe;
            color: white;
        }
        
        .tab-content {
            display: none;
        }
        
        .tab-content.active {
            display: block;
        }
        
        .file-list {
            max-height: 200px;
            overflow-y: auto;
            border: 1px solid #dee2e6;
            border-radius: 8px;
        }
        
        .file-item {
            padding: 10px;
            border-bottom: 1px solid #e9ecef;
            cursor: pointer;
            transition: background 0.3s;
        }
        
        .file-item:hover {
            background: #f8f9fa;
        }
        
        .file-item.selected {
            background: #e3f2fd;
            border-color: #4facfe;
        }
        
        .messages {
            flex: 1;
            padding: 20px;
            overflow-y: auto;
            background: #f8f9fa;
            min-height: 500px;
            max-height: 500px;
        }
        
        .message {
            margin-bottom: 15px;
            padding: 15px;
            border-radius: 12px;
            max-width: 80%;
        }
        
        .message.user {
            background: linear-gradient(45deg, #4facfe 0%, #00f2fe 100%);
            color: white;
            margin-left: auto;
        }
        
        .message.ai {
            background: white;
            border: 1px solid #dee2e6;
        }
        
        .message.error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        
        .input-area {
            padding: 20px;
            background: white;
            border-top: 1px solid #dee2e6;
        }
        
        .input-container {
            display: flex;
            gap: 10px;
        }
        
        .message-input {
            flex: 1;
            padding: 12px;
            border: 2px solid #e9ecef;
            border-radius: 25px;
            font-size: 1em;
            outline: none;
            transition: border-color 0.3s;
        }
        
        .message-input:focus {
            border-color: #4facfe;
        }
        
        .send-btn {
            padding: 12px 24px;
            background: linear-gradient(45deg, #4facfe 0%, #00f2fe 100%);
            color: white;
            border: none;
            border-radius: 25px;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.3s;
        }
        
        .send-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(79, 172, 254, 0.4);
        }
        
        .send-btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }
        
        .progress-container {
            margin-top: 15px;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 8px;
            display: none;
        }
        
        .progress-bar {
            width: 100%;
            height: 8px;
            background: #e9ecef;
            border-radius: 4px;
            overflow: hidden;
            margin-bottom: 10px;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(45deg, #4facfe 0%, #00f2fe 100%);
            transition: width 0.3s;
            width: 0%;
        }
        
        .progress-text {
            font-size: 0.9em;
            color: #666;
            text-align: center;
        }
        
        .spinner {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid #f3f3f3;
            border-top: 3px solid #4facfe;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .chat-progress {
            text-align: center;
            padding: 20px;
        }
        
        .papers-list {
            max-height: 300px;
            overflow-y: auto;
            margin-top: 15px;
        }
        
        .paper-item {
            padding: 10px;
            margin-bottom: 10px;
            background: white;
            border-radius: 8px;
            border: 1px solid #dee2e6;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 ArXiv论文智能问答系统</h1>
            <p>基于AI的学术论文智能分析与问答平台</p>
        </div>
        
        <div class="main-content">
            <div class="sidebar">
                <!-- LLM配置区域 -->
                <div class="config-section">
                    <div class="section-title">
                        🔧 LLM配置
                    </div>
                    <div class="input-group">
                        <label>模型名称:</label>
                        <input type="text" id="modelName" placeholder="例如: qwen" value="qwen">
                    </div>
                    <div class="input-group">
                        <label>端口号:</label>
                        <input type="number" id="modelPort" placeholder="9000" value="9000">
                    </div>
                    <button class="config-btn" onclick="configureLLM()">🔗 连接</button>
                    <div id="configStatus" style="margin-top: 10px;">
                        {% if llm_configured %}
                            <span class="status-configured">✅ 已连接到 {{ llm_model }}</span>
                        {% else %}
                            <span class="status-not-configured">⚠️ 请先配置LLM连接</span>
                        {% endif %}
                    </div>
                </div>
                
                <!-- 数据源选择区域 -->
                <div class="data-section">
                    <div class="section-title">
                        📁 数据源选择
                    </div>
                    
                    <div class="tabs">
                        <button class="tab active" onclick="switchTab('existing')">已有文章</button>
                        <button class="tab" onclick="switchTab('crawl')">搜索新文章</button>
                    </div>
                    
                    <!-- 已有文章选项卡 -->
                    <div id="existing" class="tab-content active">
                        <div class="file-list" id="fileList">
                            <!-- 文件列表将通过JavaScript加载 -->
                        </div>
                        <button class="load-btn" onclick="loadSelectedFile()">📂 加载选中文件</button>
                    </div>
                    
                    <!-- 搜索新文章选项卡 -->
                    <div id="crawl" class="tab-content">
                        <div class="input-group">
                            <label>摘要关键词:</label>
                            <input type="text" id="abstractKeywords" placeholder="例如: machine learning">
                        </div>
                        <div class="input-group">
                            <label>标题关键词:</label>
                            <input type="text" id="titleKeywords" placeholder="例如: neural network">
                        </div>
                        <div class="input-group">
                            <label>分类:</label>
                            <input type="text" id="categories" placeholder="例如: cs.AI" value="cs.AI">
                        </div>
                        <div class="input-group">
                            <label>作者:</label>
                            <input type="text" id="author" placeholder="作者姓名">
                        </div>
                        <div class="input-group">
                            <label>开始日期:</label>
                            <input type="date" id="startDate">
                        </div>
                        <div class="input-group">
                            <label>结束日期:</label>
                            <input type="date" id="endDate">
                        </div>
                        <div class="input-group">
                            <label>最大结果数:</label>
                            <input type="number" id="maxResults" value="10" min="1" max="50">
                        </div>
                        <div class="input-group">
                            <label>翻译选项:</label>
                            <select id="translateOption">
                                <option value="false">保持英文</option>
                                <option value="true">翻译为中文</option>
                            </select>
                        </div>
                        
                        <button class="crawl-btn" id="crawlBtn" onclick="crawlPapers()">🕷️ 开始爬取</button>
                        
                        <!-- 进度条 -->
                        <div class="progress-container" id="progressContainer">
                            <div class="progress-bar">
                                <div class="progress-fill" id="progressFill"></div>
                            </div>
                            <div class="progress-text" id="progressText">准备中...</div>
                        </div>
                    </div>
                    
                    <div id="dataStatus" style="margin-top: 15px;">
                        {% if has_papers %}
                            <span class="status-configured">✅ 已加载 {{ paper_count }} 篇论文</span>
                        {% else %}
                            <span class="status-not-configured">⚠️ 请选择数据源</span>
                        {% endif %}
                    </div>
                </div>
                
                <!-- 论文列表 -->
                <div id="papersList" class="papers-list"></div>
            </div>
            
            <!-- 聊天区域 -->
            <div class="chat-area">
                <div class="messages" id="messages">
                    <div class="message ai">
                        <strong>🤖 AI助手:</strong><br>
                        欢迎使用ArXiv论文智能问答系统！<br><br>
                        <strong>📋 使用步骤：</strong><br>
                        1. 🔧 配置LLM连接<br>
                        2. 📁 选择数据源（已有文章或搜索新文章）<br>
                        3. 💬 开始智能问答<br><br>
                        请先完成配置，然后我就可以帮您分析论文了！
                    </div>
                </div>
                
                <div class="input-area">
                    <div class="input-container">
                        <input type="text" id="messageInput" class="message-input" 
                               placeholder="请先配置LLM并加载论文数据..." 
                               onkeypress="handleKeyPress(event)" disabled>
                        <button class="send-btn" id="sendBtn" onclick="sendMessage()" disabled>发送</button>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let isConfigured = false;
        let hasPapers = false;
        let isLoading = false;
        let selectedFile = null;

        // 初始化
        document.addEventListener('DOMContentLoaded', function() {
            loadAvailableFiles();
            updateChatInterface();
            document.getElementById('messageInput').focus();
        });

        // 标签切换
        function switchTab(tabName) {
            // 隐藏所有标签内容
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });
            document.querySelectorAll('.tab').forEach(tab => {
                tab.classList.remove('active');
            });
            
            // 显示选中的标签
            document.getElementById(tabName).classList.add('active');
            event.target.classList.add('active');
        }

        // 加载可用文件
        async function loadAvailableFiles() {
            try {
                const response = await fetch('/files');
                const data = await response.json();
                const fileList = document.getElementById('fileList');
                
                if (data.files && data.files.length > 0) {
                    fileList.innerHTML = data.files.map(file => 
                        `<div class="file-item" onclick="selectFile('${file.path}', '${file.name}')" data-path="${file.path}">
                            <strong>${file.display_name}</strong><br>
                            <small>${file.count} 篇论文</small>
                        </div>`
                    ).join('');
                } else {
                    fileList.innerHTML = '<div style="padding: 20px; text-align: center; color: #666;">暂无可用文件</div>';
                }
            } catch (error) {
                document.getElementById('fileList').innerHTML = '<div style="padding: 20px; text-align: center; color: #dc3545;">加载失败</div>';
            }
        }

        // 选择文件
        function selectFile(path, name) {
            selectedFile = path;
            document.querySelectorAll('.file-item').forEach(item => {
                item.classList.remove('selected');
            });
            document.querySelector(`[data-path="${path}"]`).classList.add('selected');
        }

        // 加载选中的文件
        async function loadSelectedFile() {
            if (!selectedFile) {
                alert('请先选择一个文件');
                return;
            }

            try {
                const response = await fetch('/load', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({file_path: selectedFile})
                });
                
                const data = await response.json();
                
                if (data.success) {
                    document.getElementById('dataStatus').innerHTML = 
                        `<span class="status-configured">✅ ${data.message}</span>`;
                    hasPapers = true;
                    updateChatInterface();
                    loadPapers(); // 刷新论文列表
                } else {
                    alert('加载失败: ' + data.message);
                }
            } catch (error) {
                alert('加载失败: ' + error.message);
            }
        }

        // 爬取论文
        async function crawlPapers() {
            const crawlBtn = document.getElementById('crawlBtn');
            const originalText = crawlBtn.textContent;
            crawlBtn.disabled = true;
            crawlBtn.textContent = '🔄 爬取中...';
            
            showProgress('🔍 正在准备爬取...');
            
            const searchParams = {
                abstract_keywords: document.getElementById('abstractKeywords').value,
                title_keywords: document.getElementById('titleKeywords').value,
                categories: document.getElementById('categories').value,
                author: document.getElementById('author').value,
                start_date: document.getElementById('startDate').value.replace(/-/g, ''),
                end_date: document.getElementById('endDate').value.replace(/-/g, ''),
                max_results: document.getElementById('maxResults').value,
                translate: document.getElementById('translateOption').value === 'true'
            };
            
            try {
                updateProgress(20, '📡 连接ArXiv服务器...', '正在建立连接...');
                
                const response = await fetch('/crawl', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(searchParams)
                });
                
                updateProgress(60, '⚡ 正在处理数据...', '正在解析论文信息...');
                const data = await response.json();
                
                updateProgress(90, '💾 保存论文数据...', '正在保存到本地...');
                
                if (data.success) {
                    updateProgress(100, '✅ 爬取完成！', data.message);
                    
                    document.getElementById('dataStatus').innerHTML = 
                        `<span class="status-configured">✅ ${data.message}</span>`;
                    
                    hasPapers = true;
                    updateChatInterface();
                    loadPapers();
                    
                    // 切换到已有文章选项卡
                    setTimeout(() => {
                        switchTab('existing');
                        loadAvailableFiles();
                    }, 1000);
                } else {
                    updateProgress(0, '❌ 爬取失败', data.message);
                    alert('爬取失败: ' + data.message);
                }
            } catch (error) {
                updateProgress(0, '❌ 网络错误', error.message);
                alert('爬取失败: ' + error.message);
            } finally {
                setTimeout(() => {
                    hideProgress();
                    crawlBtn.disabled = false;
                    crawlBtn.textContent = originalText;
                }, 2000);
            }
        }

        // 配置LLM
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
                } else {
                    statusEl.innerHTML = '<span class="status-not-configured">❌ ' + data.message + '</span>';
                    isConfigured = false;
                }
                
                updateChatInterface();
            } catch (error) {
                document.getElementById('configStatus').innerHTML = '<span class="status-not-configured">❌ 连接失败: ' + error.message + '</span>';
            }
        }

        // 发送消息
        async function sendMessage() {
            if (isLoading || !isConfigured || !hasPapers) return;
            
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
                
                if (data.response && data.response.length > 0) {
                    data.response.forEach(resp => {
                        addMessage(resp.response, resp.type === 'error' ? 'error' : 'ai');
                    });
                } else {
                    addMessage('抱歉，我无法理解您的问题。', 'error');
                }
            } catch (error) {
                removeLoadingMessage();
                addMessage('发送失败: ' + error.message, 'error');
            } finally {
                setLoading(false);
            }
        }

        // 更新聊天界面状态
        function updateChatInterface() {
            const messageInput = document.getElementById('messageInput');
            const sendBtn = document.getElementById('sendBtn');
            
            if (isConfigured && hasPapers) {
                messageInput.disabled = false;
                sendBtn.disabled = false;
                messageInput.placeholder = '请输入您的问题...';
            } else if (!isConfigured) {
                messageInput.disabled = true;
                sendBtn.disabled = true;
                messageInput.placeholder = '请先配置LLM连接...';
            } else if (!hasPapers) {
                messageInput.disabled = true;
                sendBtn.disabled = true;
                messageInput.placeholder = '请先加载论文数据...';
            }
        }

        // 添加消息
        function addMessage(content, type) {
            const messages = document.getElementById('messages');
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${type}`;
            
            if (type === 'user') {
                messageDiv.innerHTML = `<strong>👤 您:</strong><br>${content}`;
            } else if (type === 'ai') {
                messageDiv.innerHTML = `<strong>🤖 AI助手:</strong><br>${content}`;
            } else {
                messageDiv.innerHTML = `<strong>⚠️ 错误:</strong><br>${content}`;
            }
            
            messages.appendChild(messageDiv);
            messages.scrollTop = messages.scrollHeight;
        }

        // 添加加载消息
        function addLoadingMessage() {
            const messages = document.getElementById('messages');
            const loadingDiv = document.createElement('div');
            loadingDiv.className = 'message';
            loadingDiv.id = 'loading-message';
            loadingDiv.innerHTML = `
                <div class="chat-progress">
                    <div class="spinner"></div>
                    <div style="margin-top: 10px;">🤔 AI正在深度分析论文内容...</div>
                    <div style="font-size: 12px; color: #666; margin-top: 5px;">请稍候，这可能需要几秒钟</div>
                </div>
            `;
            messages.appendChild(loadingDiv);
            messages.scrollTop = messages.scrollHeight;
        }

        // 移除加载消息
        function removeLoadingMessage() {
            const loadingMessage = document.getElementById('loading-message');
            if (loadingMessage) {
                loadingMessage.remove();
            }
        }

        // 设置加载状态
        function setLoading(loading) {
            isLoading = loading;
            document.getElementById('sendBtn').disabled = loading || !isConfigured || !hasPapers;
        }

        // 处理回车键
        function handleKeyPress(event) {
            if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                sendMessage();
            }
        }

        // 进度条功能
        function showProgress(text) {
            const container = document.getElementById('progressContainer');
            const progressText = document.getElementById('progressText');
            progressText.textContent = text;
            container.style.display = 'block';
        }

        function updateProgress(percent, title, detail = '') {
            const fill = document.getElementById('progressFill');
            const text = document.getElementById('progressText');
            fill.style.width = percent + '%';
            text.innerHTML = `${title}<br><small>${detail}</small>`;
        }

        function hideProgress() {
            document.getElementById('progressContainer').style.display = 'none';
        }

        // 加载论文列表
        async function loadPapers() {
            try {
                const response = await fetch('/papers');
                const data = await response.json();
                const papersList = document.getElementById('papersList');
                
                if (data.papers && data.papers.length > 0) {
                    papersList.innerHTML = '<div style="font-weight: bold; margin-bottom: 10px;">📄 论文预览</div>';
                    data.papers.slice(0, 5).forEach((paper, index) => {
                        const paperDiv = document.createElement('div');
                        paperDiv.className = 'paper-item';
                        paperDiv.innerHTML = `
                            <div style="font-weight: bold; color: #667eea;">📄 论文 ${index + 1}</div>
                            <div style="font-weight: 600; margin: 8px 0 5px 0;">${paper.title || '无标题'}</div>
                            <div style="color: #6c757d; font-size: 0.85em;">${paper.authors || '未知作者'}</div>
                        `;
                        papersList.appendChild(paperDiv);
                    });
                } else {
                    papersList.innerHTML = '';
                }
            } catch (error) {
                console.error('加载论文列表失败:', error);
            }
        }
    </script>
</body>
</html>'''


def start_simple_web_chat(args):
    """启动简化的Web聊天界面"""
    print(f"🚀 ArXiv论文智能问答系统启动中...")
    
    # 创建聊天机器人
    chatbot = SimpleWebChatBot(
        web_port=getattr(args, 'web_port', 8080),
        chat_file=getattr(args, 'chat_file', None)
    )
    
    # 创建Flask应用
    app = create_simple_app(chatbot)
    
    print(f"✅ 系统就绪！")
    print(f"📍 访问地址: http://localhost:{chatbot.web_port}")
    print(f"🔧 请在网页中配置LLM连接")
    print(f"📁 选择数据源后即可开始智能问答")
    
    # 自动打开浏览器
    def open_browser():
        time.sleep(2)
        try:
            webbrowser.open(f"http://localhost:{chatbot.web_port}")
        except:
            pass
    
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()
    
    # 启动Flask应用
    try:
        app.run(host='0.0.0.0', port=chatbot.web_port, debug=False, threaded=True)
    except KeyboardInterrupt:
        print(f"\n🛑 系统已停止")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--web_port', type=int, default=8080)
    parser.add_argument('--chat_file', default=None)
    args = parser.parse_args()
    start_simple_web_chat(args)
