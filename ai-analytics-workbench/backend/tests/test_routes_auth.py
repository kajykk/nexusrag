"""认证路由测试：注册 / 登录 / me / demo（P0 新增）。"""

from fastapi import status


class TestRegister:
    def test_register_success(self, client):
        resp = client.post(
            "/api/v1/auth/register",
            json={
                "email": "user@example.com",
                "name": "Test User",
                "password": "password123",
            },
        )
        assert resp.status_code == status.HTTP_201_CREATED
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "user@example.com"
        assert data["user"]["name"] == "Test User"
        assert "hashed_password" not in data["user"]

    def test_register_short_password_rejected(self, client):
        resp = client.post(
            "/api/v1/auth/register",
            json={
                "email": "user@example.com",
                "name": "Test",
                "password": "123",
            },
        )
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_register_invalid_email_rejected(self, client):
        resp = client.post(
            "/api/v1/auth/register",
            json={
                "email": "not-an-email",
                "name": "Test",
                "password": "password123",
            },
        )
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_register_duplicate_email(self, client, make_user):
        make_user(email="dup@example.com")
        resp = client.post(
            "/api/v1/auth/register",
            json={
                "email": "dup@example.com",
                "name": "Dup",
                "password": "password123",
            },
        )
        assert resp.status_code == status.HTTP_409_CONFLICT

    def test_password_is_hashed_in_db(self, client, db_session):
        """确保密码不会以明文存入数据库。"""
        from app.models import User

        client.post(
            "/api/v1/auth/register",
            json={
                "email": "secure@example.com",
                "name": "Test",
                "password": "plaintext-password",
            },
        )
        user = db_session.query(User).filter(User.email == "secure@example.com").first()
        assert user is not None
        assert user.hashed_password != "plaintext-password"
        assert "$2" in user.hashed_password  # bcrypt 前缀


class TestLogin:
    def test_login_success(self, client, make_user):
        make_user(email="login@example.com", password="password123")
        resp = client.post(
            "/api/v1/auth/login",
            json={
                "email": "login@example.com",
                "password": "password123",
            },
        )
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert "access_token" in data
        assert data["user"]["email"] == "login@example.com"

    def test_login_wrong_password(self, client, make_user):
        make_user(email="login@example.com", password="password123")
        resp = client.post(
            "/api/v1/auth/login",
            json={
                "email": "login@example.com",
                "password": "wrong",
            },
        )
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_unknown_email(self, client):
        resp = client.post(
            "/api/v1/auth/login",
            json={
                "email": "nobody@example.com",
                "password": "any",
            },
        )
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_inactive_user(self, client, make_user, db_session):
        """被禁用的账号无法登录。"""
        user = make_user(email="inactive@example.com", password="password123")
        user.is_active = False
        db_session.commit()

        resp = client.post(
            "/api/v1/auth/login",
            json={
                "email": "inactive@example.com",
                "password": "password123",
            },
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN


class TestMe:
    def test_me_with_valid_token(self, client, auth_headers):
        resp = client.get("/api/v1/auth/me", headers=auth_headers)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["email"] == "test@example.com"

    def test_me_without_token(self, client):
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_me_with_invalid_token(self, client):
        resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_me_with_malformed_header(self, client):
        resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "NotBearer abc"},
        )
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


class TestDemoAccount:
    def test_demo_creates_user_if_not_exists(self, client):
        resp = client.post("/api/v1/auth/demo")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert "access_token" in data
        assert data["user"]["email"] == "demo@analytics-workbench.dev"

    def test_demo_idempotent(self, client):
        # 第一次调用
        resp1 = client.post("/api/v1/auth/demo")
        assert resp1.status_code == 200
        uid1 = resp1.json()["user"]["id"]

        # 第二次调用应返回相同用户（不创建新账号）
        resp2 = client.post("/api/v1/auth/demo")
        assert resp2.status_code == 200
        uid2 = resp2.json()["user"]["id"]
        assert uid1 == uid2

    def test_demo_token_can_call_me(self, client):
        resp = client.post("/api/v1/auth/demo")
        token = resp.json()["access_token"]
        resp2 = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp2.status_code == 200
        assert resp2.json()["email"] == "demo@analytics-workbench.dev"
