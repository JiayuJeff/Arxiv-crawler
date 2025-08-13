#!/usr/bin/env python3
"""
ArXiv网页版聊天功能演示
"""

import json
import os
import sys

def show_features():
    """展示新功能特点"""
    print("🎉 ArXiv网页版聊天系统新功能：")
    print()
    print("✨ 主要特性:")
    print("  1. 🌐 网页版聊天界面 - 美观的UI设计")
    print("  2. 🧠 智能加载策略:")
    print("     - 小于max_load_files: 批量处理所有论文")
    print("     - 大于max_load_files: 逐篇加载处理")
    print("  3. 📝 对话记录保存 - 每轮对话自动保存到conversation字段")
    print("  4. ⏭️  论文跳过功能 - 可跳过不感兴趣的论文")
    print("  5. 🔄 实时状态显示 - 显示活跃论文数量和处理模式")
    print()
    print("🎯 使用方法:")
    print("  基本命令:")
    print("    python main.py --chat_file <文件> --translate_llm <模型> --port <端口> --web")
    print()
    print("  完整示例:")
    print("    python main.py \\")
    print("      --chat_file tool-rl/output.json \\")
    print("      --translate_llm 'Qwen/Qwen3-32B' \\")
    print("      --port 10006 \\")
    print("      --web \\")
    print("      --max_load_files 5 \\")
    print("      --web_port 8080")
    print()
    print("🌟 新增参数说明:")
    print("  --web                启用网页版界面")
    print("  --max_load_files N   最大同时加载论文数 (默认: 10)")
    print("  --web_port PORT      网页服务器端口 (默认: 8080)")
    print()

def check_requirements():
    """检查运行要求"""
    print("🔍 检查运行要求:")
    
    # 检查文件
    test_file = "tool-rl/output.json"
    if os.path.exists(test_file):
        print(f"  ✅ 测试文件存在: {test_file}")
        with open(test_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"  📊 包含 {len(data)} 篇论文")
    else:
        print(f"  ❌ 测试文件不存在: {test_file}")
        return False
    
    # 检查库
    try:
        import flask
        print(f"  ✅ Flask已安装: {flask.__version__}")
    except ImportError:
        print("  ❌ Flask未安装，请运行: pip install flask")
        return False
    
    try:
        import openai
        print(f"  ✅ OpenAI已安装: {openai.__version__}")
    except ImportError:
        print("  ❌ OpenAI未安装，请运行: pip install openai")
        return False
    
    print("  ✅ 所有依赖已安装")
    return True

def show_data_structure():
    """展示数据结构变化"""
    print("\n📋 数据结构说明:")
    print("每篇论文的JSON结构现在包含:")
    print("""
{
  "arxiv_id": "2507.21836v1",
  "title": "论文标题",
  "abstract": "英文摘要",
  "abstract_cn": "中文摘要",
  "authors": ["作者1", "作者2"],
  "published": "2025-07-29T14:12:28Z",
  "categories": ["cs.CL"],
  "page_url": "论文链接",
  "pdf_url": "PDF链接",
  "_paper_id": 1,                    // 新增: 论文唯一ID
  "conversation": [                  // 新增: 对话记录
    {
      "question": "用户问题",
      "response": "AI回答"
    },
    {
      "question": "第二轮问题", 
      "response": "第二轮回答"
    }
  ]
}""")

def main():
    """主函数"""
    print("=" * 60)
    print("  🤖 ArXiv网页版聊天系统演示")
    print("=" * 60)
    
    show_features()
    
    if not check_requirements():
        print("\n❌ 环境检查失败，请安装缺失的依赖")
        return
    
    show_data_structure()
    
    print("\n🚀 启动说明:")
    print("1. 确保LLM服务在指定端口运行 (如: http://localhost:10006)")
    print("2. 运行启动命令")
    print("3. 在浏览器中访问 http://localhost:8080")
    print("4. 开始与论文进行智能对话!")
    
    print("\n💡 使用建议:")
    print("- max_load_files=1: 适合详细分析每篇论文")
    print("- max_load_files>=论文数: 适合概览和对比分析")
    print("- 使用跳过功能过滤不相关的论文")
    print("- 对话记录会自动保存，支持多轮深入讨论")
    
    print("\n" + "=" * 60)
    print("✨ 准备就绪！您可以开始使用新的网页版聊天功能了！")
    print("=" * 60)

if __name__ == "__main__":
    main()
