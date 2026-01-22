"""测试中转站 API 集成 - 输出到文件"""

import asyncio
import sys

sys.path.insert(0, ".")

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.settings import get_settings
from app.services.custom_model_adapter import CustomChatModel

results = []


async def test_custom_model():
    settings = get_settings()
    model = CustomChatModel(
        api_key=settings.custom_api_key,
        base_url=settings.custom_base_url,
        model="gpt-5.1-codex-max",
        temperature=0.7,
    )

    results.append("=" * 50)
    results.append("Testing CustomChatModel Adapter")
    results.append("=" * 50)

    # Test 1: ainvoke
    results.append("\n[Test 1] ainvoke:")
    try:
        messages = [HumanMessage(content="Say hello in one word")]
        response = await model.ainvoke(messages)
        results.append(f"Response type: {type(response).__name__}")
        content = str(response.content)[:200] if response.content else "empty"
        results.append(f"Content: {content}")
        results.append("Result: SUCCESS")
    except Exception as e:
        results.append(f"Error: {type(e).__name__}: {e}")
        results.append("Result: FAILED")

    # Test 2: astream
    results.append("\n[Test 2] astream:")
    try:
        messages = [HumanMessage(content="Count 1 to 3")]
        chunks = []
        async for chunk in model.astream(messages):
            if chunk.content:
                chunks.append(str(chunk.content))
        full_text = "".join(chunks)
        results.append(f"Response: {full_text[:200]}")
        results.append(f"Total chunks: {len(chunks)}")
        results.append("Result: SUCCESS")
    except Exception as e:
        results.append(f"Error: {type(e).__name__}: {e}")
        results.append("Result: FAILED")

    # Test 3: with SystemMessage
    results.append("\n[Test 3] With SystemMessage:")
    try:
        messages = [
            SystemMessage(content="You are a helpful assistant. Be very brief."),
            HumanMessage(content="What is 2+2?"),
        ]
        response = await model.ainvoke(messages)
        content = str(response.content)[:200] if response.content else "empty"
        results.append(f"Response: {content}")
        results.append("Result: SUCCESS")
    except Exception as e:
        results.append(f"Error: {type(e).__name__}: {e}")
        results.append("Result: FAILED")

    results.append("\n" + "=" * 50)
    results.append("All tests completed!")
    results.append("=" * 50)

    # Write results
    with open("test_results.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(results))

    print("Done. Results in test_results.txt")


if __name__ == "__main__":
    asyncio.run(test_custom_model())
