#!/usr/bin/env python3
"""
检查ArXiv爬虫系统是否正常工作
"""

import sys
import importlib

def check_module(module_name):
    """检查模块是否可以导入"""
    try:
        module = importlib.import_module(module_name)
        print(f"✓ {module_name} - 导入成功")
        return True
    except ImportError as e:
        print(f"✗ {module_name} - 导入失败: {e}")
        return False

def check_dependencies():
    """检查外部依赖"""
    dependencies = [
        ('requests', '网络请求'),
        ('xml.etree.ElementTree', 'XML解析'),
        ('json', 'JSON处理'),
        ('csv', 'CSV处理'),
        ('argparse', '命令行参数'),
        ('concurrent.futures', '并发处理'),
        ('datetime', '日期时间'),
        ('time', '时间处理'),
        ('urllib.parse', 'URL处理')
    ]
    
    all_ok = True
    print("\n检查系统依赖:")
    for dep, desc in dependencies:
        if check_module(dep):
            pass
        else:
            all_ok = False
    
    # 检查可选依赖
    print("\n检查可选依赖 (仅翻译和问答功能需要):")
    try:
        import openai
        print("✓ openai - 可用")
    except ImportError:
        print("⚠ openai - 不可用 (翻译和问答功能将无法使用)")
    
    return all_ok

def check_project_modules():
    """检查项目模块"""
    modules = ['crawl', 'translate', 'chat', 'main']
    
    print("\n检查项目模块:")
    all_ok = True
    for module in modules:
        if check_module(module):
            pass
        else:
            all_ok = False
    
    return all_ok

def test_basic_functionality():
    """测试基本功能"""
    print("\n测试基本功能:")
    
    try:
        # 测试爬虫模块
        from crawl import ArxivCrawler
        crawler = ArxivCrawler()
        print("✓ ArxivCrawler - 初始化成功")
        
        # 测试查询构建
        query = crawler.build_search_query(
            abstract_keywords=['test']
        )
        print(f"✓ 查询构建 - 成功: {query[:50]}...")
        
    except Exception as e:
        print(f"✗ 爬虫功能测试失败: {e}")
        return False
    
    try:
        # 测试翻译模块 (如果openai可用)
        import openai
        from translate import ArxivTranslator
        translator = ArxivTranslator("test-model", "http://localhost:5000")
        print("✓ ArxivTranslator - 初始化成功")
    except ImportError:
        print("⚠ 翻译功能跳过 (openai未安装)")
    except Exception as e:
        print(f"✗ 翻译功能测试失败: {e}")
    
    try:
        # 测试问答模块 (如果openai可用)
        import openai
        from chat import ArxivChatBot
        chatbot = ArxivChatBot("test-model", "http://localhost:5000")
        print("✓ ArxivChatBot - 初始化成功")
    except ImportError:
        print("⚠ 问答功能跳过 (openai未安装)")
    except Exception as e:
        print(f"✗ 问答功能测试失败: {e}")
    
    return True

def main():
    """主检查函数"""
    print("ArXiv爬虫系统检查")
    print("=" * 50)
    
    deps_ok = check_dependencies()
    modules_ok = check_project_modules()
    func_ok = test_basic_functionality()
    
    print("\n" + "=" * 50)
    print("检查结果:")
    
    if deps_ok and modules_ok and func_ok:
        print("✓ 系统检查通过！")
        print("\n可用功能:")
        print("- 爬取ArXiv论文")
        print("- 复杂搜索查询")
        print("- JSON/CSV格式输出")
        
        try:
            import openai
            print("- 摘要翻译 (需要LLM服务)")
            print("- 论文问答 (需要LLM服务)")
        except ImportError:
            print("- 摘要翻译 (需要安装openai库)")
            print("- 论文问答 (需要安装openai库)")
        
        print("\n使用方法:")
        print("python main.py --help  # 查看完整帮助")
        print("python examples.py     # 查看使用示例")
    else:
        print("✗ 系统检查失败，请解决上述问题")
        sys.exit(1)

if __name__ == "__main__":
    main()
