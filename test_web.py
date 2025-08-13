#!/usr/bin/env python3
"""
测试网页版聊天功能
"""

import sys
import os

# 添加当前目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from web_chat import start_web_chat
import argparse

class TestArgs:
    def __init__(self):
        self.output = "tool-rl/output.json"
        self.translate_llm = "Qwen/Qwen3-32B"
        self.port = 10006
        self.max_load_files = 1  # 设置为1来测试逐篇处理模式
        self.web_port = 8080

if __name__ == "__main__":
    print("启动测试网页版聊天...")
    args = TestArgs()
    
    # 检查文件是否存在
    if not os.path.exists(args.output):
        print(f"错误: 文件不存在 {args.output}")
        sys.exit(1)
    
    print(f"使用文件: {args.output}")
    print(f"最大加载文件数: {args.max_load_files}")
    print(f"网页端口: {args.web_port}")
    
    try:
        start_web_chat(args)
    except KeyboardInterrupt:
        print("\n已退出")
    except Exception as e:
        print(f"错误: {e}")
