"""Application worker pool tests."""


def test_blocking_executor_is_shared_and_recreated_after_shutdown(monkeypatch):
    import bazi_engine._runtime as runtime

    runtime.close_blocking_executor()
    monkeypatch.setenv("BAZI_MAX_BLOCKING_WORKERS", "2")

    first = runtime.get_blocking_executor()
    second = runtime.get_blocking_executor()

    assert first is second
    assert first._max_workers == 2

    runtime.close_blocking_executor()
    recreated = runtime.get_blocking_executor()
    assert recreated is not first
    runtime.close_blocking_executor()
