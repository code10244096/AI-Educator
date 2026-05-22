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
            "model": model or self.model,
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
    
    async def grade_homework(
        self,
        ocr_result: str,
        reference_answer: Optional[str] = None,
        subject: str = "数学"
    ) -> Dict:
        """批改作业"""
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
