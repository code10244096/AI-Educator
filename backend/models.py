from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class User(Base):
    """用户表"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default="student")  # student, teacher, admin
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关系
    homework_submissions = relationship("HomeworkSubmission", back_populates="user")
    wrong_questions = relationship("WrongQuestion", back_populates="user")


class ClassInfo(Base):
    """班级信息表"""
    __tablename__ = "classes"
    
    id = Column(Integer, primary_key=True, index=True)
    class_name = Column(String(100), nullable=False)
    teacher_id = Column(Integer, ForeignKey("users.id"))
    total_students = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关系
    homework_assignments = relationship("HomeworkAssignment", back_populates="class_info")


class HomeworkAssignment(Base):
    """作业布置表"""
    __tablename__ = "homework_assignments"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    class_id = Column(Integer, ForeignKey("classes.id"))
    teacher_id = Column(Integer, ForeignKey("users.id"))
    reference_answer = Column(Text)  # 参考答案
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关系
    class_info = relationship("ClassInfo", back_populates="homework_assignments")
    submissions = relationship("HomeworkSubmission", back_populates="assignment")


class HomeworkSubmission(Base):
    """作业提交表"""
    __tablename__ = "homework_submissions"
    
    id = Column(Integer, primary_key=True, index=True)
    assignment_id = Column(Integer, ForeignKey("homework_assignments.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    image_paths = Column(Text)  # JSON 字符串存储多张图片路径
    ocr_result = Column(Text)  # OCR 识别结果
    grading_result = Column(Text)  # JSON 格式存储批改结果
    wrong_count = Column(Integer, default=0)  # 错题数量
    score = Column(Float)  # 分数
    status = Column(String(20), default="pending")  # pending, grading, completed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关系
    assignment = relationship("HomeworkAssignment", back_populates="submissions")
    user = relationship("User", back_populates="homework_submissions")


class WrongQuestion(Base):
    """错题表"""
    __tablename__ = "wrong_questions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    question_text = Column(Text, nullable=False)  # 原题
    user_answer = Column(Text)  # 用户答案
    correct_answer = Column(Text)  # 正确答案
    knowledge_point = Column(String(200))  # 知识点
    subject = Column(String(50))  # 科目
    error_date = Column(DateTime(timezone=True), server_default=func.now())
    is_mastered = Column(Boolean, default=False)  # 是否已掌握
    variant_questions = Column(Text)  # JSON 格式存储变式题
    image_path = Column(String(500))  # 原题图片路径
    
    # 关系
    user = relationship("User", back_populates="wrong_questions")


class LessonPlan(Base):
    """教案表"""
    __tablename__ = "lesson_plans"
    
    id = Column(Integer, primary_key=True, index=True)
    teacher_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String(200), nullable=False)  # 课题名称
    period = Column(String(50))  # 课时数
    student_level = Column(String(50))  # 学生基础
    requirements = Column(Text)  # 额外要求
    content = Column(Text)  # 教案内容（Markdown 格式）
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
