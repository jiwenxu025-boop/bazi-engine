"""Runtime SQLite schema and legacy importer tests."""
import json
from concurrent.futures import ThreadPoolExecutor

from bazi_engine.runtime_store import RuntimeStore


def test_legacy_runtime_data_import_is_idempotent(tmp_path):
    activation_file = tmp_path / "activation_codes.json"
    free_usage_file = tmp_path / "free_usage.json"
    feedback_dir = tmp_path / "feedback"
    generation_dir = tmp_path / "generations"
    feedback_dir.mkdir()
    generation_dir.mkdir()

    activation_file.write_text(
        json.dumps({"PAID001": {"剩余": 4, "备注": "test"}}, ensure_ascii=False),
        encoding="utf-8",
    )
    free_usage_file.write_text(
        json.dumps({"hashed-ip": {"date": "2026-07-16", "count": 2}}),
        encoding="utf-8",
    )
    (generation_dir / "fusion_generation_2026-07-16.jsonl").write_text(
        json.dumps({
            "timestamp": "2026-07-16T10:00:00", "generation_id": "a" * 32,
            "generation_type": "fusion", "outcome": "success", "duration_ms": 800,
            "prompt_version": "test-v1", "model": "test-model", "temperature": 0.3,
            "repaired": True,
        }, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (feedback_dir / "fusion_feedback_2026-07-16.jsonl").write_text(
        json.dumps({
            "timestamp": "2026-07-16T10:01:00", "generation_id": "a" * 32,
            "rating": "very", "inaccurate_section": "", "report_hash": "hash",
            "report_length": 700, "prompt_version": "test-v1", "model": "test-model",
            "temperature": 0.3, "repaired": True,
        }, ensure_ascii=False) + "\nnot-json\n",
        encoding="utf-8",
    )
    (feedback_dir / "feedback_2026-07-16.jsonl").write_text(
        json.dumps({
            "timestamp": "2026-07-16T10:02:00", "engine_level": "普通",
            "user_level": "宽裕", "discrepancy": True,
        }, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    store = RuntimeStore(tmp_path / "runtime.sqlite3")
    first = store.import_legacy(
        activation_file=activation_file,
        free_usage_file=free_usage_file,
        feedback_dir=feedback_dir,
        generation_dir=generation_dir,
    )
    second = store.import_legacy(
        activation_file=activation_file,
        free_usage_file=free_usage_file,
        feedback_dir=feedback_dir,
        generation_dir=generation_dir,
    )

    assert first.total_imported() == 5
    assert first.skipped_records == 1
    assert second.total_imported() == 2
    assert store.summary_counts() == {
        "activation_codes": 1,
        "free_usage": 1,
        "fusion_generations": 1,
        "fusion_feedback": 1,
        "family_feedback": 1,
    }


def test_activation_reservations_are_transactional_under_concurrency(tmp_path):
    store = RuntimeStore(tmp_path / "runtime.sqlite3")
    store.seed_activation_codes({"PAID001": {"剩余": 3, "备注": "test"}})

    with ThreadPoolExecutor(max_workers=12) as executor:
        reservations = list(executor.map(lambda _: store.reserve_activation("PAID001"), range(12)))

    successful = [reservation for reservation in reservations if reservation]
    assert len(successful) == 3
    assert store.activation_remaining("PAID001") == 0
    assert store.release_reservation(successful[0].reservation_id) is True
    assert store.release_reservation(successful[0].reservation_id) is False
    assert store.activation_remaining("PAID001") == 1
    assert store.settle_reservation(successful[1].reservation_id) is True
    assert store.activation_remaining("PAID001") == 1


def test_free_reservations_release_on_failure(tmp_path):
    store = RuntimeStore(tmp_path / "runtime.sqlite3")
    first = store.reserve_free("hash", "2026-07-16", 2)
    second = store.reserve_free("hash", "2026-07-16", 2)

    assert first and second
    assert store.reserve_free("hash", "2026-07-16", 2) is None
    assert store.release_reservation(first.reservation_id) is True
    third = store.reserve_free("hash", "2026-07-16", 2)
    assert third is not None
    assert store.settle_reservation(second.reservation_id) is True
    assert store.free_remaining("hash", "2026-07-16", 2) == 0
