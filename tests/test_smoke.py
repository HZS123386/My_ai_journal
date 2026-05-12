from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import app, get_current_user, get_db
from database import Base
from models import Entry, User


def test_app_title():
    assert app.title == "AI 日记助手"


def test_core_routes_exist():
    paths = {route.path for route in app.routes}
    assert "/" in paths
    assert "/login" in paths
    assert "/register" in paths
    assert "/me" in paths
    assert "/entries" in paths
    assert "/entries/{entry_id}" in paths
    assert "/speech/transcribe" in paths
    assert "/weekly-report" in paths


def test_entry_detail_returns_current_user_entry(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False},
    )
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    db = testing_session()
    now = datetime.now(UTC)
    entry = Entry(
        content="今天完成了语音输入测试",
        summary="完成语音测试",
        mood="开心",
        todos=["整理答辩材料"],
        user_id=1,
        created_at=now,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    entry_id = entry.id
    db.close()

    def override_db():
        session = testing_session()
        try:
            yield session
        finally:
            session.close()

    def override_current_user():
        return User(
            id=1,
            username="tester",
            email="tester@example.com",
            password_hash="hashed",
            created_at=now,
        )

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_current_user

    try:
        client = TestClient(app)
        response = client.get(f"/entries/{entry_id}")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["content"] == "今天完成了语音输入测试"
    assert response.json()["todos"] == ["整理答辩材料"]

