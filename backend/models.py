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
    members = relationship("ClassMember", back_populates="class_info")


class ClassMember(Base):
    """班级成员表"""
    __tablename__ = "class_members"
    
    id = Column(Integer, primary_key=True, index=True)
    class_id = Column(Integer, ForeignKey("classes.id"))
    name = Column(String(50), nullable=False)
    gender = Column(String(10), default="男")
    order_index = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    class_info = relationship("ClassInfo", back_populates="members")


class HomeworkAssignment(Base):
    """作业布置表"""
    __tablename__ = "homework_assignments"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    class_id = Column(Integer, ForeignKey("classes.id"))
    teacher_id = Column(Integer, ForeignKey("users.id"))
    reference_answer = Column(Text)  # 参考答案
    assign_date = Column(String(20))
    deadline = Column(String(20))
    status = Column(String(20), default="待批改")  # 待批改 / 已批改
    subject = Column(String(50), default="数学")
    description = Column(Text)
    dataset_file_id = Column(Integer)
    total_students = Column(Integer, default=45)
    avg_score = Column(Float)
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
    student_name = Column(String(50))
    dataset_file_id = Column(Integer)
    is_test_data = Column(Boolean, default=False)
    submit_time = Column(String(50))
    file_count = Column(Integer, default=1)
    image_paths = Column(Text)  # JSON 字符串存储多张图片路径
    ocr_result = Column(Text)  # OCR 识别结果
    grading_result = Column(Text)  # JSON 格式存储批改结果
    wrong_count = Column(Integer, default=0)  # 错题数量
    score = Column(Float)  # 分数
    status = Column(String(20), default="pending")  # pending, grading, completed
    grading_status = Column(String(20), default="待批改")  # 待批改 / 已批改 / 未提交
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


class QuestionBank(Base):
    """题库表 - 支持多学科、多学龄、多题型"""
    __tablename__ = "question_bank"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # 基本信息
    question_text = Column(Text, nullable=False)  # 题目内容（支持 Markdown/LaTeX）
    answer = Column(Text, nullable=False)  # 标准答案
    solution = Column(Text)  # 详细解答过程
    question_type = Column(String(50), nullable=False)  # 选择题/填空题/解答题/判断题/证明题
    
    # 分类信息
    subject = Column(String(50), nullable=False, index=True)  # 数学/物理/化学/语文/英语等
    education_level = Column(String(50), nullable=False, index=True)  # 小学/初中/高中
    exam_type = Column(String(100), index=True)  # 高考/中考/月考/模拟考/竞赛
    year = Column(Integer, index=True)  # 年份
    region = Column(String(100))  # 地区（如：全国卷/北京卷/上海卷）
    
    # 知识点与难度
    knowledge_points = Column(Text)  # JSON 数组存储多个知识点
    difficulty = Column(Integer, default=3)  # 1-5 难度等级
    score = Column(Float)  # 分值
    
    # RAG 相关
    embedding = Column(Text)  # JSON 数组存储向量（用于语义检索）
    search_keywords = Column(Text)  # JSON 数组存储关键词
    
    # 来源与状态
    source_url = Column(String(500))  # 原始来源 URL
    is_verified = Column(Boolean, default=False)  # 是否已审核
    
    # 教案辅助字段
    teaching_tips = Column(Text)  # 教学建议
    common_mistakes = Column(Text)  # 常见错误
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # 关系
    variants = relationship("QuestionVariant", back_populates="original_question")


class QuestionVariant(Base):
    """变式题表 - 基于原题生成的变式练习"""
    __tablename__ = "question_variants"
    
    id = Column(Integer, primary_key=True, index=True)
    original_id = Column(Integer, ForeignKey("question_bank.id"))
    question_text = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    solution = Column(Text)
    variant_type = Column(String(50))  # 数值变化/条件变换/逆向思维/综合应用
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关系
    original_question = relationship("QuestionBank", back_populates="variants")
