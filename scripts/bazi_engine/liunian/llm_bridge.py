"""LLM 推理层桥接 — 并行审查与流式回调。

v0.15.1: 当 ≥3 个年份需要 LLM 审查时，使用 call_llm_batch_review 批量合并调用。
"""
import logging

from .signal import AnnualScan, EventSignal

logger = logging.getLogger(__name__)


def _review_to_signal(llm_evt) -> EventSignal:
    """将逐类 AI 审阅转换为独立展示信号，不进入规则评分。"""
    review_status = getattr(llm_evt, "review_status", "有信号")
    notes = []
    if review_status == "有信号":
        notes.append(
            f"🤖 LLM综合推理 (置信度{llm_evt.confidence:.0%}): {llm_evt.reasoning}"
        )
    elif review_status == "未完成":
        notes.append("本类别未返回完整审阅结果")
    return EventSignal(
        category=llm_evt.category,
        direction=llm_evt.direction,
        strength=llm_evt.strength,
        prediction=llm_evt.prediction,
        triggers=llm_evt.triggers,
        notes=notes,
        source="llm",
        review_status=review_status,
    )


def _execute_llm_reviews_streaming(results: list[AnnualScan],
                                    llm_tasks: list[tuple[int, dict]],
                                    on_llm_result, on_llm_token=None):
    """流式 LLM 审查 — 支持批量合并模式。"""
    if len(llm_tasks) >= 3:
        return _execute_batch_streaming(results, llm_tasks, on_llm_result, on_llm_token)

    from concurrent.futures import ThreadPoolExecutor, as_completed

    from ..llm_review import call_llm_review

    def _do_review(idx, year, ctx):
        def _on_token(tok: str):
            if on_llm_token:
                on_llm_token(year, tok)
        return call_llm_review(ctx, on_token=_on_token)

    with ThreadPoolExecutor(max_workers=min(5, len(llm_tasks))) as executor:
        futures = {}
        for idx, ctx in llm_tasks:
            year = results[idx].year if idx < len(results) else 0
            futures[executor.submit(_do_review, idx, year, ctx)] = (idx, year)

        for future in as_completed(futures):
            idx, year = futures[future]
            try:
                llm_results = future.result(timeout=60)
                # AI 审阅与规则信号分开，不影响筛选、强度统计或主摘要。
                for llm_evt in llm_results:
                    results[idx].ai_reviews.append(_review_to_signal(llm_evt))
                if on_llm_result:
                    sig_dicts = _signals_to_dicts(llm_results)
                    on_llm_result(year, sig_dicts)
            except Exception as error:
                logger.warning("LLM review failed year=%s type=%s", year, type(error).__name__)


def _execute_llm_reviews_parallel(results: list[AnnualScan],
                                   llm_tasks: list[tuple[int, dict]]):
    """并行 LLM 审查 — 支持批量合并模式。"""
    if len(llm_tasks) >= 3:
        return _execute_batch_parallel(results, llm_tasks)

    from concurrent.futures import ThreadPoolExecutor, as_completed

    from ..llm_review import call_llm_review

    with ThreadPoolExecutor(max_workers=min(5, len(llm_tasks))) as executor:
        futures = {}
        for idx, ctx in llm_tasks:
            futures[executor.submit(call_llm_review, ctx)] = idx

        for future in as_completed(futures):
            idx = futures[future]
            try:
                llm_results = future.result(timeout=60)
                for llm_evt in llm_results:
                    results[idx].ai_reviews.append(_review_to_signal(llm_evt))
            except Exception as error:
                year = results[idx].year if idx < len(results) else "?"
                logger.warning("LLM review failed year=%s type=%s", year, type(error).__name__)


def _execute_batch_streaming(results, llm_tasks, on_llm_result, on_llm_token):
    """批量合并模式（流式）：一次 API 调用审查多个年份。"""
    from ..llm_review import call_llm_batch_review

    ctxs = [ctx for _, ctx in llm_tasks]
    year_map = [idx for idx, _ in llm_tasks]

    # 批量模式 token 流无法分配具体年份，不传 on_token（结果仍会通过 llm_result 回调送达）
    batch_results = call_llm_batch_review(ctxs, on_token=None)
    for i, yr_results in enumerate(batch_results):
        idx = year_map[i]
        for llm_evt in yr_results:
            results[idx].ai_reviews.append(_review_to_signal(llm_evt))
        if yr_results and on_llm_result:
            year = results[idx].year if idx < len(results) else 0
            sig_dicts = _signals_to_dicts(yr_results)
            on_llm_result(year, sig_dicts)


def _execute_batch_parallel(results, llm_tasks):
    """批量合并模式（同步）：一次 API 调用审查多个年份，结果直接合并。"""
    from ..llm_review import call_llm_batch_review

    ctxs = [ctx for _, ctx in llm_tasks]
    year_map = [idx for idx, _ in llm_tasks]

    batch_results = call_llm_batch_review(ctxs)
    for i, yr_results in enumerate(batch_results):
        idx = year_map[i]
        for llm_evt in yr_results:
            results[idx].ai_reviews.append(_review_to_signal(llm_evt))


def _signals_to_dicts(llm_results) -> list[dict]:
    """LLMReviewResult → dict 列表（供流式回调使用）"""
    signals = [_review_to_signal(llm_evt) for llm_evt in llm_results]
    return [{
        "category": s.category, "direction": s.direction,
        "strength": s.strength, "prediction": s.prediction,
        "triggers": s.triggers, "notes": s.notes, "source": s.source,
        "review_status": s.review_status,
    } for s in signals]
