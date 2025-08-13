import argparse
import requests
import xml.etree.ElementTree as ET
import json
import csv
import time
from datetime import datetime
from typing import List, Dict, Optional
import urllib.parse
import os

class ArxivCrawler:
    def __init__(self):
        self.base_url = "http://export.arxiv.org/api/query"
        self.session = requests.Session()
        # 设置请求头，模拟浏览器行为
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
        })
    
    def build_search_query(self, 
                          categories: List[str] = None,
                          keywords_all: List[str] = None,
                          keywords_any: List[str] = None,
                          keywords_not: List[str] = None,
                          title_keywords: List[str] = None,
                          abstract_keywords: List[str] = None,
                          title_abstract_keywords: List[str] = None,
                          author: str = None,
                          start_date: str = None,
                          end_date: str = None,
                          date_type: str = "submittedDate") -> str:
        """
        构建搜索查询字符串 (支持复杂的关键词组合)
        
        Args:
            categories: 学科分类列表，如 ['cs.AI', 'cs.LG']
            keywords_all: 所有关键词都必须包含 (AND关系)
            keywords_any: 任一关键词包含即可 (OR关系)
            keywords_not: 不能包含的关键词 (NOT关系)
            title_keywords: 仅在标题中搜索的关键词
            abstract_keywords: 仅在摘要中搜索的关键词
            title_abstract_keywords: 在标题或摘要中搜索的关键词
            author: 作者姓名
            start_date: 开始日期 (YYYYMMDD格式)
            end_date: 结束日期 (YYYYMMDD格式)
            date_type: 日期类型 ('submittedDate' 或 'lastUpdatedDate')
        
        Returns:
            构建好的查询字符串
        """
        query_parts = []
        
        # 添加分类条件
        if categories:
            cat_query = " OR ".join([f"cat:{cat}" for cat in categories])
            if len(categories) > 1:
                cat_query = f"({cat_query})"
            query_parts.append(cat_query)
        
        # 添加关键词条件 - 全部包含 (AND)
        if keywords_all:
            for kw in keywords_all:
                # 对包含空格的关键词使用引号包围
                if ' ' in kw:
                    query_parts.append(f'all:"{kw}"')
                else:
                    query_parts.append(f'all:{kw}')
        
        # 添加关键词条件 - 任一包含 (OR)
        if keywords_any:
            any_parts = []
            for kw in keywords_any:
                if ' ' in kw:
                    any_parts.append(f'all:"{kw}"')
                else:
                    any_parts.append(f'all:{kw}')
            any_query = " OR ".join(any_parts)
            if len(keywords_any) > 1:
                any_query = f"({any_query})"
            query_parts.append(any_query)
        
        # 添加标题关键词
        if title_keywords:
            for kw in title_keywords:
                if ' ' in kw:
                    query_parts.append(f'ti:"{kw}"')
                else:
                    query_parts.append(f'ti:{kw}')
        
        # 添加摘要关键词
        if abstract_keywords:
            for kw in abstract_keywords:
                if ' ' in kw:
                    query_parts.append(f'abs:"{kw}"')
                else:
                    query_parts.append(f'abs:{kw}')
        
        # 添加标题或摘要关键词
        if title_abstract_keywords:
            for kw in title_abstract_keywords:
                if ' ' in kw:
                    title_abs_query = f'(ti:"{kw}" OR abs:"{kw}")'
                else:
                    title_abs_query = f'(ti:{kw} OR abs:{kw})'
                query_parts.append(title_abs_query)
        
        # 添加作者条件
        if author:
            if ' ' in author:
                query_parts.append(f'au:"{author}"')
            else:
                query_parts.append(f'au:{author}')
        
        # 添加时间范围条件
        if start_date and end_date:
            date_query = f"{date_type}:[{start_date} TO {end_date}]"
            query_parts.append(date_query)
        
        # 组合所有条件
        main_query = " AND ".join(query_parts)
        
        # 添加排除关键词 (NOT)
        if keywords_not:
            not_parts = []
            for kw in keywords_not:
                if ' ' in kw:
                    not_parts.append(f'all:"{kw}"')
                else:
                    not_parts.append(f'all:{kw}')
            not_query = " OR ".join(not_parts)
            if len(keywords_not) > 1:
                not_query = f"({not_query})"
            main_query = f"{main_query} ANDNOT {not_query}"
        
        return main_query
    
    def fetch_papers(self, 
                    search_query: str,
                    start: int = 0,
                    max_results: int = 100,
                    sort_by: str = "submittedDate",
                    sort_order: str = "descending") -> List[Dict]:
        """
        从ArXiv API获取文章数据
        
        Args:
            search_query: 搜索查询字符串
            start: 起始位置
            max_results: 最大结果数
            sort_by: 排序字段
            sort_order: 排序顺序
        
        Returns:
            文章数据列表
        """
        # ArXiv API建议单次请求不超过max_results=2000
        max_results = min(max_results, 2000)
        
        params = {
            'search_query': search_query,
            'start': start,
            'max_results': max_results,
            'sortBy': sort_by,
            'sortOrder': sort_order
        }
        
        try:
            print(f"正在请求: {self.base_url}")
            print(f"查询参数: {params}")
            
            response = self.session.get(self.base_url, params=params)
            response.raise_for_status()
            
            papers = self.parse_xml_response(response.text)
            print(f"API返回 {len(papers)} 篇文章")
            
            return papers
            
        except requests.RequestException as e:
            print(f"请求失败: {e}")
            return []
    
    def parse_xml_response(self, xml_content: str) -> List[Dict]:
        """
        解析XML响应，提取文章信息
        
        Args:
            xml_content: XML响应内容
        
        Returns:
            解析后的文章数据列表
        """
        papers = []
        
        try:
            # 解析XML
            root = ET.fromstring(xml_content)
            
            # 定义命名空间
            namespaces = {
                'atom': 'http://www.w3.org/2005/Atom',
                'opensearch': 'http://a9.com/-/spec/opensearch/1.1/',
                'arxiv': 'http://arxiv.org/schemas/atom'
            }
            
            # 获取总结果数
            total_results = root.find('opensearch:totalResults', namespaces)
            if total_results is not None:
                print(f"找到 {total_results.text} 篇文章")
            
            # 解析每篇文章
            for entry in root.findall('atom:entry', namespaces):
                paper = {}
                
                # ID (ArXiv ID)
                id_elem = entry.find('atom:id', namespaces)
                if id_elem is not None:
                    paper['arxiv_id'] = id_elem.text.split('/')[-1]
                
                # 标题
                title_elem = entry.find('atom:title', namespaces)
                if title_elem is not None:
                    paper['title'] = title_elem.text.strip()
                
                # 摘要
                summary_elem = entry.find('atom:summary', namespaces)
                if summary_elem is not None:
                    paper['abstract'] = summary_elem.text.strip()
                
                # 作者
                authors = []
                for author in entry.findall('atom:author', namespaces):
                    name_elem = author.find('atom:name', namespaces)
                    if name_elem is not None:
                        authors.append(name_elem.text)
                paper['authors'] = authors
                
                # 发布时间
                published_elem = entry.find('atom:published', namespaces)
                if published_elem is not None:
                    paper['published'] = published_elem.text
                
                # 更新时间
                updated_elem = entry.find('atom:updated', namespaces)
                if updated_elem is not None:
                    paper['updated'] = updated_elem.text
                
                # 分类
                categories = []
                for category in entry.findall('atom:category', namespaces):
                    term = category.get('term')
                    if term:
                        categories.append(term)
                paper['categories'] = categories
                
                # PDF链接
                for link in entry.findall('atom:link', namespaces):
                    if link.get('title') == 'pdf':
                        paper['pdf_url'] = link.get('href')
                    elif link.get('rel') == 'alternate':
                        paper['page_url'] = link.get('href')
                
                papers.append(paper)
                
        except ET.ParseError as e:
            print(f"XML解析错误: {e}")
        
        return papers
    
    def crawl_all_papers(self, 
                        search_query: str,
                        max_total: int = 1000,
                        batch_size: int = 100,
                        delay: float = 1.0,
                        **kwargs) -> List[Dict]:
        """
        爬取所有匹配的文章 (分批进行)
        
        Args:
            search_query: 搜索查询
            max_total: 最大爬取数量
            batch_size: 每批大小
            delay: 请求间隔(秒)
            **kwargs: 其他传递给fetch_papers的参数
        
        Returns:
            所有文章数据
        """
        all_papers = []
        start = 0
        consecutive_empty_batches = 0
        max_empty_batches = 3  # 最多允许3次连续的空批次
        
        # ArXiv API建议的最大batch_size是2000，但实际使用中建议不超过1000
        actual_batch_size = min(batch_size, 1000)
        
        while len(all_papers) < max_total:
            current_batch_size = min(actual_batch_size, max_total - len(all_papers))
            
            print(f"\n=== 正在获取第 {start + 1} - {start + current_batch_size} 篇文章 ===")
            
            papers = self.fetch_papers(
                search_query=search_query,
                start=start,
                max_results=current_batch_size,
                **kwargs
            )
            
            if not papers:
                consecutive_empty_batches += 1
                print(f"本批次没有返回文章 (连续空批次: {consecutive_empty_batches})")
                
                if consecutive_empty_batches >= max_empty_batches:
                    print("多次尝试无结果，停止爬取")
                    break
                
                # 增加起始位置，尝试下一批
                start += current_batch_size
                continue
            else:
                consecutive_empty_batches = 0  # 重置空批次计数
            
            # 过滤掉重复的文章
            new_papers = []
            existing_ids = {paper.get('arxiv_id') for paper in all_papers}
            
            for paper in papers:
                paper_id = paper.get('arxiv_id')
                if paper_id and paper_id not in existing_ids:
                    new_papers.append(paper)
                    existing_ids.add(paper_id)
            
            all_papers.extend(new_papers)
            print(f"本批次获取 {len(papers)} 篇文章，其中 {len(new_papers)} 篇为新文章")
            print(f"已获取 {len(all_papers)} 篇唯一文章")
            
            # 更新起始位置
            start += len(papers)
            
            # 如果返回的文章数少于请求数，可能是到达末尾
            if len(papers) < current_batch_size:
                print("返回文章数少于请求数，可能已到达结果末尾")
                # 但是仍然尝试下一批，因为有时候中间会有空隙
                if len(papers) == 0:
                    break
            
            # 延迟，避免请求过于频繁
            if delay > 0 and len(all_papers) < max_total:
                print(f"等待 {delay} 秒...")
                time.sleep(delay)
        
        print(f"\n=== 爬取完成 ===")
        print(f"总共获取 {len(all_papers)} 篇唯一文章")
        
        return all_papers
    
    def save_to_json(self, papers: List[Dict], filename: str):
        """保存为JSON文件"""
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(papers, f, ensure_ascii=False, indent=2)
        print(f"已保存 {len(papers)} 篇文章到 {filename}")
    
    def save_to_csv(self, papers: List[Dict], filename: str):
        """保存为CSV文件"""
        if not papers:
            return
        
        # 准备CSV字段
        fieldnames = ['arxiv_id', 'title', 'abstract', 'authors', 'published', 
                     'updated', 'categories', 'pdf_url', 'page_url']
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for paper in papers:
                # 处理列表字段，转换为字符串
                row = paper.copy()
                if 'authors' in row and isinstance(row['authors'], list):
                    row['authors'] = '; '.join(row['authors'])
                if 'categories' in row and isinstance(row['categories'], list):
                    row['categories'] = '; '.join(row['categories'])
                
                writer.writerow(row)
        
        print(f"已保存 {len(papers)} 篇文章到 {filename}")


def crawl(args):
    """
    根据给定的参数爬取ArXiv文章
    
    Args:
        args: 包含搜索参数的对象，应该有以下属性：
            - categories: 学科分类列表
            - keywords_all: 必须包含的关键词
            - keywords_any: 可选关键词
            - keywords_not: 排除关键词
            - title_keywords: 标题关键词
            - abstract_keywords: 摘要关键词
            - title_abstract_keywords: 标题或摘要关键词
            - author: 作者
            - start_date: 开始日期
            - end_date: 结束日期
            - date_type: 日期类型
            - max_results: 最大结果数
            - batch_size: 批处理大小
            - delay: 请求间隔
            - sort_by: 排序字段
            - sort_order: 排序顺序
            - output: 输出文件
            - show_query: 是否显示查询
            - show_abstracts: 是否显示摘要
            - abstract_length: 摘要长度
            - keywords: 兼容性参数
            - title: 兼容性参数
    """
    
    # 创建爬虫实例
    crawler = ArxivCrawler()
    
    # 处理兼容性参数
    keywords_all = args.keywords_all
    title_keywords = args.title_keywords
    
    if args.keywords and not keywords_all:
        keywords_all = [args.keywords]
    
    if args.title and not title_keywords:
        title_keywords = [args.title]
    
    # 构建搜索查询
    search_query = crawler.build_search_query(
        categories=args.categories,
        keywords_all=keywords_all,
        keywords_any=args.keywords_any,
        keywords_not=args.keywords_not,
        title_keywords=title_keywords,
        abstract_keywords=args.abstract_keywords,
        title_abstract_keywords=args.title_abstract_keywords,
        author=args.author,
        start_date=args.start_date,
        end_date=args.end_date,
        date_type=args.date_type
    )
    
    if not search_query:
        print("错误: 必须指定至少一个搜索条件")
        print("\n可用的搜索选项:")
        print("  --categories: 学科分类")
        print("  --keywords-all: 必须包含的关键词")
        print("  --keywords-any: 可选关键词")
        print("  --title-keywords: 标题关键词")
        print("  --abstract-keywords: 摘要关键词")
        print("  --title-abstract-keywords: 标题或摘要关键词")
        print("  --author: 作者")
        return
    
    if args.show_query:
        print(f"构建的查询字符串: {search_query}")
        print(f"URL编码后: {urllib.parse.quote(search_query)}")
        print()
    
    print(f"搜索查询: {search_query}")
    
    # 开始爬取
    papers = crawler.crawl_all_papers(
        search_query=search_query,
        max_total=args.max_results,
        batch_size=args.batch_size,
        delay=args.delay,
        sort_by=args.sort_by,
        sort_order=args.sort_order
    )
    
    if not papers:
        print("没有找到匹配的文章")
        return
    
    # 显示文章信息 (如果启用了摘要显示)
    if args.show_abstracts:
        print(f"\n=== 找到的文章详情 ===")
        for i, paper in enumerate(papers, 1):
            print(f"\n{i}. 【{paper.get('arxiv_id', 'No ID')}】")
            print(f"标题: {paper.get('title', 'No title').strip()}")
            print(f"作者: {', '.join(paper.get('authors', []))}")
            print(f"发布时间: {paper.get('published', 'No date')}")
            print(f"分类: {', '.join(paper.get('categories', []))}")
            
            # 显示摘要 (截断到指定长度)
            abstract = paper.get('abstract', 'No abstract')
            if len(abstract) > args.abstract_length:
                abstract = abstract[:args.abstract_length] + "..."
            print(f"摘要: {abstract.strip()}")
            
            # 显示链接
            if paper.get('pdf_url'):
                print(f"PDF: {paper.get('pdf_url')}")
            if paper.get('page_url'):
                print(f"页面: {paper.get('page_url')}")
    
    # 保存结果
    if args.output.endswith('.json'):
        crawler.save_to_json(papers, args.output)
    elif args.output.endswith('.csv'):
        crawler.save_to_csv(papers, args.output)
    else:
        print("错误: 输出文件格式不支持，请使用 .json 或 .csv")
        return
    
    print(f"\n=== 爬取完成 ===")
    print(f"请求的最大数量: {args.max_results}")
    print(f"实际获取数量: {len(papers)} 篇文章")
    if len(papers) < args.max_results:
        print(f"⚠️  获取数量少于请求数量，可能原因:")
        print(f"   - ArXiv数据库中实际匹配的文章数量有限")
        print(f"   - 部分文章可能被ArXiv API过滤")
        print(f"   - 使用更宽泛的搜索条件可能获得更多结果")
    print(f"保存位置: {args.output}")
    if not args.show_abstracts:
        print("提示: 使用 --show-abstracts 参数可在终端查看文章摘要")


"""
使用示例:

1. 基本搜索 - 在AI分类中搜索包含"transformer"的文章
python main.py --categories cs.AI --keywords-all "transformer" --output results.json

2. 复杂关键词搜索 - 必须包含"machine learning"，可选包含"deep learning"或"neural network"
python main.py --keywords-all "machine learning" --keywords-any "deep learning" "neural network" --output results.json

3. 特定字段搜索 - 标题包含"attention"，摘要包含"transformer"
python main.py --title-keywords "attention" --abstract-keywords "transformer" --output results.json

4. 排除搜索 - 包含"AI"但不包含"survey"或"review"
python main.py --keywords-all "AI" --keywords-not "survey" "review" --output results.json

5. 时间范围搜索 - 2024年的AI文章
python main.py --categories cs.AI --start-date 20240101 --end-date 20241231 --output results.json

6. 标题或摘要搜索 - 在标题或摘要中包含"BERT"或"GPT"
python main.py --title-abstract-keywords "BERT" "GPT" --output results.json

7. 复合搜索示例
python main.py \
    --categories cs.AI cs.LG \
    --title-keywords "transformer" \
    --keywords-all "attention mechanism" \
    --keywords-not "survey" \
    --start-date 20240101 \
    --end-date 20250805 \
    --max-results 500 \
    --output complex_search.json

8. 调试模式 - 查看构建的查询字符串
python main.py --categories cs.AI --keywords-all "transformer" --show-query --output test.json

9. 显示摘要 - 在终端输出中查看文章摘要
python main.py --abstract-keywords "reinforcement learning" --max-results 3 --show-abstracts --output results.json

10. 自定义摘要长度 - 显示更长的摘要
python main.py --categories cs.AI --max-results 5 --show-abstracts --abstract-length 500 --output results.json
"""