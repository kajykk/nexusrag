"""分析服务：LLM 调用、代码执行、图表渲染、进度推送。"""

import json

from sqlalchemy.orm import Session

from app.config import settings
from app.db.session import SessionLocal
from app.llm import SYSTEM_PROMPT, build_user_prompt, chat_completion, parse_json_response
from app.logging_config import get_logger
from app.models import Analysis, Dataset, User
from app.schemas.analysis import AnalysisResult
from app.services.dataset_service import get_dataset
from app.services.ownership import apply_visible, is_visible
from app.utils import load_table_to_dataframe, safe_execute_pandas, to_jsonable
from app.utils.sandbox import ERROR_TIMEOUT
from app.utils.timeutil import utcnow
from app.visualization import render_chart
from app.ws.pubsub import publish_progress

logger = get_logger(__name__)


def create_analysis(db: Session, dataset_id: int, question: str, owner: User | None = None) -> Analysis:
    """创建分析任务记录（状态 pending）。

    owner 提供时校验数据集归属（无权访问视为数据集不存在），并把归属传递给新任务。
    """
    dataset = get_dataset(db, dataset_id, owner)
    if not dataset:
        raise ValueError(f"数据集 {dataset_id} 不存在")
    analysis = Analysis(
        dataset_id=dataset_id,
        question=question,
        status="pending",
        owner_id=owner.id if owner else None,
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    return analysis


def get_analysis(db: Session, analysis_id: int, user: User | None = None) -> Analysis | None:
    """获取分析任务；user 提供时校验归属，不可见视为不存在。"""
    analysis = db.get(Analysis, analysis_id)
    if analysis is None:
        return None
    if not is_visible(analysis, user):
        return None
    return analysis


def list_analyses(
    db: Session,
    dataset_id: int | None = None,
    user: User | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[Analysis]:
    """列出可见分析任务（支持分页，默认 100 条）。"""
    if limit < 1 or limit > 500:
        raise ValueError("limit 应在 1..500 之间")
    if offset < 0:
        raise ValueError("offset 不能为负")
    q = apply_visible(db.query(Analysis), Analysis, user)
    if dataset_id is not None:  # 不用真值判断：dataset_id=0 时静默不过滤是防御性瑕疵
        q = q.filter(Analysis.dataset_id == dataset_id)
    return q.order_by(Analysis.created_at.desc()).limit(limit).offset(offset).all()


def execute_analysis(analysis_id: int) -> dict:
    """执行分析任务（在 Celery worker 中同步运行）。

    流程：
      1. 标记 running
      2. 加载数据集 schema 与 DataFrame
      3. 调用 LLM 生成代码
      4. 沙箱执行代码
      5. 渲染图表
      6. 标记 succeeded / failed，推送进度
    """
    db = SessionLocal()
    try:
        analysis = db.get(Analysis, analysis_id)
        if not analysis:
            logger.warning("analysis.not_found", extra={"analysis_id": analysis_id})
            return {"error": "分析任务不存在"}

        # 幂等保护：acks_late + worker 崩溃重投时，终态任务不重复执行
        if analysis.status in ("succeeded", "failed"):
            logger.info(
                "analysis.skip_terminal_state",
                extra={"analysis_id": analysis_id, "status": analysis.status},
            )
            return {"status": analysis.status, "analysis_id": analysis_id, "skipped": True}

        dataset = db.get(Dataset, analysis.dataset_id)
        if not dataset:
            logger.warning(
                "analysis.dataset_missing", extra={"analysis_id": analysis_id, "dataset_id": analysis.dataset_id}
            )
            analysis.status = "failed"
            analysis.error_message = "数据集不存在"
            db.commit()
            return {"error": "数据集不存在"}

        logger.info(
            "analysis.start",
            extra={"analysis_id": analysis_id, "dataset_id": analysis.dataset_id, "question": analysis.question[:80]},
        )
        publish_progress(analysis_id, "running", 10, "开始分析")
        analysis.status = "running"
        db.commit()

        # 1. 加载数据
        publish_progress(analysis_id, "running", 25, "加载数据集")
        df = load_table_to_dataframe(dataset.table_name)
        columns_schema = json.loads(dataset.columns_schema or "[]")
        # 必须经 to_jsonable 清洗：datetime64 列的 pd.Timestamp 无法被
        # json.dumps 序列化，会让所有含日期列的数据集分析必然失败
        preview = to_jsonable(df.head(5).to_dict(orient="records"))

        # 2. 调用 LLM
        publish_progress(analysis_id, "running", 45, "调用 LLM 生成分析代码")
        user_prompt = build_user_prompt(analysis.question, columns_schema, preview)
        raw = chat_completion(SYSTEM_PROMPT, user_prompt)
        llm_result = parse_json_response(raw)
        # schema 校验：LLM 输出缺失/类型错误时显式失败，而非静默产出空代码
        parsed = AnalysisResult.model_validate(llm_result)
        code = parsed.code
        chart_type = parsed.chart_type
        chart_config = parsed.chart_config
        summary = parsed.summary

        analysis.generated_code = code
        analysis.code_type = parsed.code_type

        # 3. 执行代码（进程级隔离沙箱，见 app/utils/sandbox.py）
        publish_progress(analysis_id, "running", 70, "执行分析代码")
        reports_dir = settings.reports_abs_dir
        exec_result = safe_execute_pandas(code, df, artifacts_dir=reports_dir)
        if exec_result["error"]:
            timed_out = exec_result.get("error_type") == ERROR_TIMEOUT
            logger.warning(
                "analysis.code_failed",
                extra={"analysis_id": analysis_id, "timeout": timed_out, "error": exec_result["error"][:200]},
            )
            analysis.status = "failed"
            analysis.error_message = exec_result["error"]
            analysis.completed_at = utcnow()
            db.commit()
            message = "代码执行超时，已强制终止" if timed_out else "代码执行失败"
            publish_progress(analysis_id, "failed", 100, message, {"error": exec_result["error"]})
            return {"error": exec_result["error"]}

        result_data = exec_result["result"]
        analysis.result_data = json.dumps({"result": result_data, "summary": summary}, ensure_ascii=False)
        analysis.chart_config = json.dumps(chart_config, ensure_ascii=False)

        # 4. 渲染图表（沙箱内若已产出 PNG 则直接采用，否则走服务端渲染）
        publish_progress(analysis_id, "running", 85, "渲染图表")
        chart_path = exec_result.get("chart_png_path") or render_chart(result_data, chart_type, analysis_id, chart_config)
        analysis.chart_image = chart_path

        # 5. 完成
        analysis.status = "succeeded"
        analysis.completed_at = utcnow()
        db.commit()
        logger.info("analysis.succeeded", extra={"analysis_id": analysis_id, "chart_path": chart_path})

        publish_progress(
            analysis_id,
            "succeeded",
            100,
            "分析完成",
            {
                "result_data": json.loads(analysis.result_data),
                "chart_config": chart_config,
                "chart_image": chart_path,
                "generated_code": code,
            },
        )
        return {"status": "succeeded", "analysis_id": analysis_id}
    except Exception as exc:  # noqa: BLE001
        logger.exception("analysis.failed", extra={"analysis_id": analysis_id})
        db.rollback()
        analysis = db.get(Analysis, analysis_id)
        if analysis:
            analysis.status = "failed"
            analysis.error_message = str(exc)
            analysis.completed_at = utcnow()
            db.commit()
        publish_progress(analysis_id, "failed", 100, f"分析失败: {exc}", {"error": str(exc)})
        return {"error": str(exc)}
    finally:
        db.close()
