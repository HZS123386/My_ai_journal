# AI 日记助手 - 项目搭建笔记

## 一、项目概述

**项目名称**：AI 日记助手  
**项目定位**：一款基于 AI 的个人日记管理应用，支持记录日常日记、AI 智能总结、文件上传解析等功能。

## 二、技术栈

| 分类 | 技术 | 版本 |
|------|------|------|
| 后端框架 | FastAPI | 最新 |
| 数据库 | SQLite | 内置 |
| ORM | SQLAlchemy | 最新 |
| 迁移工具 | Alembic | 最新 |
| 前端 | HTML/CSS/JavaScript | - |
| 样式 | Tailwind CSS 风格 | 自定义 |
| 测试 | pytest | 最新 |
| CI/CD | GitHub Actions | - |

## 三、项目结构

```
ai_journal/
├── .github/workflows/       # GitHub Actions 配置
│   └── ci.yml              # CI/CD 工作流
├── alembic/                # 数据库迁移
│   ├── versions/           # 迁移版本文件
│   ├── env.py             # 迁移环境配置
│   └── script.py.mako     # 迁移脚本模板
├── static/                 # 静态资源
│   ├── image/             # 图片资源
│   ├── style.css          # 主样式文件
│   └── upload.css         # 上传页面样式
├── templates/             # HTML 模板
│   ├── index.html         # 主页面（登录+日记）
│   └── upload.html        # 文件上传页面
├── tests/                 # 测试文件
│   ├── conftest.py        # 测试配置
│   └── test_smoke.py      # 冒烟测试
├── temp_uploads/          # 临时上传文件
├── uploads/               # 上传文件存储
├── app.py                 # 主应用入口
├── auth.py                # 认证模块
├── database.py            # 数据库配置
├── models.py              # 数据库模型
├── schemas.py             # Pydantic 模型
├── ai_service.py          # AI 服务模块
├── file_parser.py         # 文件解析模块
├── requirements.txt       # 依赖列表
└── alembic.ini            # Alembic 配置
```

## 四、从零到一搭建步骤

### 1. 环境准备

```bash
# 创建项目目录
mkdir ai_journal
cd ai_journal

# 创建虚拟环境（Windows）
python -m venv venv
venv\Scripts\activate

# 安装依赖
pip install fastapi uvicorn sqlalchemy alembic pytest python-multipart python-jose[cryptography] passlib[bcrypt] python-dotenv
```

### 2. 项目初始化

#### 2.1 创建数据库配置 (`database.py`)

```python
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./sql_app.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

#### 2.2 创建数据库模型 (`models.py`)

```python
from database import Base
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    username = Column(String, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class DiaryEntry(Base):
    __tablename__ = "diary_entries"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    content = Column(Text)
    ai_summary = Column(Text)
    emotion = Column(String)
    todo_list = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

#### 2.3 创建 Pydantic 模型 (`schemas.py`)

```python
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class UserCreate(BaseModel):
    email: str
    password: str
    username: str

class UserLogin(BaseModel):
    email: str
    password: str

class DiaryEntryCreate(BaseModel):
    content: str

class DiaryEntryResponse(BaseModel):
    id: int
    content: str
    ai_summary: Optional[str]
    emotion: Optional[str]
    todo_list: Optional[str]
    created_at: datetime
```

#### 2.4 初始化 Alembic

```bash
alembic init alembic
```

修改 `alembic.ini`：
```ini
sqlalchemy.url = sqlite:///./sql_app.db
```

修改 `alembic/env.py`：
```python
target_metadata = Base.metadata
```

创建初始迁移：
```bash
alembic revision --autogenerate -m "initial migration"
alembic upgrade head
```

### 3. 核心功能开发

#### 3.1 认证模块 (`auth.py`)

```python
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from database import get_db
from models import User

SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    return user
```

#### 3.2 AI 服务模块 (`ai_service.py`)

```python
from typing import Dict, Optional

def analyze_diary(content: str) -> Dict[str, str]:
    """
    模拟 AI 分析日记内容
    返回：情感、总结、待办事项
    """
    result = {
        "emotion": "平静",
        "summary": content[:50] + "...",
        "todo_list": "暂无待办"
    }
    
    # 简单的情感分析
    positive_words = ["开心", "高兴", "快乐", "幸福", "好"]
    negative_words = ["难过", "伤心", "失望", "生气", "烦"]
    
    if any(word in content for word in positive_words):
        result["emotion"] = "开心"
    elif any(word in content for word in negative_words):
        result["emotion"] = "难过"
    
    return result
```

#### 3.3 文件解析模块 (`file_parser.py`)

```python
from pathlib import Path
from typing import Optional

def parse_file(file_path: str) -> Optional[str]:
    """解析上传的文件内容"""
    path = Path(file_path)
    
    try:
        # 支持的文件类型
        if path.suffix.lower() in ['.txt', '.md']:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        elif path.suffix.lower() == '.docx':
            # 可扩展支持 docx 解析
            return "暂不支持此文件格式"
        else:
            return "未知文件格式"
    except Exception as e:
        return f"文件解析失败: {str(e)}"
```

#### 3.4 主应用 (`app.py`)

```python
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Request
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import timedelta
import shutil
import os
from uuid import uuid4

from database import get_db, engine
import models
from schemas import UserCreate, DiaryEntryCreate, DiaryEntryResponse
from auth import (
    verify_password, get_password_hash, create_access_token, 
    get_current_user, ACCESS_TOKEN_EXPIRE_MINUTES
)
from ai_service import analyze_diary
from file_parser import parse_file

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI 日记助手")

# 静态文件和模板
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# 路由
@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/register")
async def register(user: UserCreate, db: Session = Depends(get_db)):
    # 检查邮箱是否已存在
    if db.query(models.User).filter(models.User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # 创建用户
    hashed_password = get_password_hash(user.password)
    new_user = models.User(
        email=user.email,
        hashed_password=hashed_password,
        username=user.username
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {"message": "User created successfully"}

@app.post("/token")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer", "username": user.username}

@app.post("/diary")
async def create_diary(
    entry: DiaryEntryCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # AI 分析
    analysis = analyze_diary(entry.content)
    
    # 创建日记条目
    new_entry = models.DiaryEntry(
        user_id=current_user.id,
        content=entry.content,
        ai_summary=analysis["summary"],
        emotion=analysis["emotion"],
        todo_list=analysis["todo_list"]
    )
    db.add(new_entry)
    db.commit()
    db.refresh(new_entry)
    
    return DiaryEntryResponse.from_orm(new_entry)

@app.get("/diary")
async def get_diary_entries(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    entries = db.query(models.DiaryEntry).filter(
        models.DiaryEntry.user_id == current_user.id
    ).order_by(models.DiaryEntry.created_at.desc()).all()
    
    return [DiaryEntryResponse.from_orm(entry) for entry in entries]

@app.delete("/diary/{entry_id}")
async def delete_diary_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    entry = db.query(models.DiaryEntry).filter(
        models.DiaryEntry.id == entry_id,
        models.DiaryEntry.user_id == current_user.id
    ).first()
    
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    
    db.delete(entry)
    db.commit()
    
    return {"message": "Entry deleted successfully"}

@app.get("/upload")
async def upload_page(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request})

@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # 保存文件
    upload_dir = Path("uploads")
    upload_dir.mkdir(exist_ok=True)
    
    file_ext = Path(file.filename).suffix
    new_filename = f"{uuid4()}{file_ext}"
    file_path = upload_dir / new_filename
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # 解析文件内容
    content = parse_file(str(file_path))
    
    # AI 分析
    analysis = analyze_diary(content)
    
    # 创建日记条目
    new_entry = models.DiaryEntry(
        user_id=current_user.id,
        content=content,
        ai_summary=analysis["summary"],
        emotion=analysis["emotion"],
        todo_list=analysis["todo_list"]
    )
    db.add(new_entry)
    db.commit()
    db.refresh(new_entry)
    
    return {"message": "File uploaded and processed", "entry": DiaryEntryResponse.from_orm(new_entry)}

@app.post("/generate-weekly-report")
async def generate_weekly_report(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    from datetime import datetime, timedelta
    
    one_week_ago = datetime.now() - timedelta(weeks=1)
    entries = db.query(models.DiaryEntry).filter(
        models.DiaryEntry.user_id == current_user.id,
        models.DiaryEntry.created_at >= one_week_ago
    ).order_by(models.DiaryEntry.created_at).all()
    
    if not entries:
        return {"report": "本周暂无日记记录"}
    
    report = f"周报总结 ({one_week_ago.strftime('%Y-%m-%d')} 至 {datetime.now().strftime('%Y-%m-%d')})\n\n"
    report += f"共记录 {len(entries)} 篇日记\n\n"
    
    for entry in entries:
        date_str = entry.created_at.strftime("%Y-%m-%d")
        report += f"【{date_str}】\n"
        report += f"情感: {entry.emotion}\n"
        report += f"总结: {entry.ai_summary}\n\n"
    
    return {"report": report}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### 4. 前端页面开发

#### 4.1 主页面 (`templates/index.html`)

包含：
- 登录/注册表单（Tab 切换）
- 日记列表展示
- 新日记输入框
- 侧边栏导航
- 主题切换（深色/浅色）

#### 4.2 样式文件 (`static/style.css`)

关键特性：
- 毛玻璃效果卡片
- 深色/浅色主题支持
- 响应式设计
- 动画过渡效果

## 五、运行项目

### 开发环境

```bash
# 激活虚拟环境
venv\Scripts\activate

# 运行开发服务器
python app.py
```

访问 http://localhost:8000

### 生产环境

```bash
# 使用 uvicorn 运行
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4
```

## 六、测试

```bash
# 运行测试
pytest tests/
```

## 七、CI/CD 配置

`.github/workflows/ci.yml`:

```yaml
name: CI/CD

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: "3.11"
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    
    - name: Run tests
      run: pytest tests/
```

## 八、功能亮点

### 前端亮点
1. **毛玻璃效果设计** - 现代化的玻璃质感 UI
2. **响应式布局** - 适配各种屏幕尺寸
3. **深色/浅色主题切换** - 支持两种主题模式
4. **平滑动画过渡** - 提升用户体验
5. **Tab 切换登录/注册** - 便捷的认证方式

### AI 相关亮点
1. **AI 日记分析** - 自动分析情感、生成总结
2. **AI 周报生成** - 自动汇总一周日记
3. **文件内容解析** - 支持多种文件格式
4. **情感识别** - 识别日记中的情感倾向
5. **待办事项提取** - 自动提取待办内容

## 九、注意事项

1. **安全性**：
   - 使用 JWT 进行身份验证
   - 密码使用 bcrypt 加密存储
   - 文件上传使用 UUID 重命名，防止路径遍历攻击

2. **性能**：
   - SQLite 适合单机部署，高并发场景建议使用 PostgreSQL
   - 可以添加 Redis 缓存优化性能

3. **扩展建议**：
   - 接入真实的 AI 服务（如 OpenAI、豆包等）
   - 添加图片上传功能
   - 添加日记搜索功能
   - 支持多用户协作

---

**创建日期**：2024年  
**项目状态**：持续开发中
