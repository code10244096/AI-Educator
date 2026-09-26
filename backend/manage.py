"""
管理命令（由学校管理员在服务器上执行；不开放注册）。

用法（在 backend/ 目录，或 docker compose exec backend 中执行）：
  python manage.py create-user --username 13800000001 --name 王老师 [--role admin] [--school 某某中学] [--password <初始密码>]
  python manage.py reset-password --username 13800000001 [--password <新初始密码>]
  python manage.py disable-user --username 13800000001
  python manage.py enable-user --username 13800000001
  python manage.py list-users
  python manage.py assign-orphans --username 13800000001

- 不给 --password 时随机生成初始密码，只打印一次（输出中固定有一行 `初始密码: xxx`）；
  老师首次登录后必须先设置新密码。
- 数据库位置取 DATABASE_URL（与后端服务一致）。
- 这些函数也可以直接 import 使用（同步函数，内部自建数据库连接），便于测试：
  create_user / reset_password / disable_user / enable_user / list_users / assign_orphans
"""
import argparse
import secrets
import string
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sqlalchemy import create_engine, or_, select, update  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from auth import hash_password, is_bcrypt_hash, validate_new_password  # noqa: E402
from config import settings  # noqa: E402
from database import Base, _migrate_add_missing_columns  # noqa: E402
import models  # noqa: E402,F401
from models import ClassInfo, HomeworkAssignment, HomeworkSubmission, LessonPlan, User, WrongQuestion  # noqa: E402

ROLE_LABELS = {"teacher": "教师", "admin": "管理员"}


class ManageError(Exception):
    """管理命令的业务错误（打印中文原因，退出码 1）"""


# ==================== 数据库 ====================

def _sync_url(url: str) -> str:
    return url.replace("+aiosqlite", "").replace("+asyncpg", "+psycopg2")


def _engine():
    engine = create_engine(_sync_url(settings.DATABASE_URL))
    with engine.begin() as conn:
        # 与后端启动一致：只建缺失的表、只补缺失的列，不删任何数据
        Base.metadata.create_all(conn)
        _migrate_add_missing_columns(conn)
    return engine


def _find_user(session: Session, username: str) -> Optional[User]:
    username = (username or "").strip()
    from sqlalchemy import func
    return session.execute(
        select(User).where(func.lower(User.username) == username.lower())
    ).scalar_one_or_none()


def _require_user(session: Session, username: str) -> User:
    user = _find_user(session, username)
    if not user:
        raise ManageError(f"账号不存在：{username}")
    return user


def generate_password(length: int = 10) -> str:
    """随机初始密码：字母 + 数字（去掉易混淆的 0/O/1/l/I），保证同时含字母和数字"""
    letters = "".join(c for c in string.ascii_letters if c not in "OlI")
    digits = "23456789"
    alphabet = letters + digits
    while True:
        pwd = "".join(secrets.choice(alphabet) for _ in range(length))
        if any(c in digits for c in pwd) and any(c in letters for c in pwd):
            return pwd


def _check_password(password: str) -> None:
    problem = validate_new_password(password)
    if problem:
        raise ManageError(problem.replace("新密码", "密码"))


# ==================== 命令实现（可直接 import） ====================

def create_user(username: str, name: str, role: str = "teacher", school: Optional[str] = None,
                password: Optional[str] = None, must_change_password: bool = True) -> Tuple[int, str]:
    """开通账号，返回 (user_id, 初始密码)"""
    username = (username or "").strip()
    name = (name or "").strip()
    if not username or len(username) > 50 or any(c.isspace() for c in username):
        raise ManageError("账号不能为空、不能含空格，且不超过 50 个字符")
    if not name:
        raise ManageError("请填写老师姓名（--name）")
    if role not in ROLE_LABELS:
        raise ManageError("角色只能是 teacher 或 admin")
    if password is None:
        password = generate_password()
    else:
        _check_password(password)

    engine = _engine()
    try:
        with Session(engine) as session:
            if _find_user(session, username):
                raise ManageError(f"账号已存在：{username}")
            user = User(
                username=username,
                display_name=name[:50],
                school=(school or "").strip() or None,
                role=role,
                password_hash=hash_password(password),
                must_change_password=bool(must_change_password),
                is_active=True,
                session_version=0,
            )
            session.add(user)
            session.commit()
            return user.id, password
    finally:
        engine.dispose()


def reset_password(username: str, password: Optional[str] = None) -> str:
    """重置密码（老师下次登录后必须重新设置），旧会话失效。返回新的初始密码"""
    if password is None:
        password = generate_password()
    else:
        _check_password(password)
    engine = _engine()
    try:
        with Session(engine) as session:
            user = _require_user(session, username)
            user.password_hash = hash_password(password)
            user.must_change_password = True
            user.session_version = int(user.session_version or 0) + 1
            session.commit()
            return password
    finally:
        engine.dispose()


def _set_active(username: str, active: bool) -> None:
    engine = _engine()
    try:
        with Session(engine) as session:
            user = _require_user(session, username)
            user.is_active = active
            user.session_version = int(user.session_version or 0) + 1
            session.commit()
    finally:
        engine.dispose()


def disable_user(username: str) -> None:
    """停用账号：不能再登录，已登录的会话立即失效（数据保留）"""
    _set_active(username, False)


def enable_user(username: str) -> None:
    _set_active(username, True)


def list_users() -> List[Dict]:
    engine = _engine()
    try:
        with Session(engine) as session:
            users = session.execute(select(User).order_by(User.id)).scalars().all()
            return [{
                "id": u.id,
                "username": u.username,
                "display_name": u.display_name or "",
                "school": u.school or "",
                "role": u.role or "teacher",
                "is_active": u.is_active is not False,
                "can_login": u.is_active is not False and is_bcrypt_hash(u.password_hash),
                "must_change_password": bool(u.must_change_password),
                "last_login_at": u.last_login_at.isoformat(sep=" ", timespec="seconds") if u.last_login_at else "",
            } for u in users]
    finally:
        engine.dispose()


def assign_orphans(username: str) -> Dict[str, int]:
    """
    把“无归属”的存量数据归到指定教师（幂等、无损：只改归属字段，不删数据）。
    无归属 = 归属为空、归属账号不存在，或归属于无法登录的历史占位账号（密码不是 bcrypt 哈希，如旧版播种的 teacher/hashed）。
    已属于某位真实教师的数据不会被改动。
    """
    engine = _engine()
    try:
        with Session(engine) as session:
            target = _require_user(session, username)
            if target.is_active is False or not is_bcrypt_hash(target.password_hash):
                raise ManageError(f"账号 {username} 已停用或不能登录，不能接收数据")
            real_ids = [
                u.id for u in session.execute(select(User)).scalars().all()
                if is_bcrypt_hash(u.password_hash)
            ]

            def orphan(col):
                return or_(col.is_(None), col.not_in(real_ids)) if real_ids else True

            # 1) 先让子数据跟随已有真实归属的上级（作业随班级、提交随作业），避免把别的老师的数据归错人
            session.execute(
                update(HomeworkAssignment)
                .where(orphan(HomeworkAssignment.teacher_id))
                .where(select(ClassInfo.id).where(ClassInfo.id == HomeworkAssignment.class_id)
                       .where(ClassInfo.teacher_id.in_(real_ids)).exists())
                .values(teacher_id=select(ClassInfo.teacher_id)
                        .where(ClassInfo.id == HomeworkAssignment.class_id).scalar_subquery())
                .execution_options(synchronize_session=False)
            )
            session.execute(
                update(HomeworkSubmission)
                .where(orphan(HomeworkSubmission.teacher_id))
                .where(select(HomeworkAssignment.id).where(HomeworkAssignment.id == HomeworkSubmission.assignment_id)
                       .where(HomeworkAssignment.teacher_id.in_(real_ids)).exists())
                .values(teacher_id=select(HomeworkAssignment.teacher_id)
                        .where(HomeworkAssignment.id == HomeworkSubmission.assignment_id).scalar_subquery())
                .execution_options(synchronize_session=False)
            )

            # 2) 其余无归属的数据归到目标教师
            counts: Dict[str, int] = {}
            for label, model, col in (
                ("classes", ClassInfo, ClassInfo.teacher_id),
                ("homework_assignments", HomeworkAssignment, HomeworkAssignment.teacher_id),
                ("homework_submissions", HomeworkSubmission, HomeworkSubmission.teacher_id),
                ("wrong_questions", WrongQuestion, WrongQuestion.user_id),
                ("lesson_plans", LessonPlan, LessonPlan.teacher_id),
            ):
                res = session.execute(
                    update(model).where(orphan(col)).values({col.key: target.id})
                    .execution_options(synchronize_session=False)
                )
                counts[label] = res.rowcount or 0
            session.commit()
            return counts
    finally:
        engine.dispose()


# ==================== 命令行 ====================

def _print_table(rows: List[Dict]) -> None:
    if not rows:
        print("（还没有账号）")
        return
    print(f"{'ID':<5}{'账号':<18}{'姓名':<10}{'角色':<8}{'状态':<16}{'最近登录'}")
    for r in rows:
        if not r["is_active"]:
            status = "已停用"
        elif not r["can_login"]:
            status = "不可登录（历史占位）"
        elif r["must_change_password"]:
            status = "待修改初始密码"
        else:
            status = "正常"
        print(f"{r['id']:<5}{r['username']:<18}{r['display_name']:<10}"
              f"{ROLE_LABELS.get(r['role'], r['role']):<8}{status:<16}{r['last_login_at']}")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="manage.py", description="AI 教学助手 管理命令")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("create-user", help="开通账号")
    p.add_argument("--username", required=True, help="登录账号（手机号或工号）")
    p.add_argument("--name", required=True, help="老师姓名")
    p.add_argument("--role", default="teacher", choices=["teacher", "admin"])
    p.add_argument("--school", default=None)
    p.add_argument("--password", default=None, help="指定初始密码（不填则随机生成）")
    p.add_argument("--no-force-change", action="store_true", help="不要求首次登录修改密码（仅测试用）")

    p = sub.add_parser("reset-password", help="重置密码（下次登录需重新设置）")
    p.add_argument("--username", required=True)
    p.add_argument("--password", default=None)

    p = sub.add_parser("disable-user", help="停用账号")
    p.add_argument("--username", required=True)
    p = sub.add_parser("enable-user", help="恢复已停用的账号")
    p.add_argument("--username", required=True)

    sub.add_parser("list-users", help="列出所有账号")

    p = sub.add_parser("assign-orphans", help="把无归属的历史数据归到某位教师")
    p.add_argument("--username", required=True)

    args = parser.parse_args(argv)
    try:
        if args.command == "create-user":
            user_id, password = create_user(
                args.username, args.name, role=args.role, school=args.school,
                password=args.password, must_change_password=not args.no_force_change,
            )
            print(f"已创建账号：{args.username}（{args.name}，{ROLE_LABELS[args.role]}，ID {user_id}）")
            print(f"初始密码: {password}")
            if not args.no_force_change:
                print("请把初始密码当面交给老师；老师首次登录后需要设置新密码。")
        elif args.command == "reset-password":
            password = reset_password(args.username, args.password)
            print(f"已重置账号 {args.username} 的密码，原有登录已失效。")
            print(f"初始密码: {password}")
            print("老师用该密码登录后需要设置新密码。")
        elif args.command == "disable-user":
            disable_user(args.username)
            print(f"已停用账号：{args.username}（数据保留，可用 enable-user 恢复）")
        elif args.command == "enable-user":
            enable_user(args.username)
            print(f"已恢复账号：{args.username}")
        elif args.command == "list-users":
            _print_table(list_users())
        elif args.command == "assign-orphans":
            counts = assign_orphans(args.username)
            labels = {"classes": "班级", "homework_assignments": "作业", "homework_submissions": "批改记录",
                      "wrong_questions": "错题", "lesson_plans": "教案"}
            detail = "，".join(f"{labels[k]} {v}" for k, v in counts.items())
            print(f"已把无归属的数据归到 {args.username}：{detail}")
    except ManageError as e:
        print(f"错误：{e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass
    sys.exit(main())
