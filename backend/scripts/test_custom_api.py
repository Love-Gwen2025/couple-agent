from openai import OpenAI

# 创建客户端，模拟 Codex CLI
client = OpenAI(
    api_key="cr_f80e1d29b593d7f6fbae575679f3a32cdaf25f38c95b08b4d4c2b911c5d23229",
    base_url="https://ai.love-gwen.top/openai",
    # 添加 Codex CLI 版本信息到 User-Agent
    default_headers={
        "User-Agent": "OpenAI-Codex/0.77.0",
        "X-Client-Name": "codex-cli",
        "X-Client-Version": "0.77.0",
    },
)

# 使用 Responses API（流式模式）
response = client.responses.create(
    model="gpt-5.1-codex-max",
    input=[{"role": "user", "content": "你好，请介绍一下你自己"}],
    stream=True,  # 必须开启流式传输！
)

# 流式读取响应
for event in response:
    # 打印每个事件的文本内容
    if hasattr(event, "delta") and event.delta:
        print(event.delta, end="", flush=True)
    elif hasattr(event, "output_text") and event.output_text:
        print(event.output_text, end="", flush=True)

print()  # 换行
