"""Pydantic 模型测试：ColumnInfo、DatasetCreate、AnalysisCreate、WSProgressMessage。"""

import pytest
from pydantic import ValidationError

from app.schemas.analysis import AnalysisCreate, WSProgressMessage
from app.schemas.dataset import ColumnInfo, DatasetCreate


class TestColumnInfo:
    def test_column_info(self):
        """测试 ColumnInfo 创建。"""
        col = ColumnInfo(name="age", dtype="int64", sample=[1, 2, 3])
        assert col.name == "age"
        assert col.dtype == "int64"
        assert col.sample == [1, 2, 3]
        assert col.null_count == 0
        assert col.unique_count == 0

    def test_column_info_defaults(self):
        """测试 ColumnInfo 默认值。"""
        col = ColumnInfo(name="x", dtype="float64")
        assert col.sample == []
        assert col.null_count == 0
        assert col.unique_count == 0

    def test_column_info_requires_name(self):
        """name 为必填项。"""
        with pytest.raises(ValidationError):
            ColumnInfo(dtype="int64")  # type: ignore[call-arg]


class TestDatasetCreate:
    def test_dataset_create_validation(self):
        """测试 DatasetCreate 校验（min_length）。"""
        ds = DatasetCreate(name="销售数据", description="月度汇总")
        assert ds.name == "销售数据"
        assert ds.description == "月度汇总"

    def test_dataset_create_empty_name_rejected(self):
        """name 为空字符串应校验失败。"""
        with pytest.raises(ValidationError):
            DatasetCreate(name="")

    def test_dataset_create_default_description(self):
        """description 默认为空字符串。"""
        ds = DatasetCreate(name="x")
        assert ds.description == ""


class TestAnalysisCreate:
    def test_analysis_create(self):
        """测试 AnalysisCreate 创建。"""
        analysis = AnalysisCreate(dataset_id=1, question="统计销售额")
        assert analysis.dataset_id == 1
        assert analysis.question == "统计销售额"

    def test_analysis_create_empty_question_rejected(self):
        """question 为空字符串应校验失败（min_length=1）。"""
        with pytest.raises(ValidationError):
            AnalysisCreate(dataset_id=1, question="")


class TestWSProgressMessage:
    def test_ws_progress_message(self):
        """测试 WSProgressMessage 校验（progress 0-100）。"""
        msg = WSProgressMessage(analysis_id=1, stage="running", progress=50, message="处理中")
        assert msg.analysis_id == 1
        assert msg.stage == "running"
        assert msg.progress == 50
        assert msg.message == "处理中"

    def test_ws_progress_message_progress_zero(self):
        """progress=0 应通过。"""
        msg = WSProgressMessage(analysis_id=1, stage="queued", progress=0)
        assert msg.progress == 0

    def test_ws_progress_message_progress_hundred(self):
        """progress=100 应通过。"""
        msg = WSProgressMessage(analysis_id=1, stage="succeeded", progress=100)
        assert msg.progress == 100

    def test_ws_progress_message_progress_negative_rejected(self):
        """progress<0 应校验失败。"""
        with pytest.raises(ValidationError):
            WSProgressMessage(analysis_id=1, stage="running", progress=-1)

    def test_ws_progress_message_progress_over_hundred_rejected(self):
        """progress>100 应校验失败。"""
        with pytest.raises(ValidationError):
            WSProgressMessage(analysis_id=1, stage="running", progress=101)
