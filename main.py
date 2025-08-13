import argparse

from chat import ask
from crawl import crawl
from translate import translate


def main():
    parser = argparse.ArgumentParser(description='ArXiv文章爬虫 - 支持复杂搜索条件')
    
    # 基本搜索条件
    parser.add_argument('--categories', '-c', nargs='+', 
                       help='学科分类，如: cs.AI cs.LG')
    parser.add_argument('--author', '-a', 
                       help='作者搜索')
    
    # 关键词搜索 - 支持多种逻辑关系
    parser.add_argument('--keywords-all', nargs='+',
                       help='所有关键词都必须包含 (AND关系)，如: --keywords-all "machine learning" "deep learning"')
    parser.add_argument('--keywords-any', nargs='+',
                       help='任一关键词包含即可 (OR关系)，如: --keywords-any "transformer" "attention"')
    parser.add_argument('--keywords-not', nargs='+',
                       help='不能包含的关键词 (NOT关系)，如: --keywords-not "survey" "review"')
    
    # 特定字段搜索
    parser.add_argument('--title-keywords', nargs='+',
                       help='仅在标题中搜索的关键词')
    parser.add_argument('--abstract-keywords', nargs='+',
                       help='仅在摘要中搜索的关键词')
    parser.add_argument('--title-abstract-keywords', nargs='+',
                       help='在标题或摘要中搜索的关键词 (更宽泛的搜索)')
    
    # 兼容性参数 (保持旧接口)
    parser.add_argument('--keywords', '-k', 
                       help='简单关键词搜索 (等同于--keywords-all的单个词)')
    parser.add_argument('--title', '-t', 
                       help='标题搜索 (等同于--title-keywords的单个词)')
    
    # 时间范围
    parser.add_argument('--start-date', 
                       help='开始日期 (YYYYMMDD格式)')
    parser.add_argument('--end-date', 
                       help='结束日期 (YYYYMMDD格式)')
    parser.add_argument('--date-type', choices=['submittedDate', 'lastUpdatedDate'],
                       default='submittedDate',
                       help='日期类型: submittedDate(提交日期) 或 lastUpdatedDate(更新日期)')
    
    # 爬取参数
    parser.add_argument('--max-results', '-m', type=int, default=100,
                       help='最大爬取数量 (默认: 100)')
    parser.add_argument('--batch-size', '-b', type=int, default=50,
                       help='每批爬取数量 (默认: 50)')
    parser.add_argument('--delay', '-d', type=float, default=1.0,
                       help='请求间隔秒数 (默认: 1.0)')
    
    # 排序
    parser.add_argument('--sort-by', choices=['relevance', 'lastUpdatedDate', 'submittedDate'],
                       default='submittedDate',
                       help='排序字段 (默认: submittedDate)')
    parser.add_argument('--sort-order', choices=['ascending', 'descending'],
                       default='descending',
                       help='排序顺序 (默认: descending)')
    
    # 输出格式
    parser.add_argument('--output', '-o', 
                       help='输出文件名 (支持 .json 和 .csv)')
    
    # 问答模式
    parser.add_argument('--chat_file',
                       help='直接使用已有文件进行问答，跳过搜索和翻译步骤')
    
    # 调试选项
    parser.add_argument('--show-query', action='store_true',
                       help='显示构建的API查询字符串')
    parser.add_argument('--show-abstracts', action='store_true',
                       help='在终端输出中显示文章摘要')
    parser.add_argument('--abstract-length', type=int, default=200,
                       help='显示摘要的最大字符数 (默认: 200)')
    parser.add_argument('--translate_llm', required=True,
                       help='用于翻译的LLM模型名称')
    parser.add_argument('--port', type=int, default=5000,
                       help='LLM服务器端口 (默认: 5000)')
    parser.add_argument('--batchsize', type=int, default=5,
                       help='翻译并发数量 (默认: 5)')
    
    # 新增网页版和文件加载限制参数
    parser.add_argument('--web', action='store_true', default=True,
                       help='启动网页版聊天界面 (默认启用)')
    parser.add_argument('--console', action='store_true',
                       help='使用命令行模式而非网页版')
    parser.add_argument('--max_load_files', type=int, default=10,
                       help='最大同时加载的论文数量，超过此数量将逐篇加载 (默认: 10)')
    parser.add_argument('--web_port', type=int, default=8080,
                       help='网页服务器端口 (默认: 8080)')

    args = parser.parse_args()
    
    # 如果指定了console模式，则关闭web模式
    if args.console:
        args.web = False
    
    # 验证参数
    if args.chat_file:
        # 如果指定了chat_file，直接进行问答
        print(f"使用现有文件进行问答: {args.chat_file}")
        # 创建临时args对象用于问答
        chat_args = argparse.Namespace()
        chat_args.output = args.chat_file
        chat_args.translate_llm = args.translate_llm
        chat_args.port = args.port
        chat_args.max_load_files = args.max_load_files
        chat_args.web = args.web
        chat_args.web_port = args.web_port
        
        if args.web:
            from web_chat import start_web_chat
            start_web_chat(chat_args)
        else:
            ask(chat_args)
    else:
        # 正常流程：爬取 -> 翻译 -> 问答
        if not args.output:
            parser.error("当不使用--chat_file时，--output参数是必需的")
        
        print("开始爬取ArXiv文章...")
        crawl(args)
        
        print("开始翻译摘要...")
        translate(args)
        
        if args.web:
            print("启动网页版问答...")
            from web_chat import start_web_chat
            start_web_chat(args)
        else:
            print("开始问答模式...")
            ask(args)

if __name__ == "__main__":
    main()

"""
使用示例：

1. 完整流程（爬取 + 翻译 + 问答）：
python main.py \
    --abstract-keywords "tool use" "reinforcement learning" \
    --start-date 20250501 \
    --end-date 20250805 \
    --batchsize 10 \
    --max-results 100 \
    --output tool-rl/output.json \
    --translate_llm "Qwen/Qwen3-32B" \
    --port 10006

2. 仅问答模式（基于现有文件）：
python main.py \
    --chat_file tool-rl/output.json \
    --translate_llm "Qwen/Qwen3-32B" \
    --port 10006
"""