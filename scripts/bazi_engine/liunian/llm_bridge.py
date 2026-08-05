"""LLM 推理层桥接 — 并行审查与流式回调。"""
import logging
import threading

from .signal import AnnualScan, EventSignal

logger = logging.getLogger(__name__)

_BATCH_REVIEW_SIZE = 2
_BATCH_REVIEW_WORKERS = 4


def _review_to_signal(llm_evt) -> EventSignal:
    """将逐类 AI 审阅转换为独立展示信号，不进入规则评分。"""
    review_status = getattr(llm_evt, "review_status", "有信号")
    notes = []
    if review_status == "有信号":
        notes.append(f"AI辅助依据：{llm_evt.reasoning}")
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
                                    on_llm_result, on_llm_token=None,
                                    cancel_event: threading.Event | None = None):
    """流式 LLM 审查 — 支持批量合并模式。"""
    if len(llm_tasks) >= 3:
        return _execute_batch_streaming(
            results, llm_tasks, on_llm_result, on_llm_token, cancel_event,
        )

    from concurrent.futures import ThreadPoolExecutor, as_completed

    from ..llm_review import call_llm_review, incomplete_review_results

    def _do_review(idx, year, ctx):
        def _on_token(tok: str):
            if on_llm_token and not _cancelled(cancel_event):
                on_llm_token(year, tok)
        if _cancelled(cancel_event):
            return []
        return _invoke_single_review(
            call_llm_review, ctx, on_token=_on_token, cancel_event=cancel_event,
        )

    with ThreadPoolExecutor(max_workers=min(5, len(llm_tasks))) as executor:
        futures = {}
        for idx, ctx in llm_tasks:
            if _cancelled(cancel_event):
                break
            year = results[idx].year if idx < len(results) else 0
            futures[executor.submit(_do_review, idx, year, ctx)] = (idx, year)

        for future in as_completed(futures):
            if _cancelled(cancel_event):
                break
            idx, year = futures[future]
            try:
                llm_results = future.result(timeout=60)
            except Exception as error:
                logger.warning("LLM review failed year=%s type=%s", year, type(error).__name__)
                llm_results = []
            if not llm_results:
                llm_results = incomplete_review_results(year)
            # AI 审阅与规则信号分开，不影响筛选、强度统计或主摘要。
            for llm_evt in llm_results:
                results[idx].ai_reviews.append(_review_to_signal(llm_evt))
            if on_llm_result and not _cancelled(cancel_event):
                sig_dicts = _signals_to_dicts(llm_results)
                on_llm_result(year, sig_dicts)


def _execute_llm_reviews_parallel(results: list[AnnualScan],
                                   llm_tasks: list[tuple[int, dict]]):
    """并行 LLM 审查 — 支持批量合并模式。"""
    if len(llm_tasks) >= 3:
        return _execute_batch_parallel(results, llm_tasks)

    from concurrent.futures import ThreadPoolExecutor, as_completed

    from ..llm_review import call_llm_review, incomplete_review_results

    with ThreadPoolExecutor(max_workers=min(5, len(llm_tasks))) as executor:
        futures = {}
        for idx, ctx in llm_tasks:
            futures[executor.submit(call_llm_review, ctx)] = idx

        for future in as_completed(futures):
            idx = futures[future]
            year = results[idx].year if idx < len(results) else 0
            try:
                llm_results = future.result(timeout=60)
            except Exception as error:
                logger.warning("LLM review failed year=%s type=%s", year, type(error).__name__)
                llm_results = []
            if not llm_results:
                llm_results = incomplete_review_results(year)
            for llm_evt in llm_results:
                results[idx].ai_reviews.append(_review_to_signal(llm_evt))


def _execute_batch_streaming(
    results, llm_tasks, on_llm_result, on_llm_token, cancel_event=None,
):
    """批量合并模式（流式）：小批并发，每个缺失年份都走单年回退。"""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    chunks = list(_chunk_llm_tasks(llm_tasks))
    contexts_by_index = dict(llm_tasks)
    missing = []
    with ThreadPoolExecutor(max_workers=min(_BATCH_REVIEW_WORKERS, len(chunks))) as executor:
        futures = {
            executor.submit(
                _review_task_chunk, results, chunk, on_llm_token, cancel_event,
            ): chunk
            for chunk in chunks
            if not _cancelled(cancel_event)
        }
        for future in as_completed(futures):
            if _cancelled(cancel_event):
                break
            try:
                resolved = future.result()
            except Exception as error:
                logger.warning("LLM review chunk failed type=%s", type(error).__name__)
                for idx, _ctx in futures[future]:
                    year = results[idx].year if idx < len(results) else 0
                    missing.append((idx, year, contexts_by_index[idx]))
                continue
            for idx, year, yr_results in resolved:
                if not yr_results:
                    missing.append((idx, year, contexts_by_index[idx]))
                    continue
                for llm_evt in yr_results:
                    results[idx].ai_reviews.append(_review_to_signal(llm_evt))
                if on_llm_result and not _cancelled(cancel_event):
                    on_llm_result(year, _signals_to_dicts(yr_results))

    if missing and not _cancelled(cancel_event):
        logger.warning(
            "LLM batch review incomplete years=%s; retrying each year",
            [item[1] for item in missing],
        )
        for idx, year, yr_results in _retry_missing_reviews(
            missing, on_llm_token, cancel_event,
        ):
            if _cancelled(cancel_event):
                break
            for llm_evt in yr_results:
                results[idx].ai_reviews.append(_review_to_signal(llm_evt))
            if on_llm_result:
                on_llm_result(year, _signals_to_dicts(yr_results))


def _execute_batch_parallel(results, llm_tasks):
    """批量合并模式（同步）：小批并发，每个缺失年份都走单年回退。"""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    chunks = list(_chunk_llm_tasks(llm_tasks))
    contexts_by_index = dict(llm_tasks)
    missing = []
    with ThreadPoolExecutor(max_workers=min(_BATCH_REVIEW_WORKERS, len(chunks))) as executor:
        futures = {
            executor.submit(_review_task_chunk, results, chunk): chunk
            for chunk in chunks
        }
        for future in as_completed(futures):
            try:
                resolved = future.result()
            except Exception as error:
                logger.warning("LLM review chunk failed type=%s", type(error).__name__)
                for idx, _ctx in futures[future]:
                    year = results[idx].year if idx < len(results) else 0
                    missing.append((idx, year, contexts_by_index[idx]))
                continue
            for idx, _year, yr_results in resolved:
                if not yr_results:
                    missing.append((idx, _year, contexts_by_index[idx]))
                    continue
                for llm_evt in yr_results:
                    results[idx].ai_reviews.append(_review_to_signal(llm_evt))

    if missing:
        logger.warning(
            "LLM batch review incomplete years=%s; retrying each year",
            [item[1] for item in missing],
        )
        for idx, _year, yr_results in _retry_missing_reviews(missing):
            for llm_evt in yr_results:
                results[idx].ai_reviews.append(_review_to_signal(llm_evt))


def _chunk_llm_tasks(llm_tasks):
    for offset in range(0, len(llm_tasks), _BATCH_REVIEW_SIZE):
        yield llm_tasks[offset:offset + _BATCH_REVIEW_SIZE]


def _review_task_chunk(results, task_chunk, on_llm_token=None, cancel_event=None):
    """审阅一个小批次；缺失结果由上层逐年补做。"""
    from ..llm_review import call_llm_batch_review, call_llm_review

    if _cancelled(cancel_event):
        return []
    if len(task_chunk) == 1:
        idx, ctx = task_chunk[0]
        year = results[idx].year if idx < len(results) else 0
        return [(
            idx,
            year,
            _call_single_review(
                call_llm_review, ctx, year, on_llm_token, cancel_event,
            ),
        )]

    batch_results = _invoke_batch_review(
        call_llm_batch_review,
        [ctx for _, ctx in task_chunk],
        cancel_event=cancel_event,
    )
    resolved = []
    for position, (idx, _ctx) in enumerate(task_chunk):
        year = results[idx].year if idx < len(results) else 0
        yr_results = batch_results[position] if position < len(batch_results) else []
        resolved.append((idx, year, yr_results))
    return resolved


def _retry_missing_reviews(missing, on_llm_token=None, cancel_event=None):
    """并发执行逐年回退；仍无返回时生成明确的未完成矩阵。"""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    from ..llm_review import call_llm_review, incomplete_review_results

    if not missing or _cancelled(cancel_event):
        return []

    def retry(item):
        idx, year, ctx = item
        reviews = _call_single_review(
            call_llm_review, ctx, year, on_llm_token, cancel_event,
        )
        if not reviews and not _cancelled(cancel_event):
            reviews = incomplete_review_results(year)
        return idx, year, reviews

    resolved = []
    with ThreadPoolExecutor(max_workers=min(_BATCH_REVIEW_WORKERS, len(missing))) as executor:
        futures = {
            executor.submit(retry, item): item
            for item in missing
            if not _cancelled(cancel_event)
        }
        for future in as_completed(futures):
            if _cancelled(cancel_event):
                break
            idx, year, _ctx = futures[future]
            try:
                resolved.append(future.result())
            except Exception as error:
                logger.warning(
                    "LLM single-year fallback failed year=%s type=%s",
                    year,
                    type(error).__name__,
                )
                resolved.append((idx, year, incomplete_review_results(year)))
    return resolved


def _call_single_review(call_llm_review, ctx, year, on_llm_token, cancel_event):
    if _cancelled(cancel_event):
        return []
    if on_llm_token is None:
        return _invoke_single_review(
            call_llm_review, ctx, cancel_event=cancel_event,
        )

    def on_token(token):
        if not _cancelled(cancel_event):
            on_llm_token(year, token)

    return _invoke_single_review(
        call_llm_review, ctx, on_token=on_token, cancel_event=cancel_event,
    )


def _invoke_single_review(call_llm_review, ctx, on_token=None, cancel_event=None):
    kwargs = {}
    if on_token is not None:
        kwargs["on_token"] = on_token
    if cancel_event is not None:
        kwargs["cancel_event"] = cancel_event
    return call_llm_review(ctx, **kwargs)


def _invoke_batch_review(call_llm_batch_review, ctxs, cancel_event=None):
    kwargs = {"on_token": None}
    if cancel_event is not None:
        kwargs["cancel_event"] = cancel_event
    return call_llm_batch_review(ctxs, **kwargs)


def _cancelled(cancel_event) -> bool:
    return bool(cancel_event and cancel_event.is_set())


def _signals_to_dicts(llm_results) -> list[dict]:
    """Use the same EventSignal contract for streaming and synchronous output."""
    signals = [_review_to_signal(llm_evt) for llm_evt in llm_results]
    return [signal.to_dict() for signal in signals]
