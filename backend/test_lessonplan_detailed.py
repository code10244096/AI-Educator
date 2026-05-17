import asyncio
import sys
sys.path.insert(0, '.')

from ai_client import ai_client

async def test_lesson_plan():
    """测试教案生成"""
    print("=" * 60)
    print("开始测试教案生成...")
    print("=" * 60)
    print(f"使用模型：{ai_client.lessonplan_model}")
    print(f"API 地址：{ai_client.base_url}")
    print(f"API Key: {ai_client.api_key[:10]}...{ai_client.api_key[-10:]}")
    print("")
    
    try:
        print("正在调用 AI 模型生成教案...")
        result = await ai_client.generate_lesson_plan(
            topic="椭圆的性质与应用",
            period="1 课时",
            student_level="中等",
            requirements=""
        )
        print("\n✅ 教案生成成功！")
        print("=" * 60)
        print(result[:500])  # 只显示前 500 个字符
        print("...")
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ 教案生成失败！")
        print("=" * 60)
        print(f"错误类型：{type(e).__name__}")
        print(f"错误信息：{str(e)}")
        print("")
        import traceback
        print("完整堆栈跟踪：")
        traceback.print_exc()
        print("")
        print("=" * 60)
        print("可能的原因：")
        print("1. API 密钥无效或过期")
        print("2. 模型名称不正确")
        print("3. 网络连接问题")
        print("4. API 服务不可用")
        print("5. 余额不足或配额已用完")
        print("")
        print("请检查 backend/config.json 中的配置")
        print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_lesson_plan())
