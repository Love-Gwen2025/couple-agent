"""
测试自定义 API 中转站（Codex CLI 模拟）

使用方法：
    cd backend
    uv run python -m scripts.test_custom_api
    或
    uv run python scripts/test_custom_api.py
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径（必须在 import app 之前）
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from openai import OpenAI

from app.core.settings import get_settings

# Windows 控制台 UTF-8 编码修复
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")


def test_custom_api():
    """测试自定义 API 的流式响应"""
    settings = get_settings()

    # 创建客户端，模拟 Codex CLI
    client = OpenAI(
        api_key=settings.custom_api_key,
        base_url=settings.custom_base_url,
        # 添加 Codex CLI 版本信息到 User-Agent
        default_headers={
            "User-Agent": "OpenAI-Codex/0.88.0",
            "X-Client-Name": "codex-cli",
            "X-Client-Version": "0.88.0",
        },
    )

    print("🚀 开始测试自定义 API 流式响应...")
    print(f"📡 Base URL: {settings.custom_base_url}")
    print("🤖 Model: gpt-5.1-codex-max\n")

    # 使用 Responses API（流式模式）
    response = client.responses.create(
        model="gpt-5.1-codex-max",
        input=[{"role": "user", "content": "你好，请介绍一下你自己"}],
        stream=True,  # 必须开启流式传输！
    )

    # 流式读取响应
    print("💬 响应内容: ", end="", flush=True)
    for event in response:
        # 打印每个事件的文本内容
        if hasattr(event, "delta") and event.delta:
            print(event.delta, end="", flush=True)
        elif hasattr(event, "output_text") and event.output_text:
            print(event.output_text, end="", flush=True)

    print("\n\n✅ 测试完成！")


if __name__ == "__main__":
    test_custom_api()
