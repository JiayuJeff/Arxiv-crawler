#!/usr/bin/env python3
"""
简化版启动脚本 - 直接启动Web界面
"""

import os
import sys
import json
from flask import Flask, render_template_string, request, jsonify

def create_simple_app():
    app = Flask(__name__)
    
    # 加载测试数据
    papers = []
    if os.path.exists("test_papers.json"):
        with open("test_papers.json", 'r', encoding='utf-8') as f:
            papers = json.load(f)
    
    @app.route('/')
    def home():
        return f'''
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <title>ArXiv论文智能问答系统</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
                .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .config {{ background: #e3f2fd; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
                .input-group {{ margin: 10px 0; }}
                input {{ padding: 10px; margin: 5px; border: 1px solid #ddd; border-radius: 4px; }}
                button {{ padding: 10px 20px; background: #2196F3; color: white; border: none; border-radius: 4px; cursor: pointer; }}
                button:hover {{ background: #1976D2; }}
                .status {{ margin-top: 15px; padding: 10px; border-radius: 4px; }}
                .status.success {{ background: #d4edda; color: #155724; }}
                .status.warning {{ background: #fff3cd; color: #856404; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🤖 ArXiv论文智能问答系统</h1>
                    <p>已加载 {len(papers)} 篇论文</p>
                </div>
                
                <div class="config">
                    <h3>🔧 LLM配置</h3>
                    <div class="input-group">
                        <input type="text" id="modelName" placeholder="模型名称 (如: gpt-3.5-turbo)" style="width: 300px;">
                        <input type="number" id="modelPort" placeholder="端口号" value="9000" style="width: 100px;">
                        <button onclick="configureLLM()">连接</button>
                    </div>
                    <div id="status" class="status warning">⚠️ 请先配置LLM连接</div>
                </div>
                
                <div>
                    <h3>💬 问答区域</h3>
                    <div id="messages" style="height: 300px; overflow-y: scroll; border: 1px solid #ddd; padding: 15px; margin-bottom: 15px; background: #fafafa;">
                        <p>请先配置LLM连接，然后开始提问...</p>
                    </div>
                    <div>
                        <input type="text" id="messageInput" placeholder="请输入您的问题..." style="width: 70%;">
                        <button onclick="sendMessage()" id="sendBtn" disabled>发送</button>
                    </div>
                </div>
            </div>
            
            <script>
                let isConfigured = false;
                
                async function configureLLM() {{
                    const modelName = document.getElementById('modelName').value.trim();
                    const port = parseInt(document.getElementById('modelPort').value) || 9000;
                    
                    if (!modelName) {{
                        alert('请输入模型名称');
                        return;
                    }}
                    
                    try {{
                        const response = await fetch('/configure', {{
                            method: 'POST',
                            headers: {{'Content-Type': 'application/json'}},
                            body: JSON.stringify({{model_name: modelName, port: port}})
                        }});
                        
                        const data = await response.json();
                        const statusEl = document.getElementById('status');
                        const sendBtn = document.getElementById('sendBtn');
                        
                        if (data.success) {{
                            statusEl.className = 'status success';
                            statusEl.textContent = '✅ ' + data.message;
                            isConfigured = true;
                            sendBtn.disabled = false;
                            document.getElementById('messages').innerHTML = '<p>✅ LLM连接成功！现在可以开始提问了。</p>';
                        }} else {{
                            statusEl.className = 'status warning';
                            statusEl.textContent = '❌ ' + data.message;
                            isConfigured = false;
                            sendBtn.disabled = true;
                        }}
                    }} catch (error) {{
                        document.getElementById('status').textContent = '❌ 连接失败: ' + error.message;
                    }}
                }}
                
                async function sendMessage() {{
                    if (!isConfigured) return;
                    
                    const input = document.getElementById('messageInput');
                    const message = input.value.trim();
                    if (!message) return;
                    
                    const messagesDiv = document.getElementById('messages');
                    messagesDiv.innerHTML += `<p><strong>您:</strong> ${{message}}</p>`;
                    input.value = '';
                    
                    try {{
                        messagesDiv.innerHTML += '<p><em>🤔 AI正在思考...</em></p>';
                        messagesDiv.scrollTop = messagesDiv.scrollHeight;
                        
                        const response = await fetch('/chat', {{
                            method: 'POST',
                            headers: {{'Content-Type': 'application/json'}},
                            body: JSON.stringify({{message: message}})
                        }});
                        
                        const data = await response.json();
                        
                        // 移除思考提示
                        const paragraphs = messagesDiv.getElementsByTagName('p');
                        const lastP = paragraphs[paragraphs.length - 1];
                        if (lastP && lastP.innerHTML.includes('思考')) {{
                            lastP.remove();
                        }}
                        
                        if (data.error) {{
                            messagesDiv.innerHTML += `<p style="color: red;"><strong>错误:</strong> ${{data.error}}</p>`;
                        }} else if (data.results && data.results.length > 0) {{
                            messagesDiv.innerHTML += `<p><strong>🤖 AI:</strong> ${{data.results[0].response.replace(/\\n/g, '<br>')}}</p>`;
                        }}
                        
                        messagesDiv.scrollTop = messagesDiv.scrollHeight;
                    }} catch (error) {{
                        messagesDiv.innerHTML += `<p style="color: red;">发送失败: ${{error.message}}</p>`;
                    }}
                }}
                
                // 回车发送
                document.getElementById('messageInput').addEventListener('keypress', function(e) {{
                    if (e.key === 'Enter' && isConfigured) {{
                        sendMessage();
                    }}
                }});
            </script>
        </body>
        </html>
        '''
    
    @app.route('/configure', methods=['POST'])
    def configure():
        try:
            data = request.get_json()
            model_name = data.get('model_name', '')
            port = data.get('port', 9000)
            
            # 简单的模拟配置（实际项目中这里会连接真实的LLM）
            if model_name:
                return jsonify({'success': True, 'message': f'成功连接到 {model_name} (端口: {port})'})
            else:
                return jsonify({'success': False, 'message': '请提供模型名称'})
        except Exception as e:
            return jsonify({'success': False, 'message': f'配置失败: {str(e)}'})
    
    @app.route('/chat', methods=['POST'])
    def chat():
        try:
            data = request.get_json()
            question = data.get('message', '')
            
            if not question:
                return jsonify({'error': '请输入问题'})
            
            # 简单的模拟回答（实际项目中这里会调用LLM）
            answer = f"这是对问题 '{question}' 的模拟回答。\\n\\n基于加载的 {len(papers)} 篇论文，我可以为您提供相关分析。\\n\\n注意：这是简化版本的演示回答。"
            
            return jsonify({
                'results': [{
                    'type': 'all_papers',
                    'response': answer
                }],
                'active_papers': len(papers)
            })
        except Exception as e:
            return jsonify({'error': f'处理失败: {str(e)}'})
    
    return app

def main():
    print("🚀 启动简化版ArXiv智能问答系统...")
    
    app = create_simple_app()
    
    port = 8080
    print(f"📱 服务地址: http://localhost:{{port}}")
    print(f"🔧 在网页中配置LLM连接后即可使用")
    print(f"🛑 按 Ctrl+C 退出")
    print("-" * 50)
    
    try:
        app.run(host='0.0.0.0', port=port, debug=False)
    except KeyboardInterrupt:
        print("\\n🛑 程序已停止")
    except Exception as e:
        print(f"❌ 启动失败: {{e}}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
