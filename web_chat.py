#!/usr/bin/env python3
"""
ArXiv论文网页版问答模块
提供基于Flask的网页聊天界面
"""

import json
import os
import webbrowser
import threading
import time
from flask import Flask, render_template, request, jsonify
from typing import List, Dict, Optional

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
    print(f"\n{'='*60}")
    print(f"🚀 ArXiv论文智能问答系统")
    print(f"{'='*60}")
    print(f"📁 数据文件: {args.output}")
    print(f"🤖 AI模型: {args.translate_llm}")
    print(f"🌐 LLM服务: http://0.0.0.0:{args.port}")
    print(f"📊 加载策略: {'批量处理' if args.max_load_files >= 50 else '逐篇处理'} (阈值: {args.max_load_files})")
    print(f"🔗 网页端口: {args.web_port}")
    
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
        
        print(f"\n🎯 系统准备就绪!")
        print(f"📱 网页地址: http://localhost:{args.web_port}")
        print(f"� 已加载 {len(chatbot.papers)} 篇论文")
        print(f"💬 {'批量模式: 所有论文一起分析' if len(chatbot.papers) <= args.max_load_files else '逐篇模式: 每篇论文单独分析'}")
        print(f"{'='*60}")
        print(f"🌟 浏览器即将自动打开...")
        print(f"⚠️  如未自动打开，请手动访问上述地址")
        print(f"� 按 Ctrl+C 退出")
        print(f"{'='*60}")
        
        # 延迟后自动打开浏览器
        def open_browser():
            time.sleep(2)  # 等待服务器启动
            url = f"http://localhost:{args.web_port}"
            try:
                webbrowser.open(url)
                print(f"✅ 浏览器已打开: {url}")
            except Exception as e:
                print(f"⚠️  无法自动打开浏览器: {e}")
                print(f"📝 请手动打开: {url}")
        
        # 在后台线程中打开浏览器
        browser_thread = threading.Thread(target=open_browser)
        browser_thread.daemon = True
        browser_thread.start()
        
        # 启动Flask服务器
        app.run(host='0.0.0.0', port=args.web_port, debug=False, use_reloader=False)
        
    except KeyboardInterrupt:
        print(f"\n\n{'='*60}")
        print(f"👋 感谢使用ArXiv论文智能问答系统!")
        print(f"{'='*60}")
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        print(f"\n🔧 故障排除建议:")
        print(f"1. 检查LLM服务是否在端口 {args.port} 运行")
        print(f"2. 确认数据文件 {args.output} 存在且格式正确")
        print(f"3. 检查端口 {args.web_port} 是否被占用")
        return


def create_templates():
    """创建HTML模板"""
    os.makedirs('templates', exist_ok=True)
    
    html_content = '''<!DOCTYPE html>
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
        
        .header::before {
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: repeating-linear-gradient(
                45deg,
                transparent,
                transparent 10px,
                rgba(255,255,255,0.05) 10px,
                rgba(255,255,255,0.05) 20px
            );
            animation: movePattern 20s linear infinite;
        }
        
        @keyframes movePattern {
            0% { transform: translate(0, 0); }
            100% { transform: translate(50px, 50px); }
        }
        
        .header h1 {
            font-size: 2.2em;
            margin-bottom: 10px;
            font-weight: 700;
            position: relative;
            z-index: 1;
        }
        
        .header .subtitle {
            font-size: 1.1em;
            opacity: 0.9;
            position: relative;
            z-index: 1;
        }
        
        .status {
            background: rgba(255,255,255,0.2);
            padding: 15px;
            border-radius: 12px;
            margin-top: 15px;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 10px;
            position: relative;
            z-index: 1;
        }
        
        .status-item {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .status-item .icon {
            font-size: 1.2em;
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
            position: relative;
        }
        
        .user-message::before {
            content: '👤';
            position: absolute;
            left: -30px;
            top: 50%;
            transform: translateY(-50%);
            font-size: 1.2em;
            background: white;
            border-radius: 50%;
            width: 25px;
            height: 25px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .ai-message {
            background: white;
            border: 2px solid #e9ecef;
            padding: 18px 24px;
            border-radius: 25px 25px 25px 8px;
            margin-right: 15%;
            word-wrap: break-word;
            box-shadow: 0 4px 15px rgba(0,0,0,0.05);
            position: relative;
        }
        
        .ai-message::before {
            content: '🤖';
            position: absolute;
            right: -30px;
            top: 50%;
            transform: translateY(-50%);
            font-size: 1.2em;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 50%;
            width: 25px;
            height: 25px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .paper-info {
            background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%);
            border: 1px solid #ffd700;
            padding: 12px 16px;
            border-radius: 12px;
            margin-bottom: 12px;
            font-size: 0.9em;
            box-shadow: 0 2px 8px rgba(255, 215, 0, 0.2);
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
            text-transform: uppercase;
            letter-spacing: 0.5px;
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
        
        .btn-secondary {
            background: linear-gradient(135deg, #6c757d 0%, #5a6268 100%);
            color: white;
            box-shadow: 0 4px 15px rgba(108, 117, 125, 0.3);
        }
        
        .btn-secondary:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(108, 117, 125, 0.4);
        }
        
        .btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none !important;
        }
        
        .btn-group {
            display: flex;
            gap: 12px;
        }
        
        .sidebar {
            width: 320px;
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            padding: 25px;
            overflow-y: auto;
            border-left: 2px solid #eee;
        }
        
        .sidebar h3 {
            margin-bottom: 18px;
            color: #495057;
            font-weight: 700;
            font-size: 1.1em;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .skip-section {
            margin-bottom: 35px;
        }
        
        .skip-input {
            width: 100%;
            padding: 12px 16px;
            border: 2px solid #dee2e6;
            border-radius: 12px;
            margin-bottom: 12px;
            background: white;
            transition: border-color 0.3s ease;
        }
        
        .skip-input:focus {
            border-color: #667eea;
            outline: none;
        }
        
        .papers-list {
            max-height: 450px;
            overflow-y: auto;
        }
        
        .paper-item {
            background: white;
            border: 2px solid #dee2e6;
            border-radius: 12px;
            padding: 15px;
            margin-bottom: 12px;
            font-size: 0.9em;
            transition: all 0.3s ease;
        }
        
        .paper-item:hover {
            border-color: #667eea;
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }
        
        .paper-item.skipped {
            background: #f8d7da;
            border-color: #f5c6cb;
            opacity: 0.7;
        }
        
        .paper-id {
            font-weight: bold;
            color: #667eea;
            font-size: 1em;
        }
        
        .paper-title {
            font-weight: 600;
            margin: 8px 0 5px 0;
            color: #2c3e50;
        }
        
        .paper-authors {
            color: #6c757d;
            font-size: 0.85em;
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
        
        .welcome-message {
            background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
            border: 2px solid #2196f3;
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 20px;
            text-align: center;
        }
        
        .welcome-message h3 {
            color: #1976d2;
            margin-bottom: 15px;
            font-size: 1.3em;
        }
        
        .welcome-message p {
            color: #0d47a1;
            margin-bottom: 10px;
        }
        
        .quick-questions {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 10px;
            margin-top: 15px;
        }
        
        .quick-question {
            background: white;
            border: 1px solid #2196f3;
            border-radius: 8px;
            padding: 10px;
            cursor: pointer;
            transition: all 0.3s ease;
            font-size: 0.9em;
        }
        
        .quick-question:hover {
            background: #2196f3;
            color: white;
            transform: translateY(-2px);
        }
        
        @media (max-width: 768px) {
            .container {
                height: 100vh;
                border-radius: 0;
                margin: 0;
            }
            
            body {
                padding: 0;
            }
            
            .main-content {
                flex-direction: column;
            }
            
            .sidebar {
                width: 100%;
                max-height: 300px;
                border-left: none;
                border-top: 2px solid #eee;
            }
            
            .user-message, .ai-message {
                margin-left: 5%;
                margin-right: 5%;
            }
            
            .user-message::before, .ai-message::before {
                display: none;
            }
        }
        
        /* 滚动条样式 */
        ::-webkit-scrollbar {
            width: 8px;
        }
        
        ::-webkit-scrollbar-track {
            background: #f1f1f1;
            border-radius: 4px;
        }
        
        ::-webkit-scrollbar-thumb {
            background: #667eea;
            border-radius: 4px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: #5a67d8;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 ArXiv论文智能问答系统</h1>
            <p class="subtitle">基于AI的学术论文智能分析平台</p>
            <div class="status">
                <div class="status-item">
                    <span class="icon">📚</span>
                    <span>已加载: <strong id="paperCount">{{ paper_count }}</strong> 篇论文</span>
                </div>
                <div class="status-item">
                    <span class="icon">🔄</span>
                    <span>模式: <strong id="processMode">{{ '批量处理' if paper_count <= max_load_files else '逐篇处理' }}</strong></span>
                </div>
                <div class="status-item">
                    <span class="icon">✅</span>
                    <span>活跃: <strong id="activePapers">{{ paper_count }}</strong> 篇</span>
                </div>
            </div>
        </div>
        
        <div class="main-content">
            <div class="chat-area">
                <div class="messages" id="messages">
                    <div class="welcome-message">
                        <h3>🎉 欢迎使用ArXiv论文智能问答系统！</h3>
                        <p>💡 您可以询问关于已加载论文的任何问题</p>
                        <p>🔍 支持主题搜索、论文对比、技术分析等</p>
                        <p>📝 在右侧可以管理和跳过不感兴趣的论文</p>
                        
                        <div class="quick-questions">
                            <div class="quick-question" onclick="askQuestion('这些论文的主要研究方向是什么？')">
                                📊 研究方向分析
                            </div>
                            <div class="quick-question" onclick="askQuestion('总结这些论文的核心贡献')">
                                🎯 核心贡献总结
                            </div>
                            <div class="quick-question" onclick="askQuestion('比较不同论文的方法优缺点')">
                                ⚖️ 方法对比分析
                            </div>
                            <div class="quick-question" onclick="askQuestion('有哪些值得关注的技术创新？')">
                                💡 技术创新点
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="input-area">
                    <div class="input-group">
                        <input type="text" id="messageInput" placeholder="请输入您的问题，如：这些论文的主要技术特点是什么？" onkeypress="handleKeyPress(event)">
                        <button class="btn btn-primary" onclick="sendMessage()" id="sendBtn">
                            <span id="sendBtnText">发送</span>
                        </button>
                    </div>
                    <div class="btn-group">
                        <button class="btn btn-secondary" onclick="clearChat()">🗑️ 清空对话</button>
                        <button class="btn btn-secondary" onclick="showHelp()">❓ 使用帮助</button>
                    </div>
                </div>
            </div>
            
            <div class="sidebar">
                <div class="skip-section">
                    <h3>📋 论文管理</h3>
                    <input type="text" class="skip-input" id="skipInput" placeholder="输入要跳过的论文编号(如: 1,3,5)">
                    <div class="btn-group">
                        <button class="btn btn-secondary" onclick="skipPapers()" style="flex: 1;">⏭️ 跳过选中</button>
                        <button class="btn btn-secondary" onclick="clearSkipped()" style="flex: 1;">🔄 全部恢复</button>
                    </div>
                </div>
                
                <div>
                    <h3>📚 论文列表</h3>
                    <div class="papers-list" id="papersList">
                        <div class="loading">
                            <div class="spinner"></div>
                            正在加载论文列表...
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let isLoading = false;

        function askQuestion(question) {
            document.getElementById('messageInput').value = question;
            sendMessage();
        }

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
                            const paperInfo = `📄 论文 ${result.paper_id}: ${result.paper_title}`;
                            addMessage(result.response, 'ai', paperInfo);
                        } else if (result.type === 'error') {
                            const errorInfo = result.paper_id ? `📄 论文 ${result.paper_id}: ${result.paper_title}` : '';
                            addMessage(result.response, 'error', errorInfo);
                        }
                    });
                    
                    // 更新活跃论文数量
                    document.getElementById('activePapers').textContent = data.active_papers;
                }
            } catch (error) {
                removeLoadingMessage();
                addMessage('❌ 发送失败: ' + error.message, 'error');
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
            const sendBtnText = document.getElementById('sendBtnText');
            const messageInput = document.getElementById('messageInput');
            
            sendBtn.disabled = loading;
            messageInput.disabled = loading;
            sendBtnText.textContent = loading ? '处理中...' : '发送';
            
            if (loading) {
                sendBtn.style.background = '#6c757d';
            } else {
                sendBtn.style.background = '';
            }
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
                    addMessage('✅ ' + data.message, 'ai');
                    document.getElementById('activePapers').textContent = data.active_papers;
                    skipInput.value = '';
                    loadPapers(); // 重新加载论文列表
                } else {
                    addMessage('❌ ' + data.error, 'error');
                }
            } catch (error) {
                addMessage('❌ 操作失败: ' + error.message, 'error');
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
                    addMessage('✅ ' + data.message, 'ai');
                    document.getElementById('activePapers').textContent = data.active_papers;
                    loadPapers(); // 重新加载论文列表
                } else {
                    addMessage('❌ ' + data.error, 'error');
                }
            } catch (error) {
                addMessage('❌ 操作失败: ' + error.message, 'error');
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
                        <div class="paper-id">📄 论文 ${paper.id}</div>
                        <div class="paper-title">${paper.title}</div>
                        <div class="paper-authors">${paper.authors}</div>
                        ${paper.skipped ? '<div style="color: #dc3545; font-size: 0.8em; margin-top: 5px;">⏭️ 已跳过</div>' : ''}
                    `;
                    papersList.appendChild(paperDiv);
                });
            } catch (error) {
                document.getElementById('papersList').innerHTML = '<div class="error-message">❌ 加载失败</div>';
            }
        }

        function clearChat() {
            const messages = document.getElementById('messages');
            messages.innerHTML = `
                <div class="welcome-message">
                    <h3>🎉 欢迎使用ArXiv论文智能问答系统！</h3>
                    <p>💡 您可以询问关于已加载论文的任何问题</p>
                    <p>🔍 支持主题搜索、论文对比、技术分析等</p>
                    <p>📝 在右侧可以管理和跳过不感兴趣的论文</p>
                    
                    <div class="quick-questions">
                        <div class="quick-question" onclick="askQuestion('这些论文的主要研究方向是什么？')">
                            📊 研究方向分析
                        </div>
                        <div class="quick-question" onclick="askQuestion('总结这些论文的核心贡献')">
                            🎯 核心贡献总结
                        </div>
                        <div class="quick-question" onclick="askQuestion('比较不同论文的方法优缺点')">
                            ⚖️ 方法对比分析
                        </div>
                        <div class="quick-question" onclick="askQuestion('有哪些值得关注的技术创新？')">
                            💡 技术创新点
                        </div>
                    </div>
                </div>
            `;
        }

        function showHelp() {
            addMessage(`
                <h3>📖 使用帮助</h3>
                <p><strong>🎯 问答功能：</strong></p>
                <ul>
                    <li>📊 研究总结：询问论文的研究方向、核心贡献等</li>
                    <li>🔍 技术分析：了解具体的技术方法和创新点</li>
                    <li>⚖️ 对比分析：比较不同论文的方法和结果</li>
                    <li>📝 细节查询：询问特定论文的详细信息</li>
                </ul>
                <p><strong>📋 论文管理：</strong></p>
                <ul>
                    <li>⏭️ 跳过论文：输入编号（如1,3,5）跳过不感兴趣的论文</li>
                    <li>🔄 恢复论文：清空跳过列表恢复所有论文</li>
                    <li>📚 查看列表：右侧显示所有论文状态</li>
                </ul>
                <p><strong>💡 使用技巧：</strong></p>
                <ul>
                    <li>🎪 点击快捷问题按钮快速开始</li>
                    <li>🔄 支持多轮对话，可以深入讨论</li>
                    <li>📱 支持移动端，随时随地使用</li>
                </ul>
            `, 'ai');
        }

        // 页面加载时初始化
        document.addEventListener('DOMContentLoaded', function() {
            loadPapers();
            document.getElementById('messageInput').focus();
            
            // 添加欢迎音效（可选）
            setTimeout(() => {
                console.log('🎉 ArXiv论文智能问答系统已就绪！');
            }, 1000);
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
