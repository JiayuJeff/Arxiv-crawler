# 🤖 ArXiv论文智能问答系统

一个基于AI的学术论文智能分析平台，能够自动爬取ArXiv论文并提供智能问答功能。

## ✨ 功能特点

- � **智能论文爬取**: 从ArXiv自动获取最新论文
- 💬 **智能问答系统**: 基于OpenAI API的论文内容分析
- 🌐 **Web界面**: 美观的Web界面，支持实时对话
- 📱 **响应式设计**: 支持桌面端和移动端使用
- 📊 **论文管理**: 可跳过不感兴趣的论文，提高查询效率
- � **多模式处理**: 支持批量处理和逐篇处理模式
- 🎨 **现代化UI**: 炫酷的渐变背景和动画效果

## � 快速开始

### 环境要求

- Python 3.7+
- OpenAI API密钥
- 稳定的网络连接

### 安装依赖

```bash
# 克隆项目
git clone https://github.com/JiayuJeff/Arxiv-crawler.git
cd Arxiv-crawler

# 安装依赖包
pip install requests openai flask
```

### 配置API

启动兼容OpenAI的API服务（如本地LLM服务器），确保在指定端口运行。

### 🎯 一键启动（推荐）

```bash
python main.py
```

系统将自动：
1. 🌐 启动Web服务器（默认8080端口）
2. 🚀 自动打开浏览器
3. 📚 加载测试论文数据
4. ✨ 显示配置界面，等待LLM连接配置

**首次使用步骤**：
1. 运行 `python main.py`
2. 浏览器打开后，在页面顶部输入：
   - 模型名称（如：`gpt-3.5-turbo`）
   - 端口号（如：`9000`）
3. 点击"连接"按钮
4. 配置成功后即可开始智能问答

### 📋 详细启动选项

```bash
# 使用Web界面（默认模式）
python main.py

# 自定义Web端口
python main.py --web_port 9090

# 使用已有论文文件
python main.py --chat_file your_papers.json

# 使用命令行模式（需要完整参数）
python main.py --console --translate_llm gpt-3.5-turbo --port 9000 --output papers.json

# 查看所有选项
python main.py --help
```

## 🎮 使用指南

### Web界面使用

1. **启动系统**
   ```bash
   python main.py
   ```
   浏览器会自动打开 `http://localhost:8080`

2. **智能问答**
   - 💡 点击快捷问题按钮快速开始
   - 📝 在输入框中输入问题，支持中英文
   - 🎯 系统会自动分析相关论文并回答

3. **论文管理**
   - � 右侧显示所有加载的论文列表
   - ⏭️ 输入论文编号（如：1,3,5）跳过不感兴趣的论文
   - 🔄 点击"全部恢复"重新启用所有论文

4. **快捷操作**
   - 🎪 使用快捷问题按钮：研究方向分析、核心贡献总结等
   - 🗑️ 清空对话：重置聊天记录
   - ❓ 使用帮助：查看详细使用说明

### 命令行使用

```bash
# 使用命令行模式
python main.py --console

# 进入交互模式后
> 这些论文的主要研究方向是什么？
> 总结论文的核心技术贡献
> 比较不同方法的优缺点
> 跳过论文 1,3,5
> 退出
```

## 📊 高级功能

### 批量论文处理

系统支持两种处理模式：

- **批量处理模式**: 论文数量 ≤ `max_load_files`，一次性处理所有论文
- **逐篇处理模式**: 论文数量较多时，逐篇分析以提高响应速度

### 智能问答示例

```
🔍 研究主题查询:
"这些论文主要研究什么领域？"

💡 技术对比分析:
"比较不同论文使用的深度学习方法"

📊 数据集分析:
"这些论文使用了哪些数据集？"

🎯 实验结果总结:
"总结各论文的主要实验结果"

🔬 方法创新点:
"有哪些值得关注的技术创新？"
```

### 论文管理技巧

```
⏭️ 跳过单篇论文: 
输入 "1" 跳过第1篇论文

⏭️ 跳过多篇论文:
输入 "1,3,5,7" 跳过指定论文

🔄 恢复所有论文:
点击"全部恢复"或清空输入框后提交
```

## 🛠️ 配置选项

### 命令行参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--web` | `True` | 启用Web界面模式 |
| `--console` | `False` | 启用命令行模式 |
| `--web_port` | `8080` | Web服务器端口 |
| `--max_load_files` | `10` | 最大加载论文数量 |
| `--api_base` | `http://localhost:9000/v1` | API服务地址 |
| `--api_key` | `your-key-here` | API密钥 |

### 配置文件

在 `main.py` 中可以修改默认配置：

```python
# API配置
API_BASE = "http://localhost:9000/v1"
API_KEY = "your-key-here"

# 处理配置
MAX_LOAD_FILES = 10
WEB_PORT = 8080
```

## 🌐 Web界面功能

### 主要特性

- 🎨 **现代化设计**: 渐变背景、动画效果、响应式布局
- 💬 **实时对话**: 流畅的聊天体验，支持多轮对话
- 📱 **移动端适配**: 完美支持手机和平板设备
- � **状态实时更新**: 论文加载状态、处理模式实时显示

### 界面组件

1. **头部状态栏**
   - 📚 显示已加载论文数量
   - 🔄 显示当前处理模式
   - ✅ 显示活跃论文数量

2. **聊天区域**
   - 💬 用户消息（右侧蓝色气泡）
   - 🤖 AI回复（左侧白色气泡）
   - 📄 论文信息标签
   - ❌ 错误信息提示

3. **输入区域**
   - 📝 消息输入框（支持回车发送）
   - 🚀 发送按钮（处理中自动禁用）
   - 🗑️ 清空对话按钮
   - ❓ 使用帮助按钮

4. **侧边栏**
   - 📋 论文管理工具
   - 📚 论文列表展示
   - ⏭️ 跳过论文功能

## � Linux服务器使用

### 无显示环境（推荐）

1. **在服务器上启动**：
   ```bash
   python main.py --web_port 8080
   ```

2. **本地端口转发**：
   ```bash
   # 在本地机器执行
   ssh -L 8080:localhost:8080 username@your_server_ip
   ```

3. **本地访问**：
   打开浏览器访问 `http://localhost:8080`

### 有显示环境

直接运行即可：
```bash
python main.py
```
系统会尝试自动打开浏览器（firefox、chrome等）。

## �🔧 故障排除

### 常见问题

1. **无法访问Web界面**
   ```bash
   # 检查端口是否被占用
   netstat -an | grep 8080
   
   # 尝试其他端口
   python main.py --web_port 9090
   ```

2. **API连接失败**
   ```bash
   # 检查API服务是否运行
   curl http://localhost:9000/v1/models
   
   # 修改API地址
   python main.py --api_base http://your-api-server:port/v1
   ```

3. **论文加载缓慢**
   ```bash
   # 减少加载论文数量
   python main.py --max_load_files 5
   ```

4. **浏览器未自动打开**
   - **Windows/macOS**: 手动访问：`http://localhost:8080`
   - **Linux服务器**: 如果是无显示环境，请在本地转发端口：
     ```bash
     # 本地机器执行端口转发
     ssh -L 8080:localhost:8080 username@server_ip
     # 然后访问 http://localhost:8080
     ```
   - **Linux桌面**: 确保安装了浏览器（firefox、chrome等）

### 调试模式

```bash
# 启用详细日志
python main.py --console
# 然后查看控制台输出

# 检查论文爬取状态
python diagnose_crawl.py
```

## 📁 项目结构

```
Arxiv-crawler/
├── main.py              # 主程序入口
├── web_chat.py          # Web界面服务
├── chat.py              # 聊天逻辑处理
├── crawl.py             # 论文爬取模块
├── translate.py         # 翻译功能
├── diagnose_crawl.py    # 爬取诊断工具
├── test_web.py          # Web功能测试
├── examples.py          # 使用示例
├── README.md            # 项目说明
├── PROJECT_STATUS.md    # 项目状态
└── WEB_FEATURES.md      # Web功能说明
```

## 🤝 贡献指南

欢迎提交Issues和Pull Requests！

1. Fork 本项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 📜 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 📞 联系方式

- 项目地址: [https://github.com/JiayuJeff/Arxiv-crawler](https://github.com/JiayuJeff/Arxiv-crawler)
- 作者: JiayuJeff
- 邮箱: jliufv@connect.ust.hk

---

🎉 **开始您的论文研究之旅吧！**
