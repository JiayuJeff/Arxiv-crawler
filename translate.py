#!/usr/bin/env python3
"""
ArXiv文章摘要翻译模块
使用指定的LLM将英文摘要翻译为中文
"""

import json
import asyncio
import aiohttp
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

from tqdm import tqdm

try:
    from openai import OpenAI
except ImportError:
    print("Warning: openai库未安装。请运行: pip install openai")
    OpenAI = None


class ArxivTranslator:
    def __init__(self, model_name: str, port: int, host: str = "0.0.0.0"):
        """
        初始化翻译器
        
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
            api_key="EMPTY",  # 本地服务通常不需要真实key
            base_url=self.base_url
        )
        
        # 翻译提示词
        self.system_prompt = """你是一个专业的学术论文翻译专家。请将用户提供的英文摘要翻译成中文。

翻译要求：
1. 保持学术术语的准确性
2. 语言流畅自然，符合中文表达习惯
3. 保持原文的逻辑结构和技术细节
4. 只输出翻译结果，不要包含任何解释或额外内容

请直接输出翻译后的中文内容。"""

    def translate_single_abstract(self, abstract: str) -> str:
        """
        翻译单个摘要
        
        Args:
            abstract: 英文摘要
            
        Returns:
            中文翻译
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": abstract}
                ],
                temperature=0.3,
                max_tokens=2048
            )
            
            translation = response.choices[0].message.content.strip()
            return translation
            
        except Exception as e:
            print(f"翻译失败: {e}")
            return abstract  # 如果翻译失败，返回原文
    
    def translate_abstracts_batch(self, papers: List[Dict], batch_size: int = 5) -> List[Dict]:
        """
        批量翻译摘要
        
        Args:
            papers: 包含摘要的论文列表
            batch_size: 并发数量
            
        Returns:
            添加了中文摘要的论文列表
        """
        print(f"开始翻译 {len(papers)} 篇文章的摘要...")
        print(f"使用模型: {self.model_name}")
        print(f"服务地址: {self.base_url}")
        print(f"并发数量: {batch_size}")
        
        # 过滤出有摘要的文章
        papers_with_abstracts = [p for p in papers if p.get('abstract')]
        print(f"其中 {len(papers_with_abstracts)} 篇文章有摘要需要翻译")
        
        # 使用线程池进行并发翻译
        with ThreadPoolExecutor(max_workers=batch_size) as executor:
            # 提交翻译任务
            future_to_paper = {}
            for paper in papers_with_abstracts:
                abstract = paper.get('abstract', '')
                if abstract:
                    future = executor.submit(self.translate_single_abstract, abstract)
                    future_to_paper[future] = paper
            
            # 收集翻译结果
            completed_count = 0
            for future in tqdm(as_completed(future_to_paper), total=len(future_to_paper)):
                paper = future_to_paper[future]
                try:
                    translation = future.result()
                    paper['abstract_cn'] = translation
                    completed_count += 1
                    
                    # 显示进度
                    if completed_count % max(1, len(papers_with_abstracts) // 10) == 0:
                        progress = (completed_count / len(papers_with_abstracts)) * 100
                        print(f"翻译进度: {completed_count}/{len(papers_with_abstracts)} ({progress:.1f}%)")
                
                except Exception as e:
                    print(f"翻译论文 {paper.get('arxiv_id', 'unknown')} 时出错: {e}")
                    paper['abstract_cn'] = paper.get('abstract', '')  # 翻译失败时使用原文
        
        print(f"翻译完成! 共处理 {len(papers_with_abstracts)} 篇文章")
        return papers


def translate(args):
    """
    翻译函数，处理爬虫输出的文件
    
    Args:
        args: 包含翻译参数的对象，应该有以下属性：
            - output: 输入/输出文件路径
            - translate_llm: 翻译模型名称
            - port: 服务端口
            - batchsize: 并发数量
    """
    input_file = args.output  # 使用爬虫的输出文件作为输入
    
    print(f"\n=== 开始翻译阶段 ===")
    print(f"输入文件: {input_file}")
    
    # 读取JSON文件
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            papers = json.load(f)
        print(f"成功读取 {len(papers)} 篇文章")
    except Exception as e:
        print(f"读取文件失败: {e}")
        return
    
    # 创建翻译器并翻译
    translator = ArxivTranslator(
        model_name=args.translate_llm,
        port=args.port,
    )
    
    # 执行翻译
    translated_papers = translator.translate_abstracts_batch(
        papers=papers,
        batch_size=args.batchsize
    )
    
    # 保存结果到原文件(不保留think token)
    for paper_item in translated_papers:
        abs_cn = paper_item.get('abstract_cn', '')
        if abs_cn and '</think>' in abs_cn:
            paper_item['abstract_cn'] = abs_cn.split('</think>')[-1]
    try:
        with open(input_file, 'w', encoding='utf-8') as f:
            json.dump(translated_papers, f, ensure_ascii=False, indent=2)
        print(f"翻译结果已保存到: {input_file}")
    except Exception as e:
        print(f"保存文件失败: {e}")
        return
    
    print("=== 翻译阶段完成 ===\n")


if __name__ == "__main__":
    # 测试用的简单参数
    class Args:
        def __init__(self):
            self.output = "test.json"
            self.translate_llm = "gpt-3.5-turbo"
            self.port = 5000
            self.batchsize = 3
    
    # 创建测试数据
    test_data = [
        {
            "arxiv_id": "test1",
            "title": "Test Paper 1",
            "abstract": "This is a test abstract for machine learning research.",
            "authors": ["Test Author"]
        },
        {
            "arxiv_id": "test2", 
            "title": "Test Paper 2",
            "abstract": "Another test abstract about artificial intelligence.",
            "authors": ["Another Author"]
        }
    ]
    
    # 保存测试数据
    with open("test/test.json", 'w', encoding='utf-8') as f:
        json.dump(test_data, f, ensure_ascii=False, indent=2)
    
    # 测试翻译
    args = Args()
    translate(args)
