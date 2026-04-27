from app import app


def test_app_title():
    assert app.title == "AI 日记助手"


def test_core_routes_exist():
    paths = {route.path for route in app.routes}
    assert "/" in paths
    assert "/login" in paths
    assert "/register" in paths
    assert "/me" in paths
    assert "/entries" in paths
    assert "/weekly-report" in paths

