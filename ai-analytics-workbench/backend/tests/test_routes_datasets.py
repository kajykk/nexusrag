"""数据集路由测试（P0 新增）。

注意：upload 端点依赖真实 PG 表创建，测试中使用 mock 检验认证行为；
其他端点用内存 SQLite 完整覆盖。
"""

import io

import pytest
from fastapi import status


@pytest.fixture
def csv_file_bytes():
    return b"name,age,score\nAlice,25,85.5\nBob,30,92.3\n"


class TestDatasetRoutesAuth:
    """验证所有 datasets 端点要求认证。"""

    def test_list_requires_auth(self, client):
        resp = client.get("/api/v1/datasets")
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_detail_requires_auth(self, client, make_dataset):
        ds = make_dataset()
        resp = client.get(f"/api/v1/datasets/{ds.id}")
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_delete_requires_auth(self, client, make_dataset):
        ds = make_dataset()
        resp = client.delete(f"/api/v1/datasets/{ds.id}")
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_upload_requires_auth(self, client, csv_file_bytes):
        resp = client.post(
            "/api/v1/datasets/upload",
            files={"file": ("test.csv", io.BytesIO(csv_file_bytes), "text/csv")},
            data={"name": "测试"},
        )
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


class TestDatasetRoutesWithAuth:
    """认证后访问数据集端点。"""

    def test_list_empty(self, client, auth_headers):
        resp = client.get("/api/v1/datasets", headers=auth_headers)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json() == []

    def test_list_with_data(self, client, auth_headers, make_dataset):
        make_dataset(name="数据集 A")
        make_dataset(name="数据集 B")
        resp = client.get("/api/v1/datasets", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

    def test_detail_found(self, client, auth_headers, make_dataset):
        ds = make_dataset(name="详情测试", row_count=42)
        resp = client.get(f"/api/v1/datasets/{ds.id}", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == ds.id
        assert body["name"] == "详情测试"
        assert body["row_count"] == 42

    def test_detail_not_found(self, client, auth_headers):
        resp = client.get("/api/v1/datasets/9999", headers=auth_headers)
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_detail_uses_pydantic_schema(self, client, auth_headers, make_dataset):
        """验证返回字段与 DatasetOut schema 一致。"""
        ds = make_dataset()
        resp = client.get(f"/api/v1/datasets/{ds.id}", headers=auth_headers)
        body = resp.json()
        expected_fields = {
            "id",
            "name",
            "original_filename",
            "file_type",
            "row_count",
            "column_count",
            "created_at",
            "columns_schema",
            "preview",
            "description",
        }
        assert expected_fields.issubset(set(body.keys()))

    def test_delete_not_found(self, client, auth_headers):
        resp = client.delete("/api/v1/datasets/9999", headers=auth_headers)
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_invalid_token_rejected(self, client):
        """无效 token 必须返回 401。"""
        resp = client.get(
            "/api/v1/datasets",
            headers={"Authorization": "Bearer fake.jwt.token"},
        )
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED
