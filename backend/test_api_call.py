import httpx
import json

async def test_api():
    api_key = "sk-4d1a7638497c4595a5f38ac7c3dc29d7"
    base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    model = "qwen3.5-plus-2026-04-20"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": "你好，请回复一个JSON格式：{\"status\": \"ok\"}"
            }
        ],
        "temperature": 0.7,
        "max_tokens": 1000
    }
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            response = await client.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text[:500]}")
        except Exception as e:
            print(f"Error: {e}")

import asyncio
asyncio.run(test_api())
