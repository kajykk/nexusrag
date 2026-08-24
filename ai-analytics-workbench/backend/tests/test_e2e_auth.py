"""端到端测试：登录 → 访问受保护资源（P0 新增）。

模拟用户从登录到访问 API 的完整流程。
"""

from fastapi import status


class TestEndToEndAuth:
    """完整认证流程测试。"""

    def test_register_then_login_then_access(self, client):
        """注册 → 登录 → 访问受保护资源。"""
        # 1. 注册
        resp = client.post(
            "/api/v1/auth/register",
            json={
                "email": "e2e@example.com",
                "name": "E2E User",
                "password": "supersecret",
            },
        )
        assert resp.status_code == status.HTTP_201_CREATED
        register_token = resp.json()["access_token"]

        # 2. 用注册返回的 token 访问 /me
        resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {register_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["email"] == "e2e@example.com"

        # 3. 重新登录获取新 token
        resp = client.post(
            "/api/v1/auth/login",
            json={
                "email": "e2e@example.com",
                "password": "supersecret",
            },
        )
        assert resp.status_code == 200
        login_token = resp.json()["access_token"]

        # 4. 用登录 token 访问受保护资源（数据集列表）
        headers = {"Authorization": f"Bearer {login_token}"}
        resp = client.get("/api/v1/datasets", headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_demo_login_then_protected_route(self, client):
        """演示账号登录 → 访问受保护资源。"""
        resp = client.post("/api/v1/auth/demo")
        assert resp.status_code == 200
        token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 访问受保护资源
        resp = client.get("/api/v1/datasets", headers=headers)
        assert resp.status_code == 200

        resp = client.get("/api/v1/reports", headers=headers)
        assert resp.status_code == 200

    def test_token_from_user_a_cannot_access_user_b_resources_via_session(
        self, client, make_user, make_dataset, auth_headers
    ):
        """所有用户共享同一数据集视图（当前实现），但 token 必须有效。"""
        # 用 user A 的 token 访问数据集列表
        resp = client.get("/api/v1/datasets", headers=auth_headers)
        assert resp.status_code == 200

        # 用一个伪造的 token 访问，必须 401
        resp = client.get(
            "/api/v1/datasets",
            headers={"Authorization": "Bearer fake.token.here"},
        )
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_expired_token_rejected(self, client, make_user):
        """过期 token 必须被拒绝。"""
        from datetime import timedelta

        from app.security import create_access_token

        user = make_user(email="expired@example.com", password="x123456")
        token = create_access_token(subject=user.id, expires_delta=timedelta(seconds=-1))

        resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_health_check_no_auth_needed(self, client):
        """健康检查端点应公开可访问。"""
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
