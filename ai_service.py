import os
import json
from openai import OpenAI, APITimeoutError
from dotenv import load_dotenv

load_dotenv(override=True)

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
    timeout=90,
    max_retries=2,
)


def _clean_json_text(text: str) -> str:
    text = text.strip()

    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    return text


def _safe_json_loads(text: str) -> dict:
    text = _clean_json_text(text)

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start:end + 1]

    return json.loads(text)


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

        text = response.choices[0].message.content or ""
        print("模型原始输出：", repr(text))

        result = _safe_json_loads(text)

        return {
            "summary": result.get("summary", ""),
            "mood": result.get("mood", "平静"),
            "todos": result.get("todos", []),
        }

    except APITimeoutError:
        print("AI 分析失败：请求超时")
        return {
            "summary": "",
            "mood": "",
            "todos": [],
        }

    except Exception as e:
        print("AI 分析失败：", e)
        return {
            "summary": "",
            "mood": "",
            "todos": [],
        }


def generate_weekly_report(entries: list[dict]) -> dict:
    valid_entries = [
        item for item in entries
        if item.get("content")
    ]

    content_text = "\n\n".join([
        f"日期: {item['created_at']}\n原文: {item['content']}\n总结: {item['summary']}\n情绪: {item['mood']}\n待办: {', '.join(item['todos']) if item['todos'] else '无'}"
        for item in valid_entries
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

        text = response.choices[0].message.content or ""
        result = _safe_json_loads(text)

        return {
            "weekly_summary": result.get("weekly_summary", ""),
            "mood_overview": result.get("mood_overview", ""),
            "key_todos": result.get("key_todos", []),
            "next_week_suggestion": result.get("next_week_suggestion", ""),
        }

    except APITimeoutError:
        return {
            "weekly_summary": "周报生成超时，请稍后重试",
            "mood_overview": "暂无",
            "key_todos": [],
            "next_week_suggestion": "稍后再试一次",
        }

    except Exception as e:
        print("周报生成失败：", e)
        return {
            "weekly_summary": "周报生成失败",
            "mood_overview": "暂无",
            "key_todos": [],
            "next_week_suggestion": "请稍后重试",
        }

def summarize_file_content(content: str) -> dict:
    """
    对文件内容进行 AI 总结
    """
    # 限制内容长度，避免超出模型 token 限制
    max_content_length = 8000
    if len(content) > max_content_length:
        content = content[:max_content_length] + "\n\n（内容已截断，以上为部分内容）"
    
    prompt = f"""
你是一个文档总结助手。请阅读下面的文档内容并进行总结。

要求：
1. summary: 用一段中文总结文档的主要内容，不超过200字
2. key_points: 提取文档中的关键点，返回字符串数组
3. category: 根据内容判断文档类别，从以下选项中选一个：
   工作报告、会议记录、学术论文、个人笔记、数据分析、其他

文档内容：
{content}

返回格式：
{{
  "summary": "文档总结",
  "key_points": ["关键点1", "关键点2", "关键点3"],
  "category": "文档类别"
}}
"""

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "你是一个专业的文档总结助手，只返回 JSON。"},
                {"role": "user", "content": prompt},
            ],
            stream=False,
        )

        text = response.choices[0].message.content or ""
        result = _safe_json_loads(text)

        return {
            "summary": result.get("summary", ""),
            "key_points": result.get("key_points", []),
            "category": result.get("category", "其他"),
        }

    except APITimeoutError:
        return {
            "summary": "总结生成超时，请稍后重试",
            "key_points": [],
            "category": "其他",
        }

    except Exception as e:
        print("文档总结失败：", e)
        return {
            "summary": "总结生成失败",
            "key_points": [],
            "category": "其他",
        }



