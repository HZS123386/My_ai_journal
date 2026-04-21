from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "sqlite:///./journal.db"

engine = create_engine(   #Python和数据库之间的总连接器
    DATABASE_URL,
    connect_args = {"check_same_thread": False},   #允许这个连接在不同线程里被使用
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
                            #autocommit=False   不会自动提交，你要手动 db.commit()
                            #autoflush=False    不会自动把内存里的改动立刻同步到数据库

Base = declarative_base()








