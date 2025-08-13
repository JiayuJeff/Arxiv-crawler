#!/usr/bin/env python3
"""
ArXiv爬虫使用示例
这个文件包含了各种使用场景的示例命令
"""

import subprocess
import sys
import os

def run_example(name, cmd, description):
    """运行示例命令"""
    print(f"\n{'='*60}")
    print(f"示例: {name}")
    print(f"描述: {description}")
    print(f"命令: {cmd}")
    print(f"{'='*60}")
    
    # 提示用户是否运行
    response = input("是否运行此示例? (y/n): ").strip().lower()
    if response in ['y', 'yes']:
        try:
            subprocess.run(cmd, shell=True, check=True)
        except subprocess.CalledProcessError as e:
            print(f"命令执行失败: {e}")
    else:
        print("跳过执行")

def main():
    """运行所有示例"""
    
    # 确保在正确的目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    examples = [
        {
            "name": "基础搜索",
            "cmd": "python main.py --abstract-keywords 'machine learning' --max-results 5 --output basic_search.json --translate_llm qwen --show-abstracts",
            "description": "在摘要中搜索'machine learning'关键词，返回5篇文章并翻译"
        },
        {
            "name": "复杂逻辑搜索",
            "cmd": "python main.py --keywords-all 'transformer' 'attention' --keywords-not 'survey' 'review' --categories cs.AI cs.CL --max-results 10 --output complex_search.json --translate_llm qwen",
            "description": "同时包含transformer和attention，但不包含survey或review，限定AI和计算语言学分类"
        },
        {
            "name": "作者搜索",
            "cmd": "python main.py --author 'Yoshua Bengio' --max-results 5 --output author_search.json --translate_llm qwen --sort-by lastUpdatedDate",
            "description": "搜索Yoshua Bengio的最新论文"
        },
        {
            "name": "时间范围搜索",
            "cmd": "python main.py --title-keywords 'large language model' --start-date 20240101 --end-date 20241231 --max-results 20 --output recent_llm.json --translate_llm qwen",
            "description": "搜索2024年关于大语言模型的论文"
        },
        {
            "name": "仅查看查询语句",
            "cmd": "python main.py --abstract-keywords 'deep learning' 'neural network' --show-query --max-results 1 --output test.json --translate_llm qwen",
            "description": "显示构建的API查询语句（调试用）"
        },
        {
            "name": "CSV格式输出",
            "cmd": "python main.py --keywords-any 'BERT' 'GPT' 'transformer' --categories cs.CL --max-results 15 --output nlp_models.csv --translate_llm qwen",
            "description": "搜索NLP模型相关论文并保存为CSV格式"
        },
        {
            "name": "测试问答功能",
            "cmd": "python chat.py --output test_papers.json --translate_llm qwen",
            "description": "基于测试数据进行问答交互"
        }
    ]
    
    print("ArXiv爬虫使用示例")
    print("注意: 这些示例需要LLM服务在指定端口运行")
    print("如果没有LLM服务，请移除 --translate_llm 参数")
    
    for i, example in enumerate(examples, 1):
        print(f"\n{i}. {example['name']}")
        print(f"   {example['description']}")
    
    print("\n请选择要运行的示例 (1-{}, 0=全部, q=退出):".format(len(examples)), end=" ")
    choice = input().strip()
    
    if choice.lower() == 'q':
        print("退出")
        return
    
    try:
        if choice == '0':
            # 运行所有示例
            for example in examples:
                run_example(example['name'], example['cmd'], example['description'])
        else:
            # 运行指定示例
            idx = int(choice) - 1
            if 0 <= idx < len(examples):
                example = examples[idx]
                run_example(example['name'], example['cmd'], example['description'])
            else:
                print("无效选择")
    except ValueError:
        print("请输入有效数字")

if __name__ == "__main__":
    main()
