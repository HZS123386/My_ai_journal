from fastapi import FastAPI, Depends, Request, HTTPException, File, UploadFile
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from file_parser import parse_file
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from database import Base, engine, SessionLocal
from models import Entry, User
from schemas import (
    EntryCreate,
    EntryResponse,
    UserCreate,
    UserLogin,
    UserResponse,
    TokenResponse,
)
from ai_service import analyze_entry, generate_weekly_report as generate_weekly_report_ai, summarize_file_content
from auth import hash_password, verify_password, create_access_token, decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")
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

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="无效或过期的 token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="token 缺少用户信息")

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")

    return user

#注册
@app.post("/register", response_model=UserResponse, summary="用户注册")
def register(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(
        (User.email == user.email) | (User.username == user.username)
    ).first()

    if existing_user:
        raise HTTPException(status_code=400, detail="用户名或邮箱已存在")

    new_user = User(
        username=user.username,
        email=user.email,
        password_hash=hash_password(user.password),
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

#登录
@app.post("/login", response_model=TokenResponse, summary="用户登录")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == form_data.username).first()

    if not db_user or not verify_password(form_data.password, db_user.password_hash):
        raise HTTPException(status_code=401, detail="邮箱或密码错误")

    access_token = create_access_token(
        data={"sub": str(db_user.id), "email": db_user.email}
    )

    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/me", response_model=UserResponse, summary="获取当前登录用户")
def get_me(current_user: User = Depends(get_current_user)):
    return current_user

#首页
@app.get("/", summary="首页")
def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={}
    )

#新建
@app.post(
    "/entries",
    response_model=EntryResponse,
    summary="新建日记",
    description="创建一条新的日记记录"
)
def create_entry(
        entry: EntryCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    ai_result = analyze_entry(entry.content)

    new_entry = Entry(
        content=entry.content,
        summary=ai_result["summary"],
        mood=ai_result["mood"],
        todos=ai_result["todos"],
        user_id=current_user.id,
    )

    db.add(new_entry)
    db.commit()
    db.refresh(new_entry)
    return new_entry

#获取
@app.get(
    "/entries",
    response_model=list[EntryResponse],
    summary="获取日记列表",
    description="按最新创建时间倒序返回所有日记"
)
def list_entries(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    return (
            db.query(Entry)
            .filter(Entry.user_id == current_user.id)
            .order_by(Entry.id.desc())
            .all()
    )

#删除
@app.delete("/entries/{entry_id}", summary="删除日记")
def delete_entry(
        entry_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    entry = (
        db.query(Entry)
        .filter(Entry.id == entry_id, Entry.user_id == current_user.id)
        .first()
    )

    if not entry:
        raise HTTPException(status_code=404, detail="未找到该日记")

    db.delete(entry)
    db.commit()
    return {"message": "删除成功"}

#生成周报
@app.get("/weekly-report", summary="生成周报")
def weekly_report(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    entries = (
        db.query(Entry)
        .filter(Entry.user_id == current_user.id)
        .order_by(Entry.created_at.desc())
        .limit(7)
        .all()
    )

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
            "mood": entry.mood or "",
            "todos": entry.todos or [],
            "created_at": str(entry.created_at),
        }
        for entry in entries
    ]

    return generate_weekly_report_ai(entry_data)

# 文件上传并总结
@app.post("/upload-file", summary="上传文件并总结")
async def upload_file(
        file: UploadFile = File(...),
        current_user: User = Depends(get_current_user)
):
    # 检查文件类型
    allowed_extensions = ['.txt', '.docx', '.xlsx', '.pdf']
    file_extension = '.' + file.filename.split('.')[-1].lower()
    
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"不支持的文件格式。支持的格式：{', '.join(allowed_extensions)}"
        )
    
    # 读取文件内容
    try:
        file_content = await file.read()
    except Exception as e:
        raise HTTPException(status_code=500, detail="文件读取失败")
    
    # 解析文件
    parsed_content = parse_file(file_content, file.filename)
    if parsed_content is None:
        raise HTTPException(status_code=400, detail="无法解析该文件")
    
    # AI 总结
    ai_result = summarize_file_content(parsed_content)
    
    return {
        "filename": file.filename,
        "content_length": len(parsed_content),
        "summary": ai_result["summary"],
        "key_points": ai_result["key_points"],
        "category": ai_result["category"],
    }

