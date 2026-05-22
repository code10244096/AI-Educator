import httpx
import json
import os

async def test_grader():
    api_key = "sk-4d1a7638497c4595a5f38ac7c3dc29d7"
    base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    model = "qwen3.5-plus-2026-04-20"
    
    # 读取测试文件
    test_file = os.path.join(os.path.dirname(__file__), "..", "dataset", "测试集", "批改作业", "deepseek_markdown_20260522_0931a6.md")
    with open(test_file, "r", encoding="utf-8") as f:
        content = f.read()
    
    print(f"文件内容长度: {len(content)}")
    print(f"文件内容前200字符: {content[:200]}")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    prompt = f"""
你是一位经验丰富且专业的数学老师，请批改这份作业。

学生作答内容：
{content[:3000]}

请以 JSON 格式返回批改结果，包含以下字段：
- total_questions: 题目总数
- correct_count: 正确数量
- wrong_count: 错误数量
- score: 分数（0-100）
- questions: 每道题的详细批改结果数组

只返回 JSON，不要其他内容。
"""
    
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.3,
        "max_tokens": 4000
    }
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            response = await client.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            print(f"Status: {response.status_code}")
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            print(f"Response length: {len(content)}")
            print(f"Response preview: {content[:500]}")
            
            # 尝试解析 JSON
            try:
                cleaned = content.replace("```json", "").replace("```", "").strip()
                parsed = json.loads(cleaned)
                print(f"JSON parsed successfully: {json.dumps(parsed, ensure_ascii=False, indent=2)[:500]}")
            except json.JSONDecodeError as e:
                print(f"JSON parse error: {e}")
                print(f"Raw content: {content[:1000]}")
        except Exception as e:
            print(f"Error: {e}")

import asyncio
asyncio.run(test_grader())
