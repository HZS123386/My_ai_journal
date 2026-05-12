from fastapi import FastAPI, Depends, Request, HTTPException, File, UploadFile, Form
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from file_parser import parse_file
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import os
import shutil
from uuid import uuid4

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
from ai_service import analyze_entry, generate_weekly_report as generate_weekly_report_ai, summarize_file_content, transcribe_audio
from auth import hash_password, verify_password, create_access_token, decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")
Base.metadata.create_all(bind=engine)

# 大文件上传配置
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB 单文件大小限制
CHUNK_SIZE = 1 * 1024 * 1024      # 每个分片 1MB
TEMP_DIR = "temp_uploads"          # 临时分片存储目录
UPLOAD_DIR = "uploads"             # 最终文件存储目录
MAX_AUDIO_SIZE = 25 * 1024 * 1024  # 本地语音转写单次音频大小限制
ALLOWED_AUDIO_EXTENSIONS = {'.flac', '.mp3', '.mp4', '.mpeg', '.mpga', '.m4a', '.ogg', '.wav', '.webm'}

# 创建必要的目录
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

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

@app.get("/upload", summary="文件上传页面")
def upload_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="upload.html",
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


@app.get("/entries/{entry_id}", response_model=EntryResponse, summary="获取日记详情")
def get_entry(
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

    return entry


@app.post("/speech/transcribe", summary="语音转写")
async def transcribe_speech(
        file: UploadFile = File(...),
        current_user: User = Depends(get_current_user)
):
    filename = file.filename or "journal-audio.webm"
    file_extension = os.path.splitext(filename)[1].lower()

    if file_extension not in ALLOWED_AUDIO_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="不支持的音频格式。支持 flac、mp3、mp4、mpeg、mpga、m4a、ogg、wav、webm"
        )

    try:
        audio_content = await file.read()
    except Exception:
        raise HTTPException(status_code=500, detail="音频读取失败")

    if not audio_content:
        raise HTTPException(status_code=400, detail="音频文件为空")

    if len(audio_content) > MAX_AUDIO_SIZE:
        raise HTTPException(status_code=413, detail="音频文件过大，最大支持 25MB")

    try:
        return transcribe_audio(audio_content, filename)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except TimeoutError as exc:
        raise HTTPException(status_code=504, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

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


# ==================== 大文件分片上传功能 ====================

@app.post("/upload/init", summary="初始化分片上传")
async def init_upload(
    filename: str = Form(...),
    total_size: int = Form(...),
    current_user: User = Depends(get_current_user)
):
    """
    初始化分片上传，返回文件 ID 用于后续分片上传
    
    参数：
    - filename: 原始文件名
    - total_size: 文件总大小（字节）
    """
    if total_size > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail=f"文件过大，最大支持 {MAX_FILE_SIZE//1024//1024}MB")
    
    file_id = str(uuid4())
    total_chunks = (total_size + CHUNK_SIZE - 1) // CHUNK_SIZE
    
    return {
        "file_id": file_id,
        "total_chunks": total_chunks,
        "chunk_size": CHUNK_SIZE,
        "message": "分片上传已初始化"
    }


@app.post("/upload/chunk", summary="上传分片")
async def upload_chunk(
    file_id: str = Form(...),
    chunk_number: int = Form(...),
    total_chunks: int = Form(...),
    chunk: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    上传单个分片
    
    参数：
    - file_id: 初始化时获取的文件 ID
    - chunk_number: 当前分片序号（从 1 开始）
    - total_chunks: 总分片数
    - chunk: 分片文件
    """
    if chunk_number < 1 or chunk_number > total_chunks:
        raise HTTPException(status_code=400, detail="无效的分片序号")
    
    chunk_dir = os.path.join(TEMP_DIR, file_id)
    os.makedirs(chunk_dir, exist_ok=True)
    
    chunk_path = os.path.join(chunk_dir, f"chunk_{chunk_number}")
    with open(chunk_path, "wb") as f:
        shutil.copyfileobj(chunk.file, f)
    
    return {
        "file_id": file_id,
        "chunk_number": chunk_number,
        "status": "success",
        "message": f"分片 {chunk_number}/{total_chunks} 上传成功"
    }


@app.post("/upload/complete", summary="合并分片并总结")
async def complete_upload(
    file_id: str = Form(...),
    filename: str = Form(...),
    current_user: User = Depends(get_current_user)
):
    """
    完成分片上传，合并所有分片并生成 AI 总结
    
    参数：
    - file_id: 文件 ID
    - filename: 原始文件名
    """
    chunk_dir = os.path.join(TEMP_DIR, file_id)
    
    if not os.path.exists(chunk_dir):
        raise HTTPException(status_code=404, detail="未找到分片数据")
    
    chunks = []
    for f in os.listdir(chunk_dir):
        if f.startswith("chunk_"):
            chunks.append(int(f.split("_")[1]))
    
    if not chunks:
        raise HTTPException(status_code=400, detail="未找到分片")
    
    chunks.sort()
    
    final_path = os.path.join(UPLOAD_DIR, f"{file_id}_{filename}")
    with open(final_path, "wb") as final_file:
        for chunk_num in chunks:
            chunk_path = os.path.join(chunk_dir, f"chunk_{chunk_num}")
            with open(chunk_path, "rb") as chunk_file:
                final_file.write(chunk_file.read())
    
    shutil.rmtree(chunk_dir)
    
    with open(final_path, "rb") as f:
        file_content = f.read()
    
    parsed_content = parse_file(file_content, filename)
    if parsed_content is None:
        os.remove(final_path)
        raise HTTPException(status_code=400, detail="无法解析该文件")
    
    ai_result = summarize_file_content(parsed_content)
    
    return {
        "file_id": file_id,
        "filename": filename,
        "content_length": len(parsed_content),
        "summary": ai_result["summary"],
        "key_points": ai_result["key_points"],
        "category": ai_result["category"],
        "message": "文件上传完成并已总结"
    }


@app.get("/upload/progress/{file_id}", summary="查询上传进度")
async def get_upload_progress(
    file_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    查询分片上传进度
    
    参数：
    - file_id: 文件 ID
    """
    chunk_dir = os.path.join(TEMP_DIR, file_id)
    
    if not os.path.exists(chunk_dir):
        return {"file_id": file_id, "uploaded_chunks": 0, "status": "not_found"}
    
    uploaded_chunks = 0
    for f in os.listdir(chunk_dir):
        if f.startswith("chunk_"):
            uploaded_chunks += 1
    
    return {
        "file_id": file_id,
        "uploaded_chunks": uploaded_chunks,
        "status": "uploading" if uploaded_chunks > 0 else "empty"
    }


@app.delete("/upload/cancel/{file_id}", summary="取消上传")
async def cancel_upload(
    file_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    取消上传并清理分片数据
    
    参数：
    - file_id: 文件 ID
    """
    chunk_dir = os.path.join(TEMP_DIR, file_id)
    
    if os.path.exists(chunk_dir):
        shutil.rmtree(chunk_dir)
    
    return {"file_id": file_id, "message": "上传已取消，分片已清理"}

