from fastapi import FastAPI, Depends, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from database import Base, engine, SessionLocal
from models import Entry
from schemas import EntryCreate, EntryResponse
from ai_service import analyze_entry, generate_weekly_report as generate_weekly_report_ai

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AI 日记助手",
    description="一个以中文为主的个人日记与 AI 总结项目",
    version="1.0.0"
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/", summary="首页")
def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={}
    )


@app.post(
    "/entries",
    response_model=EntryResponse,
    summary="新建日记",
    description="创建一条新的日记记录"
)
def create_entry(entry: EntryCreate, db: Session = Depends(get_db)):
    ai_result = analyze_entry(entry.content)

    new_entry = Entry(
        content=entry.content,
        summary=ai_result["summary"],
        mood=ai_result["mood"],
        todos=ai_result["todos"],
    )

    db.add(new_entry)
    db.commit()
    db.refresh(new_entry)
    return new_entry


@app.get(
    "/entries",
    response_model=list[EntryResponse],
    summary="获取日记列表",
    description="按最新创建时间倒序返回所有日记"
)
def list_entries(db: Session = Depends(get_db)):
    return db.query(Entry).order_by(Entry.id.desc()).all()


@app.delete("/entries/{entry_id}", summary="删除日记")
def delete_entry(entry_id: int, db: Session = Depends(get_db)):
    entry = db.query(Entry).filter(Entry.id == entry_id).first()

    if not entry:
        return {"message": "未找到该日记"}

    db.delete(entry)
    db.commit()
    return {"message": "删除成功"}


@app.get("/weekly-report", summary="生成周报")
def weekly_report(db: Session = Depends(get_db)):
    entries = db.query(Entry).order_by(Entry.created_at.desc()).limit(7).all()

    if not entries:
        return {
            "weekly_summary": "最近没有可用于生成周报的日记",
            "mood_overview": "暂无",
            "key_todos": [],
            "next_week_suggestion": "先记录一条新的日记吧"
        }

    entry_data = [
        {
            "content": entry.content,
            "summary": entry.summary or "",
            "mood": entry.mood or "未知",
            "todos": entry.todos or [],
            "created_at": str(entry.created_at),
        }
        for entry in entries
    ]

    return generate_weekly_report_ai(entry_data)

