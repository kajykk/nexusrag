"""分析任务路由测试（P0 新增）。"""

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
