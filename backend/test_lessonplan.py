import asyncio
import sys
sys.path.insert(0, '.')

from ai_client import ai_client

async def test_lesson_plan():
    """测试教案生成"""
    print("开始测试教案生成...")
    print(f"使用模型：{ai_client.lessonplan_model}")
    print(f"API 地址：{ai_client.base_url}")
    print("")
    
    try:
        result = await ai_client.generate_lesson_plan(
            topic="导数的几何意义",
            period="1 课时",
            student_level="中等",
            requirements=""
        )
        print("✅ 教案生成成功！")
        print("=" * 50)
        print(result[:500])  # 只显示前 500 个字符
        print("...")
        print("=" * 50)
    except Exception as e:
        print(f"❌ 教案生成失败：{str(e)}")
        import traceback
        print("")
        print("详细错误信息：")
        print(traceback.format_exc())
        print("")
        print("可能的原因：")
        print("1. API 密钥无效或过期")
        print("2. 模型名称不正确")
        print("3. 网络连接问题")
        print("4. API 服务不可用")
        print("")
        print("请检查 backend/config.json 中的配置")

if __name__ == "__main__":
    asyncio.run(test_lesson_plan())
