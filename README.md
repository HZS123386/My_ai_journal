# AI 日记助手

## 功能
- 日记录入
- 语音输入
- AI 总结
- 情绪识别
- 待办提取
- 本周周报

## 技术栈
- FastAPI
- SQLite
- Jinja2
- DeepSeek API

## 本地运行
```bash
python -m pip install -r requirements.txt
python -m uvicorn app:app --reload
```

## 语音识别配置
文本分析使用 DeepSeek，语音输入使用本地 `faster-whisper` 转写。推荐使用 `small` 模型：

```env
DEEPSEEK_API_KEY=你的 DeepSeek API Key
WHISPER_MODEL_SIZE=small
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
WHISPER_LANGUAGE=zh
```

支持的音频格式：`flac`、`mp3`、`mp4`、`mpeg`、`mpga`、`m4a`、`ogg`、`wav`、`webm`。

可选模型大小：

- `base`：速度更快，占用更小，准确率一般。
- `small`：本项目推荐，中文识别效果和本地运行成本比较均衡。
- `medium` / `large-v3`：准确率更高，但更吃内存和显卡。

首次运行会下载 faster-whisper 对应模型文件；如果部署环境不能联网，需要提前下载模型或把 `WHISPER_MODEL_SIZE` 改成本地模型目录路径。

---

