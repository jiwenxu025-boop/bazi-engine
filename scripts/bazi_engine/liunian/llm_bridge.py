"""LLM 推理层桥接 — 并行审查与流式回调。

v0.15.1: 当 ≥3 个年份需要 LLM 审查时，使用 call_llm_batch_review 批量合并调用。
"""
import sys

from .signal import AnnualScan, EventSignal


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
                # 直接写入 scan.events（v0.16: 不依赖回调，确保前端初始渲染可见）
                for llm_evt in llm_results:
                    results[idx].events.append(EventSignal(
                        category=llm_evt.category, direction=llm_evt.direction,
                        strength=llm_evt.strength, prediction=llm_evt.prediction,
                        triggers=llm_evt.triggers,
                        notes=[f"🤖 LLM综合推理 (置信度{llm_evt.confidence:.0%}): {llm_evt.reasoning}"],
                        source="llm",
                    ))
                if on_llm_result:
                    sig_dicts = _signals_to_dicts(llm_results)
                    on_llm_result(year, sig_dicts)
            except Exception as e:
                print(f"[llm_review] 年份{year} LLM调用/回调失败: {e}", file=sys.stderr)


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
                    results[idx].events.append(EventSignal(
                        category=llm_evt.category,
                        direction=llm_evt.direction,
                        strength=llm_evt.strength,
                        prediction=llm_evt.prediction,
                        triggers=llm_evt.triggers,
                        notes=[f"🤖 LLM综合推理 (置信度{llm_evt.confidence:.0%}): {llm_evt.reasoning}"],
                        source="llm",
                    ))
            except Exception as e:
                print(f"[llm_review] 年份{results[idx].year if idx < len(results) else '?'} LLM并行调用失败: {e}", file=sys.stderr)


def _execute_batch_streaming(results, llm_tasks, on_llm_result, on_llm_token):
    """批量合并模式（流式）：一次 API 调用审查多个年份。"""
    from ..llm_review import call_llm_batch_review

    ctxs = [ctx for _, ctx in llm_tasks]
    year_map = [idx for idx, _ in llm_tasks]

    # 批量模式 token 流无法分配具体年份，不传 on_token（结果仍会通过 llm_result 回调送达）
    batch_results = call_llm_batch_review(ctxs, on_token=None)
    for i, yr_results in enumerate(batch_results):
        idx = year_map[i]
        # 直接写入 scan.events（v0.16: 不依赖回调，确保前端初始渲染可见）
        for llm_evt in yr_results:
            results[idx].events.append(EventSignal(
                category=llm_evt.category,
                direction=llm_evt.direction,
                strength=llm_evt.strength,
                prediction=llm_evt.prediction,
                triggers=llm_evt.triggers,
                notes=[f"🤖 LLM综合推理 (置信度{llm_evt.confidence:.0%}): {llm_evt.reasoning}"],
                source="llm",
            ))
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
            results[idx].events.append(EventSignal(
                category=llm_evt.category,
                direction=llm_evt.direction,
                strength=llm_evt.strength,
                prediction=llm_evt.prediction,
                triggers=llm_evt.triggers,
                notes=[f"🤖 LLM综合推理 (置信度{llm_evt.confidence:.0%}): {llm_evt.reasoning}"],
                source="llm",
            ))


def _signals_to_dicts(llm_results) -> list[dict]:
    """LLMReviewResult → dict 列表（供流式回调使用）"""
    signals = []
    for llm_evt in llm_results:
        sig = EventSignal(
            category=llm_evt.category,
            direction=llm_evt.direction,
            strength=llm_evt.strength,
            prediction=llm_evt.prediction,
            triggers=llm_evt.triggers,
            notes=[f"🤖 LLM综合推理 (置信度{llm_evt.confidence:.0%}): {llm_evt.reasoning}"],
            source="llm",
        )
        signals.append(sig)
    return [{
        "category": s.category, "direction": s.direction,
        "strength": s.strength, "prediction": s.prediction,
        "triggers": s.triggers, "notes": s.notes, "source": s.source,
    } for s in signals]
