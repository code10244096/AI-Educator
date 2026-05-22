import httpx
import json
import os
import asyncio

async def test_full_grader_flow():
    """Test the full grader flow with a test file"""
    api_base = "http://localhost:8000/api"
    test_file_path = os.path.join(os.path.dirname(__file__), "..", "dataset", "测试集", "批改作业", "deepseek_markdown_20260522_0931a6.md")
    
    if not os.path.exists(test_file_path):
        print(f"Test file not found: {test_file_path}")
        return
    
    print(f"Testing with file: {test_file_path}")
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        try:
            with open(test_file_path, "rb") as f:
                files = {
                    "files": (os.path.basename(test_file_path), f, "text/markdown")
                }
                data = {
                    "subject": "数学",
                    "reference_answer": ""
                }
                
                print("Sending request to /grader/upload...")
                response = await client.post(
                    f"{api_base}/grader/upload",
                    files=files,
                    data=data
                )
                
                print(f"Status: {response.status_code}")
                print(f"Response: {response.text[:1000]}")
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"\nGrading result:")
                    print(f"  Submission ID: {result.get('submission_id')}")
                    print(f"  Image count: {result.get('image_count')}")
                    print(f"  Total questions: {result.get('grading_result', {}).get('total_questions')}")
                    print(f"  Correct count: {result.get('grading_result', {}).get('correct_count')}")
                    print(f"  Wrong count: {result.get('grading_result', {}).get('wrong_count')}")
                else:
                    print(f"Error: {response.text}")
                    
        except Exception as e:
            print(f"Exception: {e}")
            import traceback
            traceback.print_exc()

asyncio.run(test_full_grader_flow())
