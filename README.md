# ArXiv爬虫和问答系统使用指南

## 🚀 功能概述

这是一个完整的ArXiv论文处理工具链，包含三个主要功能：
1. **📚 爬取** - 从ArXiv获取论文信息
2. **🌐 翻译** - 将英文摘要翻译为中文
3. **💬 问答** - 基于论文内容进行智能问答

## 📦 安装依赖

```bash
pip install openai requests
```

## 🎯 完整使用流程

### 一键运行（推荐）
```bash
python main.py \
    --abstract-keywords "tool use" "reinforcement learning" \
    --start-date 20250501 \
    --end-date 20250805 \
    --max-results 10 \
    --output papers.json \
    --translate_llm "Qwen/Qwen3-32B" \
    --port 10006 \
    --batchsize 5
```

这个命令会：
1. 🔍 爬取包含"tool use"和"reinforcement learning"的论文
2. 🌐 翻译所有摘要为中文
3. 💬 启动问答模式

### 分步执行

#### 1. 只爬取论文
```bash
python -c "
from crawl import crawl
import argparse

class Args:
    categories = ['cs.AI']
    max_results = 5
    output = 'papers.json'
    # ... 其他参数

crawl(Args())
"
```

#### 2. 只翻译已有文件
```bash
python -c "
from translate import translate
import argparse

class Args:
    output = 'papers.json'
    translate_llm = 'Qwen/Qwen3-32B'
    port = 10006
    batchsize = 5

translate(Args())
"
```

#### 3. 只启动问答
```bash
python -c "
from chat import ask
import argparse

class Args:
    output = 'papers.json'
    translate_llm = 'Qwen/Qwen3-32B'
    port = 10006

ask(Args())
"
```

## 💬 问答功能特色

### 支持的问题类型
- 📊 **论文总结**: "请总结这些论文的主要贡献"
- 🔍 **技术分析**: "这些论文使用了哪些技术方法？"
- ⚖️ **对比分析**: "比较这些论文的异同点"
- 🎯 **特定查询**: "哪些论文涉及强化学习？"
- 📚 **概念解释**: "什么是工具集成推理？"

### 交互示例
```
👤 您: 这些论文的主要研究方向是什么？

🤖 助手: 基于提供的论文摘要，主要研究方向包括：

1. **工具集成推理** (AutoTIR论文)
   - 通过强化学习实现自主工具集成推理
   - 增强大型语言模型的推理能力

2. **机器人工具使用** (Prolonging Tool Life论文)  
   - 通过寿命引导的强化学习学习通用工具的巧妙使用
   - 在不确定环境中提高工具使用效率

这些研究都聚焦于智能系统与工具的交互...
```

## 🔧 配置参数说明

### 爬取参数
- `--categories`: 学科分类 (如 cs.AI, cs.LG)
- `--abstract-keywords`: 摘要关键词 (AND关系)
- `--keywords-any`: 可选关键词 (OR关系)
- `--start-date` / `--end-date`: 时间范围
- `--max-results`: 最大爬取数量

### 翻译参数
- `--translate_llm`: 翻译模型名称 (必需)
- `--port`: LLM服务端口
- `--batchsize`: 翻译并发数

### 问答参数
- 使用与翻译相同的LLM配置
- 自动读取`--output`指定的JSON文件

## 🎨 输出格式

### JSON文件结构
```json
[
  {
    "arxiv_id": "2507.21836v1",
    "title": "论文标题",
    "abstract": "英文摘要...",
    "abstract_cn": "中文摘要...",
    "authors": ["作者1", "作者2"],
    "published": "2025-07-29T14:12:28Z",
    "categories": ["cs.CL"],
    "pdf_url": "PDF链接",
    "page_url": "页面链接"
  }
]
```

## 🚨 注意事项

1. **LLM服务**: 确保在指定端口运行兼容OpenAI API的LLM服务
2. **网络连接**: 爬取功能需要访问ArXiv API
3. **文件路径**: 使用绝对路径避免路径问题
4. **并发控制**: 合理设置`batchsize`避免API限制
5. **退出问答**: 输入`quit`、`exit`或`退出`结束对话

## 🎯 使用技巧

1. **精确搜索**: 使用`--abstract-keywords`进行精确匹配
2. **宽泛搜索**: 使用`--keywords-any`扩大搜索范围
3. **时间筛选**: 限制时间范围获取最新研究
4. **分类筛选**: 指定学科分类提高相关性
5. **批量处理**: 调整`batchsize`平衡速度和稳定性

Happy researching! 🎓✨
