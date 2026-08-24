"""DataFrame 与 schema 工具：类型推断、JSON 序列化。"""

import json

import numpy as np
import pandas as pd


def infer_dataframe_schema(df: pd.DataFrame, sample_size: int = 3) -> list[dict]:
    """提取 DataFrame 的列信息（名称、类型、样例、空值数、唯一值数）。"""
    columns = []
    for col in df.columns:
        col_str = str(col)
        dtype = str(df[col].dtype)
        sample = _to_jsonable(df[col].head(sample_size).tolist())
        null_count = int(df[col].isna().sum())
        unique_count = int(df[col].nunique(dropna=True))
        columns.append(
            {
                "name": col_str,
                "dtype": dtype,
                "sample": sample,
                "null_count": null_count,
                "unique_count": unique_count,
            }
        )
    return columns


def to_jsonable(obj):
    """将对象转为 JSON 可序列化形式（公开别名，供 services 调用）。"""
    return _to_jsonable(obj)


def _to_jsonable(obj):
    """将对象转为 JSON 可序列化形式（内部实现）。"""
    if obj is None:
        return None
    if isinstance(obj, pd.DataFrame):
        return json.loads(obj.to_json(orient="records", force_ascii=False, date_format="iso"))
    if isinstance(obj, pd.Series):
        return json.loads(obj.to_json(orient="records", force_ascii=False))
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, dict):
        return {str(k): _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, list | tuple):
        return [_to_jsonable(v) for v in obj]
    if isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    return obj
