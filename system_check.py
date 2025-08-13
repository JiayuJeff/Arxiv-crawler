#!/usr/bin/env python3
"""
ArXiv爬虫系统状态检查
"""

print("🔍 正在检查系统状态...")

# 1. 检查模块导入
try:
    import simple_web
    print("✅ simple_web模块导入成功")
except Exception as e:
    print(f"❌ simple_web模块导入失败: {e}")

# 2. 检查组件创建
try:
    chatbot = simple_web.SimpleWebChatBot(web_port=8899)
    print("✅ 聊天机器人创建成功")
except Exception as e:
    print(f"❌ 聊天机器人创建失败: {e}")

# 3. 检查Flask应用
try:
    app = simple_web.create_simple_app(chatbot)
    print("✅ Flask应用创建成功")
except Exception as e:
    print(f"❌ Flask应用创建失败: {e}")

# 4. 检查HTML模板
try:
    html = simple_web.get_html_template()
    print(f"✅ HTML模板生成成功 ({len(html)} 字符)")
except Exception as e:
    print(f"❌ HTML模板生成失败: {e}")

# 5. 检查关键功能
try:
    files = chatbot.get_available_files()
    print(f"✅ 文件扫描功能正常 (找到 {len(files)} 个文件)")
except Exception as e:
    print(f"❌ 文件扫描功能失败: {e}")

# 6. 检查UI组件
ui_checks = [
    ('连接按钮', '🔗 连接' in html),
    ('配置区域', 'configureLLM' in html),
    ('数据选择', '数据源选择' in html),
    ('进度条', 'progress-container' in html),
    ('聊天区域', 'sendMessage' in html)
]

for name, check in ui_checks:
    status = "✅" if check else "❌"
    print(f"{status} {name}: {'正常' if check else '缺失'}")

print("\n🎯 检查完成！")
print("如果所有项目都显示✅，说明系统已完全修复。")
print("如果有❌项目，请检查相应的错误信息。")
