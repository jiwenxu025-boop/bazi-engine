"""LLM 推理层桥接 — 并行审查与流式回调。"""
from .signal import AnnualScan, EventSignal


def _execute_llm_reviews_streaming(results: list[AnnualScan],
                                    llm_tasks: list[tuple[int, dict]],
                                    on_llm_result, on_llm_token=None):
    """v0.11.2: 并行执行LLM审查，逐token回调+完成回调（供SSE逐字渲染）。"""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    from .llm_review import call_llm_review

    def _do_review(idx, year, ctx):
        """单年审查，token级回调"""
        def _on_token(tok: str):
            if on_llm_token:
                on_llm_token(year, tok)
        llm_results = call_llm_review(ctx, on_token=_on_token)
        return idx, year, llm_results

    with ThreadPoolExecutor(max_workers=min(5, len(llm_tasks))) as executor:
        futures = {}
        for idx, ctx in llm_tasks:
            year = results[idx].year if idx < len(results) else 0
            future = executor.submit(_do_review, idx, year, ctx)
            futures[future] = (idx, year)

        for future in as_completed(futures):
            idx, year = futures[future]
            try:
                ridx, ryear, llm_results = future.result(timeout=60)
                signals = []
                for llm_evt in llm_results:
                    sig = EventSignal(
                        category=llm_evt.category,
                        direction=llm_evt.direction,
                        strength=llm_evt.strength,
                        prediction=llm_evt.prediction,
                        triggers=llm_evt.triggers,
                        notes=[f"🤖 LLM综合推理 (置信度{llm_evt.confidence:.0%}): {llm_evt.reasoning}"],
                    )
                    signals.append(sig)
                sig_dicts = [{ "category": s.category, "direction": s.direction,
                              "strength": s.strength, "prediction": s.prediction,
                              "triggers": s.triggers, "notes": s.notes }
                            for s in signals]
                on_llm_result(ryear, sig_dicts)
            except Exception:
                pass

def _execute_llm_reviews_parallel(results: list[AnnualScan],
                                   llm_tasks: list[tuple[int, dict]]):
    """v0.11.1: 并行执行所有收集到的LLM审查任务，结果合并回results。

    使用 ThreadPoolExecutor 最多5个并发，将多年审查从串行N×3s压缩到~3s。
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    from .llm_review import call_llm_review

    with ThreadPoolExecutor(max_workers=min(5, len(llm_tasks))) as executor:
        futures = {}
        for idx, ctx in llm_tasks:
            future = executor.submit(call_llm_review, ctx)
            futures[future] = idx

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
                    ))
            except Exception:
                pass  # 单个LLM审查失败不影响整体

