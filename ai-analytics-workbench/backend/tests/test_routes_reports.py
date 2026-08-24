"""报告路由测试（P0 新增）。

不测试 PDF 导出（需要 weasyprint + cairo 依赖），重点验证认证与 schema 序列化。
"""

from fastapi import status


class TestReportRoutesAuth:
    def test_list_requires_auth(self, client):
        resp = client.get("/api/v1/reports")
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_requires_auth(self, client, make_dataset, db_session):
        from app.models import Analysis

        ds = make_dataset()
        analysis = Analysis(dataset_id=ds.id, question="q", status="succeeded")
        db_session.add(analysis)
        db_session.commit()
        db_session.refresh(analysis)

        resp = client.post(
            "/api/v1/reports",
            json={
                "analysis_id": analysis.id,
                "title": "测试",
            },
        )
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_download_requires_auth(self, client):
        resp = client.get("/api/v1/reports/1/download")
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


class TestReportRoutesWithAuth:
    def test_list_empty(self, client, auth_headers):
        resp = client.get("/api/v1/reports", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_detail_not_found(self, client, auth_headers):
        resp = client.get("/api/v1/reports/9999", headers=auth_headers)
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_download_not_generated(self, client, auth_headers, make_dataset, db_session):
        from app.models import Analysis, Report

        ds = make_dataset()
        analysis = Analysis(dataset_id=ds.id, question="q", status="succeeded")
        db_session.add(analysis)
        db_session.commit()
        db_session.refresh(analysis)

        report = Report(analysis_id=analysis.id, title="R", content_md="# x", pdf_path="")
        db_session.add(report)
        db_session.commit()
        db_session.refresh(report)

        resp = client.get(f"/api/v1/reports/{report.id}/download", headers=auth_headers)
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_download_invalid_path_rejected(self, client, auth_headers, make_dataset, db_session):
        """pdf_path 不符合正则白名单应被拒绝（防路径遍历）。"""
        from app.models import Analysis, Report

        ds = make_dataset()
        analysis = Analysis(dataset_id=ds.id, question="q", status="succeeded")
        db_session.add(analysis)
        db_session.commit()
        db_session.refresh(analysis)

        # 模拟数据库被污染的 pdf_path
        report = Report(
            analysis_id=analysis.id,
            title="R",
            content_md="# x",
            pdf_path="../../../etc/passwd",
        )
        db_session.add(report)
        db_session.commit()
        db_session.refresh(report)

        resp = client.get(f"/api/v1/reports/{report.id}/download", headers=auth_headers)
        assert resp.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert resp.json()["detail"] == "PDF 路径格式异常"
