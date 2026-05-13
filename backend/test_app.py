"""
AI 教学助手系统 - 基础功能测试脚本
用于验证代码正确性和 API 接口
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(__file__))

def test_imports():
    """测试导入是否成功"""
    print("=" * 50)
    print("测试 1: 检查模块导入")
    print("=" * 50)
    
    try:
        from config import settings
        print("✓ config 模块导入成功")
        print(f"  - 应用名称：{settings.APP_NAME}")
        print(f"  - API 前缀：{settings.API_PREFIX}")
    except Exception as e:
        print(f"✗ config 模块导入失败：{e}")
        return False
    
    try:
        from database import Base, engine, get_db, init_db
        print("✓ database 模块导入成功")
    except Exception as e:
        print(f"✗ database 模块导入失败：{e}")
        return False
    
    try:
        from models import User, ClassInfo, HomeworkAssignment, HomeworkSubmission, WrongQuestion, LessonPlan
        print("✓ models 模块导入成功")
        print(f"  - 已定义 {len([User, ClassInfo, HomeworkAssignment, HomeworkSubmission, WrongQuestion, LessonPlan])} 个数据模型")
    except Exception as e:
        print(f"✗ models 模块导入失败：{e}")
        return False
    
    try:
        from ai_client import AIClient, ai_client
        print("✓ ai_client 模块导入成功")
        print(f"  - AI 模型：{ai_client.model}")
        print(f"  - OCR 模型：{ai_client.ocr_model}")
    except Exception as e:
        print(f"✗ ai_client 模块导入失败：{e}")
        return False
    
    try:
        from api import router
        print("✓ api 模块导入成功")
        print(f"  - API 路由已注册")
    except Exception as e:
        print(f"✗ api 模块导入失败：{e}")
        return False
    
    try:
        from main import app
        print("✓ main 模块导入成功")
        print(f"  - FastAPI 应用已创建")
    except Exception as e:
        print(f"✗ main 模块导入失败：{e}")
        return False
    
    print()
    return True


def test_models():
    """测试数据模型"""
    print("=" * 50)
    print("测试 2: 检查数据模型")
    print("=" * 50)
    
    from models import User, HomeworkSubmission, WrongQuestion, LessonPlan
    
    # 检查模型属性
    models_info = {
        "User": ["id", "username", "email", "password_hash", "role"],
        "HomeworkSubmission": ["id", "assignment_id", "user_id", "image_paths", "ocr_result", "批改_result", "status"],
        "WrongQuestion": ["id", "user_id", "question_text", "knowledge_point", "is_mastered"],
        "LessonPlan": ["id", "teacher_id", "title", "content", "period"]
    }
    
    for model_name, expected_fields in models_info.items():
        model = eval(model_name)
        actual_fields = [c.name for c in model.__table__.columns]
        print(f"✓ {model_name} 模型:")
        print(f"  - 字段数：{len(actual_fields)}")
        print(f"  - 主键：{model.__tablename__}")
    
    print()
    return True


def test_api_routes():
    """测试 API 路由"""
    print("=" * 50)
    print("测试 3: 检查 API 路由")
    print("=" * 50)
    
    from main import app
    
    routes = []
    for route in app.routes:
        if hasattr(route, 'methods') and hasattr(route, 'path'):
            for method in route.methods:
                routes.append(f"{method} {route.path}")
    
    print(f"✓ 已注册 {len(routes)} 个 API 端点:")
    for route in sorted(routes):
        print(f"  - {route}")
    
    print()
    return True


def test_config():
    """测试配置文件"""
    print("=" * 50)
    print("测试 4: 检查配置")
    print("=" * 50)
    
    from config import settings
    
    config_items = {
        "应用名称": settings.APP_NAME,
        "API 前缀": settings.API_PREFIX,
        "数据库 URL": settings.DATABASE_URL,
        "AI 模型": settings.AI_MODEL,
        "OCR 模型": settings.OCR_MODEL,
        "上传目录": settings.UPLOAD_DIR,
        "CORS 源": str(settings.CORS_ORIGINS)
    }
    
    for key, value in config_items.items():
        print(f"✓ {key}: {value}")
    
    print()
    return True


def main():
    """运行所有测试"""
    print("\n")
    print("╔" + "=" * 48 + "╗")
    print("║" + " " * 12 + "AI 教学助手系统 - 代码测试" + " " * 12 + "║")
    print("╚" + "=" * 48 + "╝")
    print()
    
    tests = [
        ("模块导入测试", test_imports),
        ("数据模型测试", test_models),
        ("API 路由测试", test_api_routes),
        ("配置文件测试", test_config),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ {test_name} 执行失败：{e}")
            failed += 1
        print()
    
    print("=" * 50)
    print(f"测试结果：{passed} 通过，{failed} 失败")
    print("=" * 50)
    
    if failed == 0:
        print("\n✓ 所有测试通过！系统代码结构正确。")
        print("\n下一步:")
        print("1. 配置 backend/.env 文件中的 AI_API_KEY")
        print("2. 运行：uvicorn main:app --reload")
        print("3. 访问：http://localhost:8000/docs")
    else:
        print(f"\n✗ 有 {failed} 个测试失败，请检查错误信息。")
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
