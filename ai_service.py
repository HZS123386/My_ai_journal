import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(override=True)

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)

def analyze_entry(content: str) -> dict:
    prompt = f"""
你是一个中文日记分析助手。
请严格只返回 JSON，不要加解释。

要求：
1. summary: 用一句中文总结，不超过30字
2. mood: 只能从以下5个中选1个：
开心、焦虑、平静、疲惫、沮丧
3. todos: 从日记中提取待办事项，返回字符串数组
4. 如果没有明确待办，就返回空数组 []

日记内容：
{content}

返回格式：
{{
  "summary": "一句话总结",
  "mood": "平静",
  "todos": ["待办1", "待办2"]
}}
"""

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "你是一个中文日记分析助手，只返回 JSON。"},
                {"role": "user", "content": prompt},
            ],
            stream=False,
        )

        text = response.choices[0].message.content.strip()
        print("模型原始输出：", repr(text))

        if text.startswith("```"):
            lines = text.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()

        result = json.loads(text)

        return {
            "summary": result.get("summary", ""),
            "mood": result.get("mood", "平静"),
            "todos": result.get("todos", []),
        }

    except Exception as e:
        print("AI 分析失败：", repr(e))
        return {
            "summary": "AI 总结生成失败",
            "mood": "平静",
            "todos": [],
        }

def generate_weekly_report(entries: list[dict]) -> dict:
    content_text = "\n\n".join([
        f"日期: {item['created_at']}\n原文: {item['content']}\n总结: {item['summary']}\n情绪: {item['mood']}\n待办: {', '.join(item['todos']) if item['todos'] else '无'}"
        for item in entries
    ])

    prompt = f"""
你是一个中文周报助手。
请根据下面一组日记记录，生成周报，并严格只返回 JSON。

要求：
1. weekly_summary: 用一段中文总结本周整体情况，不超过120字
2. mood_overview: 用一句话描述本周情绪变化
3. key_todos: 提取本周最重要的待办事项，返回字符串数组
4. next_week_suggestion: 给出一句下周建议

返回格式：
{{
  "weekly_summary": "本周整体总结",
  "mood_overview": "本周情绪概览",
  "key_todos": ["待办1", "待办2"],
  "next_week_suggestion": "下周建议"
}}

日记记录：
{content_text}
"""

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "你是一个中文周报助手，只返回 JSON。"},
                {"role": "user", "content": prompt},
            ],
            stream=False,
        )

        text = response.choices[0].message.content.strip()

        if text.startswith("```"):
            lines = text.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()

        result = json.loads(text)

        return {
            "weekly_summary": result.get("weekly_summary", ""),
            "mood_overview": result.get("mood_overview", ""),
            "key_todos": result.get("key_todos", []),
            "next_week_suggestion": result.get("next_week_suggestion", ""),
        }

    except Exception:
        return {
            "weekly_summary": "周报生成失败",
            "mood_overview": "暂无",
            "key_todos": [],
            "next_week_suggestion": "请稍后重试",
        }
