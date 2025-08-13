#!/usr/bin/env python3
"""
ArXiv爬取问题诊断工具
用于调试为什么获取的文章数量少于期望值
"""

import requests
import xml.etree.ElementTree as ET
from urllib.parse import urlencode

def test_arxiv_api(search_query, max_results=100):
    """
    直接测试ArXiv API响应
    """
    base_url = "http://export.arxiv.org/api/query"
    
    print(f"🔍 测试查询: {search_query}")
    print(f"📊 期望最大结果数: {max_results}")
    print("-" * 60)
    
    # 测试不同的批次大小
    batch_sizes = [50, 100, 200]
    
    for batch_size in batch_sizes:
        current_batch = min(batch_size, max_results)
        params = {
            'search_query': search_query,
            'start': 0,
            'max_results': current_batch,
            'sortBy': 'submittedDate',
            'sortOrder': 'descending'
        }
        
        print(f"\n📦 测试批次大小: {current_batch}")
        print(f"🌐 请求URL: {base_url}?{urlencode(params)}")
        
        try:
            response = requests.get(base_url, params=params)
            response.raise_for_status()
            
            # 解析XML
            root = ET.fromstring(response.text)
            namespaces = {
                'atom': 'http://www.w3.org/2005/Atom',
                'opensearch': 'http://a9.com/-/spec/opensearch/1.1/',
            }
            
            # 获取总结果数
            total_results = root.find('opensearch:totalResults', namespaces)
            start_index = root.find('opensearch:startIndex', namespaces)
            items_per_page = root.find('opensearch:itemsPerPage', namespaces)
            
            # 计算实际条目数
            entries = root.findall('atom:entry', namespaces)
            
            print(f"📈 ArXiv报告的总结果数: {total_results.text if total_results is not None else 'Unknown'}")
            print(f"📌 起始索引: {start_index.text if start_index is not None else 'Unknown'}")
            print(f"📄 每页条目数: {items_per_page.text if items_per_page is not None else 'Unknown'}")
            print(f"✅ 实际返回的条目数: {len(entries)}")
            
            # 显示前几篇文章的信息
            print(f"\n📋 前3篇文章预览:")
            for i, entry in enumerate(entries[:3]):
                title_elem = entry.find('atom:title', namespaces)
                id_elem = entry.find('atom:id', namespaces)
                
                title = title_elem.text.strip() if title_elem is not None else "No title"
                arxiv_id = id_elem.text.split('/')[-1] if id_elem is not None else "No ID"
                
                print(f"  {i+1}. [{arxiv_id}] {title[:60]}...")
            
        except Exception as e:
            print(f"❌ 请求失败: {e}")
        
        print("-" * 40)

def analyze_search_query(search_query):
    """
    分析搜索查询的有效性
    """
    print(f"\n🔎 搜索查询分析:")
    print(f"原始查询: {search_query}")
    
    # 检查查询的组成部分
    parts = search_query.split(' AND ')
    print(f"查询组件数: {len(parts)}")
    
    for i, part in enumerate(parts, 1):
        print(f"  组件 {i}: {part}")
        
        # 分析每个组件
        if 'abs:' in part:
            keyword = part.replace('abs:', '').strip('"')
            print(f"    → 摘要关键词: '{keyword}'")
        elif 'submittedDate:' in part:
            date_range = part.replace('submittedDate:', '')
            print(f"    → 提交日期范围: {date_range}")
        elif 'cat:' in part:
            category = part.replace('cat:', '')
            print(f"    → 分类: {category}")

def suggest_alternatives(search_query, actual_results, expected_results):
    """
    建议替代搜索策略
    """
    print(f"\n💡 优化建议:")
    
    if actual_results < expected_results:
        print(f"📉 获得 {actual_results} 篇，期望 {expected_results} 篇")
        print(f"\n🔧 可能的优化策略:")
        
        # 建议放宽搜索条件
        if ' AND ' in search_query:
            print("1. 使用 OR 替代部分 AND 条件，扩大搜索范围")
            alternative = search_query.replace(' AND abs:', ' OR abs:')
            print(f"   示例: {alternative}")
        
        # 建议使用更通用的关键词
        if '"' in search_query:
            print("2. 移除引号，使用更宽泛的关键词匹配")
            alternative = search_query.replace('"', '')
            print(f"   示例: {alternative}")
        
        # 建议扩大时间范围
        if 'submittedDate:' in search_query:
            print("3. 扩大时间范围")
            print("   示例: 将开始日期提前1年")
        
        # 建议使用title搜索
        if 'abs:' in search_query and 'ti:' not in search_query:
            print("4. 添加标题搜索")
            title_query = search_query.replace('abs:', 'ti:')
            combined = f"({search_query}) OR ({title_query})"
            print(f"   示例: {combined}")

def main():
    """主函数"""
    print("=" * 60)
    print("🔍 ArXiv爬取问题诊断工具")
    print("=" * 60)
    
    # 使用您的实际查询参数
    search_query = 'abs:"tool use" AND abs:cost AND submittedDate:[20240101 TO 20250805]'
    max_results = 100
    
    # 分析查询
    analyze_search_query(search_query)
    
    # 测试API响应
    test_arxiv_api(search_query, max_results)
    
    # 提供建议
    suggest_alternatives(search_query, 25, max_results)  # 基于您的实际结果
    
    print(f"\n" + "=" * 60)
    print("🎯 总结:")
    print("ArXiv API有时会返回少于请求数量的结果，这是正常现象。")
    print("这通常表示数据库中匹配的文章确实有限。")
    print("尝试调整搜索策略以获得更多结果。")
    print("=" * 60)

if __name__ == "__main__":
    main()
