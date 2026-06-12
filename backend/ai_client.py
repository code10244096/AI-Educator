import httpx
import base64
import json
from typing import Optional, List, Dict
from config import settings


class AIClient:
    """统一 AI 模型调用客户端"""
    
    def __init__(self):
        self.api_key = settings.AI_API_KEY
        self.base_url = settings.AI_API_BASE_URL
        self.ocr_model = settings.OCR_MODEL
        self.grader_model = settings.GRADER_MODEL
        self.lessonplan_model = settings.LESSONPLAN_MODEL
        # 调试模式：当 API key 未配置时使用模拟数据
        self.is_debug_mode = not self.api_key or self.api_key == "your_api_key_here"
    
    async def _make_request(
        self,
        messages: List[Dict],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4000
    ) -> str:
        """发送请求到 AI 模型"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model or self.grader_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        async with httpx.AsyncClient(timeout=300.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                result = response.json()
                return result["choices"][0]["message"]["content"]
            except httpx.ReadTimeout as e:
                raise Exception(f"AI 模型响应超时，请重试或减少生成内容要求")
            except httpx.ConnectError as e:
                raise Exception(f"无法连接到 AI 模型服务，请检查网络")
            except httpx.HTTPStatusError as e:
                raise Exception(f"AI 模型请求失败：{e.response.status_code} - {e.response.text[:200]}")
            except Exception as e:
                raise Exception(f"AI 模型调用失败：{str(e)}")
    
    async def ocr_image(self, image_path: str) -> str:
        """OCR 识别图片中的文字"""
        # 调试模式：返回模拟的OCR结果
        if self.is_debug_mode:
            return self._mock_ocr_image(image_path)
        
        # 读取图片并转换为 base64
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode()
        
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "请识别这张图片中的所有文字内容，包括题目、公式、学生作答等。保持原有的格式和顺序。"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_data}"
                        }
                    }
                ]
            }
        ]
        
        return await self._make_request(messages, model=self.ocr_model)
    
    def _mock_ocr_image(self, image_path: str) -> str:
        """模拟 OCR 识别（调试模式）"""
        # 返回模拟的作业内容，用于测试
        return """# 高考数学作业集

## 学生作业部分

### 1. 填空题
已知 \\( a = \\log_3 2 \\)，则 \\( \\log_3 18 = \\) ______（用 \\( a \\) 表示）。

**学生答案**：\\(2+a\\)

---

### 2. 填空题
函数 \\( f(x) = \\sqrt{3}\\sin x + \\cos x \\) 的最大值为 ______。

**学生答案**：\\(2\\)

---

### 3. 填空题
已知 \\( \\vec{a} = (1,1) \\)，\\( \\vec{b} = (2, -1) \\)，则 \\( \\vec{a} \\) 在 \\( \\vec{b} \\) 方向上的投影为 ______。

**学生答案**：\\(\\frac{1}{\\sqrt{5}}\\)

---

### 4. 填空题
圆 \\( x^2 + y^2 - 2x + 4y + 1 = 0 \\) 的半径为 ______。

**学生答案**：\\(2\\)

---

### 5. 填空题
已知 \\( \\tan\\alpha = \\frac{1}{2} \\)，则 \\( \\frac{\\sin\\alpha - 2\\cos\\alpha}{\\sin\\alpha + \\cos\\alpha} = \\) ______。

**学生答案**：\\(-1\\)

---

## 参考答案
1. \\(2+a\\)
2. \\(2\\)
3. \\(\\frac{1}{\\sqrt{5}}\\)
4. \\(2\\)
5. \\(-1\\)"""
    
    async def grade_homework(
        self,
        ocr_result: str,
        reference_answer: Optional[str] = None,
        subject: str = "数学"
    ) -> Dict:
        """批改作业"""
        # 调试模式：使用模拟批改结果
        if self.is_debug_mode:
            return self._mock_grade_homework(ocr_result, reference_answer, subject)
        
        prompt = f"""
你是一位经验丰富且专业的{subject}老师，请批改这份作业。

学生作答内容：
{ocr_result}

{f'参考答案：{reference_answer}' if reference_answer else ''}

请以 JSON 格式返回批改结果，包含以下字段：
- total_questions: 题目总数
- correct_count: 正确数量
- wrong_count: 错误数量
- score: 分数（0-100）
- questions: 每道题的详细批改结果数组，包含：
  - question_number: 题号
  - question_text: 题目内容
  - student_answer: 学生答案
  - correct_answer: 正确答案
  - is_correct: 是否正确
  - explanation: 解析

只返回 JSON，不要其他内容。
"""
        
        messages = [{"role": "user", "content": prompt}]
        result = await self._make_request(messages, model=self.grader_model, temperature=0.3)
        
        # 解析 JSON
        try:
            # 清理可能的 markdown 标记
            result = result.replace("```json", "").replace("```", "").strip()
            return json.loads(result)
        except:
            return {
                "error": "批改结果解析失败",
                "raw_result": result
            }
    
    def _mock_grade_homework(
        self,
        ocr_result: str,
        reference_answer: Optional[str] = None,
        subject: str = "数学"
    ) -> Dict:
        """模拟批改作业（调试模式）"""
        import re
        
        # 首先从OCR结果中提取参考答案部分
        extracted_ref_answer = reference_answer
        if not extracted_ref_answer:
            # 尝试从OCR结果中提取参考答案
            ref_match = re.search(r"##\s*参考答案\s*\n(.+?)(?=\n##|\Z)", ocr_result, re.DOTALL)
            if ref_match:
                extracted_ref_answer = ref_match.group(1).strip()
        
        # 解析题目（匹配 ### 数字. 开头的内容）
        questions = []
        question_pattern = r"###\s*(\d+)\.\s*(.*?)(?=\n###\s*\d+\.|##\s|$)"
        matches = re.finditer(question_pattern, ocr_result, re.DOTALL)
        
        for match in matches:
            question_number = int(match.group(1))
            content = match.group(2).strip()
            
            # 提取学生答案
            student_answer = ""
            answer_match = re.search(r"学生答案[：:]?\s*(.+?)(?=\n---|\n###|\Z)", content, re.DOTALL)
            if answer_match:
                student_answer = answer_match.group(1).strip()
            elif "**学生答案**" in content:
                parts = content.split("**学生答案**")
                if len(parts) > 1:
                    remaining = parts[1]
                    # 提取到下一个分隔符或结束
                    end_idx = remaining.find("\n---")
                    if end_idx == -1:
                        end_idx = remaining.find("\n###")
                    if end_idx == -1:
                        end_idx = len(remaining)
                    student_answer = remaining[:end_idx].strip()
            
            # 解析参考答案（如果有）
            correct_answer = ""
            if extracted_ref_answer:
                ref_match = re.search(rf"{question_number}\.\s*([^\n]+)", extracted_ref_answer)
                if ref_match:
                    correct_answer = ref_match.group(1).strip()
            
            # 判断是否正确（简单匹配）
            is_correct = False
            explanation = ""
            
            if student_answer and correct_answer:
                # 去除空格和换行进行比较
                clean_student = re.sub(r'\s+', '', student_answer).lower()
                clean_correct = re.sub(r'\s+', '', correct_answer).lower()
                
                # 简单匹配逻辑
                if clean_student == clean_correct:
                    is_correct = True
                    explanation = "答案正确。"
                elif clean_student in clean_correct or clean_correct in clean_student:
                    is_correct = True
                    explanation = "答案正确。"
                else:
                    explanation = f"答案错误。学生答案：{student_answer}，正确答案：{correct_answer}"
            else:
                # 随机决定对错（模拟）
                is_correct = (question_number % 3) != 0  # 大约 2/3 正确
                if is_correct:
                    explanation = "答案正确。"
                else:
                    explanation = f"答案错误。需要进一步检查解题过程。"
            
            questions.append({
                "question_number": question_number,
                "question_text": content[:100] + "..." if len(content) > 100 else content,
                "student_answer": student_answer if student_answer else "未作答",
                "correct_answer": correct_answer if correct_answer else "未提供",
                "is_correct": is_correct,
                "explanation": explanation
            })
        
        total_questions = len(questions)
        correct_count = sum(1 for q in questions if q["is_correct"])
        wrong_count = total_questions - correct_count
        score = round((correct_count / total_questions) * 100) if total_questions > 0 else 0
        
        return {
            "total_questions": total_questions,
            "correct_count": correct_count,
            "wrong_count": wrong_count,
            "score": score,
            "questions": questions,
            "debug_mode": True,
            "message": "使用模拟批改模式（调试用）"
        }
    
    async def generate_variant_questions(
        self,
        question_text: str,
        knowledge_point: str,
        count: int = 3
    ) -> List[Dict]:
        """生成变式题"""
        prompt = f"""
请为以下题目生成{count}道变式题：

原题：{question_text}
知识点：{knowledge_point}

每道变式题应该：
1. 考察相同的知识点
2. 难度相近但具体数值或条件不同
3. 有完整的题目和答案

请以 JSON 数组格式返回，包含以下字段：
- variant_number: 变式题号
- question_text: 题目内容
- answer: 答案
- difficulty: 难度（easy/medium/hard）

只返回 JSON 数组，不要其他内容。
"""
        
        messages = [{"role": "user", "content": prompt}]
        result = await self._make_request(messages, model=self.grader_model, temperature=0.7)
        
        try:
            result = result.replace("```json", "").replace("```", "").strip()
            return json.loads(result)
        except:
            return []
    
    async def generate_lesson_plan(
        self,
        topic: str,
        period: str = "1 课时",
        student_level: str = "中等",
        requirements: str = "",
        question_bank_context: str = ""
    ) -> str:
        """生成教案"""
        question_context = ""
        if question_bank_context:
            question_context = f"""

【题库参考资料 - 请在生成教案时参考以下内容】

{question_bank_context}

请根据以上题库资料，在教案中：
1. 使用题库中的真题作为课堂练习和作业
2. 参考教学建议来设计教学环节
3. 在易错点预警中强调常见错误
4. 根据难度分布合理安排教学节奏
"""
        
        prompt = f"""
请为以下课题生成一份详细的教案：

你是一位高三数学把关教师。请为{topic}课题生成一份可直接用于课堂的详细教案。

要求：
1. 导入部分必须用一个具体例子（比如物理瞬时速度、几何图形切线），不得使用"复习上节课内容"这种话。
2. 每个知识点至少配一个学生易错点的预警（例如：求切线时容易忽略点是否在曲线上）。
3. 课堂练习包含2道题：一道基础模仿题，一道高考改编题（附简短解析）。
4. 作业分两层：必做题（3道基础）和选做题（1道提升）。
5. 语言简洁，不要空话。

课题名称：{topic}
课时数：{period}
学生基础：{student_level}
{f'额外要求：{requirements}' if requirements else ''}
{question_context}

教案应包含以下内容：
1. 教学目标（知识与技能、过程与方法、高考常用的技巧与难度）
2. 教学重难点
3. 教学方法
4. 教学准备
5. 教学过程（导入、新授、练习、总结、作业）
6. 板书设计
7. 教学反思

请使用 Markdown 格式，标题使用#号标记。
"""
        
        messages = [{"role": "user", "content": prompt}]
        return await self._make_request(messages, model=self.lessonplan_model, temperature=0.7)


# 全局客户端实例
ai_client = AIClient()
