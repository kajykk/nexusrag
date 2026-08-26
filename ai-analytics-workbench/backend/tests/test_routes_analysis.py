"""分析任务路由测试（P0 新增）。"""

import os

from fastapi import status


class TestAnalysisRoutesAuth:
    def test_list_requires_auth(self, client):
        resp = client.get("/api/v1/analyses")
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_detail_requires_auth(self, client, make_dataset):
        ds = make_dataset()
        resp = client.get(f"/api/v1/analyses/9999?dataset_id={ds.id}")
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_requires_auth(self, client, make_dataset):
        ds = make_dataset()
        resp = client.post(
            "/api/v1/analyses",
            json={
                "dataset_id": ds.id,
                "question": "总销售额是多少",
            },
        )
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


class TestAnalysisRoutesWithAuth:
    def test_create_invalid_dataset(self, client, auth_headers):
        resp = client.post(
            "/api/v1/analyses",
            headers=auth_headers,
            json={
                "dataset_id": 9999,
                "question": "测试问题",
            },
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_create_empty_question_rejected(self, client, auth_headers, make_dataset):
        ds = make_dataset()
        resp = client.post(
            "/api/v1/analyses",
            headers=auth_headers,
            json={
                "dataset_id": ds.id,
                "question": "",
            },
        )
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_list_with_dataset_id_filter(self, client, auth_headers, make_dataset, db_session):
        """列表端点应支持 dataset_id 查询参数过滤。"""
        from app.models import Analysis

        ds1 = make_dataset(name="DS1")
        ds2 = make_dataset(name="DS2")

        # 在 ds1 创建 2 个分析，ds2 创建 1 个
        db_session.add_all(
            [
                Analysis(dataset_id=ds1.id, question="q1", status="succeeded"),
                Analysis(dataset_id=ds1.id, question="q2", status="failed"),
                Analysis(dataset_id=ds2.id, question="q3", status="pending"),
            ]
        )
        db_session.commit()

        # 过滤 ds1
        resp = client.get(
            f"/api/v1/analyses?dataset_id={ds1.id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 2
        for item in body:
            assert item["dataset_id"] == ds1.id

    def test_detail_not_found(self, client, auth_headers):
        resp = client.get("/api/v1/analyses/9999", headers=auth_headers)
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_detail_returns_full_data(self, client, auth_headers, make_dataset, db_session):
        import json

        from app.models import Analysis

        ds = make_dataset()
        analysis = Analysis(
            dataset_id=ds.id,
            question="测试问题",
            status="succeeded",
            generated_code="result = 42",
            result_data=json.dumps({"result": 42, "summary": "答案是 42"}),
            chart_config=json.dumps({"title": "图表"}),
        )
        db_session.add(analysis)
        db_session.commit()
        db_session.refresh(analysis)

        resp = client.get(f"/api/v1/analyses/{analysis.id}", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["generated_code"] == "result = 42"
        assert body["result_data"]["result"] == 42
        assert body["chart_config"]["title"] == "图表"


class TestChartEndpoint:
    """图表认证下发端点（替代匿名静态挂载的安全回归）。"""

    def _make_analysis_with_chart(self, db_session, make_dataset, owner_id=None, tmp_path="reports"):
        import os

        from app.models import Analysis

        ds = make_dataset(owner_id=owner_id)
        analysis = Analysis(
            dataset_id=ds.id,
            question="q",
            status="succeeded",
            chart_image="reports/chart_9999.png",
            owner_id=owner_id,
        )
        db_session.add(analysis)
        db_session.commit()
        db_session.refresh(analysis)

        os.makedirs("reports", exist_ok=True)
        with open("reports/chart_9999.png", "wb") as f:
            f.write(b"\x89PNG\r\n fake")
        return analysis

    def test_chart_requires_auth(self, client):
        resp = client.get("/api/v1/analyses/1/chart")
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_chart_download_by_owner(self, client, auth_token, make_dataset, db_session):
        token, user = auth_token
        analysis = self._make_analysis_with_chart(db_session, make_dataset, owner_id=user.id)
        try:
            resp = client.get(
                f"/api/v1/analyses/{analysis.id}/chart",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200
            assert resp.headers["content-type"] == "image/png"
        finally:
            if os.path.exists("reports/chart_9999.png"):
                os.remove("reports/chart_9999.png")

    def test_chart_denied_for_other_user(self, client, make_user, make_dataset, db_session):
        """用户 B 不能下载用户 A 的图表（IDOR 回归）。"""
        from app.security import create_access_token

        owner = make_user(email="owner@example.com")
        stranger = make_user(email="stranger@example.com")
        analysis = self._make_analysis_with_chart(db_session, make_dataset, owner_id=owner.id)
        try:
            stranger_token = create_access_token(subject=stranger.id)
            resp = client.get(
                f"/api/v1/analyses/{analysis.id}/chart",
                headers={"Authorization": f"Bearer {stranger_token}"},
            )
            assert resp.status_code == status.HTTP_404_NOT_FOUND
        finally:
            if os.path.exists("reports/chart_9999.png"):
                os.remove("reports/chart_9999.png")

    def test_chart_missing_file_404(self, client, auth_token, make_dataset, db_session):
        from app.models import Analysis

        token, user = auth_token
        ds = make_dataset(owner_id=user.id)
        analysis = Analysis(
            dataset_id=ds.id,
            question="q",
            status="succeeded",
            chart_image="reports/chart_88888.png",
            owner_id=user.id,
        )
        db_session.add(analysis)
        db_session.commit()
        resp = client.get(
            f"/api/v1/analyses/{analysis.id}/chart",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND
