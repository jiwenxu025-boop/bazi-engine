"""SQLite runtime-data store and idempotent legacy JSON/JSONL importer."""
import hashlib
import json
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path


@dataclass(frozen=True)
class MigrationReport:
    activation_codes: int = 0
    free_usage: int = 0
    fusion_generations: int = 0
    fusion_feedback: int = 0
    family_feedback: int = 0
    skipped_records: int = 0

    def total_imported(self) -> int:
        return sum((
            self.activation_codes,
            self.free_usage,
            self.fusion_generations,
            self.fusion_feedback,
            self.family_feedback,
        ))


@dataclass(frozen=True)
class QuotaReservation:
    reservation_id: str
    remaining: int


class RuntimeStore:
    """Owns durable runtime state without touching calibration data."""

    def __init__(self, path: Path):
        self.path = path

    def connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=5.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute("PRAGMA synchronous = NORMAL")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS schema_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS activation_codes (
                    code TEXT PRIMARY KEY,
                    remaining INTEGER NOT NULL CHECK (remaining >= 0),
                    note TEXT NOT NULL DEFAULT '',
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS free_usage (
                    client_hash TEXT PRIMARY KEY,
                    usage_date TEXT NOT NULL,
                    count INTEGER NOT NULL CHECK (count >= 0)
                );
                CREATE TABLE IF NOT EXISTS quota_reservations (
                    reservation_id TEXT PRIMARY KEY,
                    kind TEXT NOT NULL CHECK (kind IN ('activation', 'free')),
                    code TEXT,
                    client_hash TEXT,
                    usage_date TEXT,
                    state TEXT NOT NULL CHECK (state IN ('reserved', 'settled', 'released')),
                    expires_at TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    CHECK (
                        (kind = 'activation' AND code IS NOT NULL AND client_hash IS NULL)
                        OR (kind = 'free' AND client_hash IS NOT NULL AND code IS NULL)
                    )
                );
                CREATE INDEX IF NOT EXISTS quota_reservations_expiry
                    ON quota_reservations(state, expires_at);
                CREATE TABLE IF NOT EXISTS fusion_generations (
                    generation_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    generation_type TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    duration_ms INTEGER,
                    prompt_version TEXT,
                    model TEXT,
                    temperature REAL,
                    repaired INTEGER NOT NULL DEFAULT 0,
                    error_class TEXT,
                    synthetic INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS fusion_feedback (
                    legacy_hash TEXT PRIMARY KEY,
                    generation_id TEXT,
                    timestamp TEXT NOT NULL,
                    rating TEXT NOT NULL,
                    inaccurate_section TEXT NOT NULL DEFAULT '',
                    report_hash TEXT,
                    report_length INTEGER,
                    prompt_version TEXT,
                    model TEXT,
                    temperature REAL,
                    repaired INTEGER NOT NULL DEFAULT 0,
                    synthetic INTEGER NOT NULL DEFAULT 0
                );
                CREATE UNIQUE INDEX IF NOT EXISTS fusion_feedback_generation_id
                    ON fusion_feedback(generation_id) WHERE generation_id IS NOT NULL;
                CREATE TABLE IF NOT EXISTS family_feedback (
                    legacy_hash TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    engine_level TEXT NOT NULL DEFAULT '',
                    user_level TEXT NOT NULL,
                    discrepancy INTEGER NOT NULL DEFAULT 0,
                    discrepancy_detail TEXT,
                    synthetic INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS legacy_imports (
                    content_hash TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                INSERT OR IGNORE INTO schema_meta(key, value) VALUES ('version', '1');
                """
            )

    def seed_activation_codes(self, codes: dict) -> int:
        """Insert environment-provided codes once without resetting consumed balances."""
        self.initialize()
        inserted = 0
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            for code, entry in codes.items():
                if not isinstance(entry, dict):
                    continue
                remaining = entry.get("剩余", 0)
                if not isinstance(remaining, int) or remaining < 0:
                    continue
                result = connection.execute(
                    "INSERT OR IGNORE INTO activation_codes(code, remaining, note) VALUES (?, ?, ?)",
                    (str(code).upper(), remaining, str(entry.get("备注", ""))),
                )
                inserted += result.rowcount
        return inserted

    def activation_remaining(self, code: str) -> int | None:
        self.initialize()
        with self.connect() as connection:
            row = connection.execute(
                "SELECT remaining FROM activation_codes WHERE code = ?", (code.strip().upper(),)
            ).fetchone()
        return int(row["remaining"]) if row else None

    def activation_codes(self) -> dict[str, dict]:
        self.initialize()
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT code, remaining, note FROM activation_codes ORDER BY code"
            ).fetchall()
        return {
            row["code"]: {"剩余": int(row["remaining"]), "备注": row["note"]}
            for row in rows
        }

    def free_remaining(self, client_hash: str, usage_date: str, limit: int) -> int:
        self.initialize()
        with self.connect() as connection:
            row = connection.execute(
                "SELECT usage_date, count FROM free_usage WHERE client_hash = ?", (client_hash,)
            ).fetchone()
        used = int(row["count"]) if row and row["usage_date"] == usage_date else 0
        return max(0, limit - used)

    def reserve_activation(self, code: str, *, expiry_seconds: int = 300) -> QuotaReservation | None:
        self.initialize()
        normalized_code = code.strip().upper()
        now = self._now()
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._release_expired(connection, now)
            updated = connection.execute(
                """
                UPDATE activation_codes
                SET remaining = remaining - 1, updated_at = CURRENT_TIMESTAMP
                WHERE code = ? AND remaining > 0
                """,
                (normalized_code,),
            ).rowcount
            if not updated:
                return None
            remaining = connection.execute(
                "SELECT remaining FROM activation_codes WHERE code = ?", (normalized_code,)
            ).fetchone()["remaining"]
            reservation_id = uuid.uuid4().hex
            connection.execute(
                """
                INSERT INTO quota_reservations(reservation_id, kind, code, state, expires_at)
                VALUES (?, 'activation', ?, 'reserved', ?)
                """,
                (reservation_id, normalized_code, self._expires_at(now, expiry_seconds)),
            )
        return QuotaReservation(reservation_id, int(remaining))

    def reserve_free(
        self,
        client_hash: str,
        usage_date: str,
        limit: int,
        *,
        expiry_seconds: int = 300,
    ) -> QuotaReservation | None:
        self.initialize()
        now = self._now()
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._release_expired(connection, now)
            row = connection.execute(
                "SELECT usage_date, count FROM free_usage WHERE client_hash = ?", (client_hash,)
            ).fetchone()
            used = int(row["count"]) if row and row["usage_date"] == usage_date else 0
            if used >= limit:
                return None
            next_count = used + 1
            connection.execute(
                """
                INSERT INTO free_usage(client_hash, usage_date, count) VALUES (?, ?, ?)
                ON CONFLICT(client_hash) DO UPDATE SET usage_date = excluded.usage_date, count = excluded.count
                """,
                (client_hash, usage_date, next_count),
            )
            reservation_id = uuid.uuid4().hex
            connection.execute(
                """
                INSERT INTO quota_reservations(
                    reservation_id, kind, client_hash, usage_date, state, expires_at
                ) VALUES (?, 'free', ?, ?, 'reserved', ?)
                """,
                (reservation_id, client_hash, usage_date, self._expires_at(now, expiry_seconds)),
            )
        return QuotaReservation(reservation_id, limit - next_count)

    def settle_reservation(self, reservation_id: str) -> bool:
        """Mark a delivered response as consumed. Repeated settlement is harmless."""
        return self._finish_reservation(reservation_id, consume=True)

    def release_reservation(self, reservation_id: str) -> bool:
        """Return a reservation that failed before delivering a response."""
        return self._finish_reservation(reservation_id, consume=False)

    def _finish_reservation(self, reservation_id: str, *, consume: bool) -> bool:
        self.initialize()
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM quota_reservations WHERE reservation_id = ?", (reservation_id,)
            ).fetchone()
            if row is None or row["state"] != "reserved":
                return False
            if consume:
                connection.execute(
                    "UPDATE quota_reservations SET state = 'settled' WHERE reservation_id = ?",
                    (reservation_id,),
                )
                return True
            self._restore_reservation(connection, row)
            connection.execute(
                "UPDATE quota_reservations SET state = 'released' WHERE reservation_id = ?",
                (reservation_id,),
            )
            return True

    @staticmethod
    def _now() -> datetime:
        return datetime.now(UTC)

    @staticmethod
    def _expires_at(now: datetime, expiry_seconds: int) -> str:
        return (now + timedelta(seconds=max(1, expiry_seconds))).isoformat()

    def _release_expired(self, connection: sqlite3.Connection, now: datetime) -> None:
        rows = connection.execute(
            """
            SELECT * FROM quota_reservations
            WHERE state = 'reserved' AND expires_at <= ?
            """,
            (now.isoformat(),),
        ).fetchall()
        for row in rows:
            self._restore_reservation(connection, row)
            connection.execute(
                "UPDATE quota_reservations SET state = 'released' WHERE reservation_id = ?",
                (row["reservation_id"],),
            )

    @staticmethod
    def _restore_reservation(connection: sqlite3.Connection, row: sqlite3.Row) -> None:
        if row["kind"] == "activation":
            connection.execute(
                """
                UPDATE activation_codes
                SET remaining = remaining + 1, updated_at = CURRENT_TIMESTAMP
                WHERE code = ?
                """,
                (row["code"],),
            )
        else:
            connection.execute(
                """
                UPDATE free_usage
                SET count = CASE WHEN count > 0 THEN count - 1 ELSE 0 END
                WHERE client_hash = ? AND usage_date = ?
                """,
                (row["client_hash"], row["usage_date"]),
            )

    def summary_counts(self) -> dict[str, int]:
        self.initialize()
        tables = (
            "activation_codes",
            "free_usage",
            "fusion_generations",
            "fusion_feedback",
            "family_feedback",
        )
        with self.connect() as connection:
            return {
                table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in tables
            }

    def import_legacy(
        self,
        *,
        activation_file: Path | None = None,
        free_usage_file: Path | None = None,
        feedback_dir: Path | None = None,
        generation_dir: Path | None = None,
    ) -> MigrationReport:
        """Import append-only runtime files. Re-running never duplicates JSONL rows."""
        self.initialize()
        counts = {
            "activation_codes": 0,
            "free_usage": 0,
            "fusion_generations": 0,
            "fusion_feedback": 0,
            "family_feedback": 0,
            "skipped_records": 0,
        }
        with self.connect() as connection:
            if activation_file is not None:
                counts["activation_codes"] += self._import_activation_codes(connection, activation_file)
            if free_usage_file is not None:
                counts["free_usage"] += self._import_free_usage(connection, free_usage_file)
            if feedback_dir is not None:
                self._import_feedback_dir(connection, feedback_dir, counts)
            if generation_dir is not None:
                self._import_generation_dir(connection, generation_dir, counts)
        return MigrationReport(**counts)

    @staticmethod
    def _read_json(path: Path) -> dict:
        if not path.exists():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return data if isinstance(data, dict) else {}

    def _import_activation_codes(self, connection: sqlite3.Connection, path: Path) -> int:
        count = 0
        for code, entry in self._read_json(path).items():
            if not isinstance(entry, dict):
                continue
            remaining = entry.get("剩余", 0)
            if not isinstance(remaining, int) or remaining < 0:
                continue
            connection.execute(
                """
                INSERT INTO activation_codes(code, remaining, note)
                VALUES (?, ?, ?)
                ON CONFLICT(code) DO UPDATE SET
                    remaining = excluded.remaining,
                    note = excluded.note,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (str(code).upper(), remaining, str(entry.get("备注", ""))),
            )
            count += 1
        return count

    def _import_free_usage(self, connection: sqlite3.Connection, path: Path) -> int:
        count = 0
        for client_hash, entry in self._read_json(path).items():
            if not isinstance(entry, dict):
                continue
            usage_date, usage_count = entry.get("date"), entry.get("count")
            if not isinstance(usage_date, str) or not isinstance(usage_count, int) or usage_count < 0:
                continue
            connection.execute(
                """
                INSERT INTO free_usage(client_hash, usage_date, count)
                VALUES (?, ?, ?)
                ON CONFLICT(client_hash) DO UPDATE SET
                    usage_date = excluded.usage_date,
                    count = excluded.count
                """,
                (str(client_hash), usage_date, usage_count),
            )
            count += 1
        return count

    def _import_feedback_dir(self, connection: sqlite3.Connection, directory: Path, counts: dict[str, int]) -> None:
        for path in sorted(directory.glob("fusion_feedback_*.jsonl")):
            self._import_jsonl(connection, path, "fusion_feedback", counts)
        for path in sorted(directory.glob("feedback_*.jsonl")):
            self._import_jsonl(connection, path, "family_feedback", counts)

    def _import_generation_dir(self, connection: sqlite3.Connection, directory: Path, counts: dict[str, int]) -> None:
        for path in sorted(directory.glob("fusion_generation_*.jsonl")):
            self._import_jsonl(connection, path, "fusion_generations", counts)

    def _import_jsonl(
        self,
        connection: sqlite3.Connection,
        path: Path,
        destination: str,
        counts: dict[str, int],
    ) -> None:
        if not path.exists():
            return
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return
        for line in lines:
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                counts["skipped_records"] += 1
                continue
            if not isinstance(record, dict):
                counts["skipped_records"] += 1
                continue
            content_hash = self._legacy_hash(destination, record)
            inserted = connection.execute(
                "INSERT OR IGNORE INTO legacy_imports(content_hash, source) VALUES (?, ?)",
                (content_hash, str(path)),
            ).rowcount
            if not inserted:
                continue
            if self._insert_record(connection, destination, content_hash, record):
                counts[destination] += 1
            else:
                counts["skipped_records"] += 1

    @staticmethod
    def _legacy_hash(destination: str, record: dict) -> str:
        serialized = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(f"{destination}:{serialized}".encode()).hexdigest()

    @staticmethod
    def _number(value) -> float | None:
        try:
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    def _insert_record(
        self,
        connection: sqlite3.Connection,
        destination: str,
        content_hash: str,
        record: dict,
    ) -> bool:
        if destination == "fusion_generations":
            generation_id = record.get("generation_id")
            timestamp = record.get("timestamp")
            if not isinstance(generation_id, str) or not isinstance(timestamp, str):
                return False
            result = connection.execute(
                """
                INSERT OR IGNORE INTO fusion_generations(
                    generation_id, timestamp, generation_type, outcome, duration_ms,
                    prompt_version, model, temperature, repaired, error_class, synthetic
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    generation_id, timestamp, str(record.get("generation_type", "fusion")),
                    str(record.get("outcome", "unknown")), record.get("duration_ms"),
                    record.get("prompt_version"), record.get("model"), self._number(record.get("temperature")),
                    int(bool(record.get("repaired"))), record.get("error_class"), int(bool(record.get("synthetic"))),
                ),
            )
            return result.rowcount == 1
        if destination == "fusion_feedback":
            timestamp, rating = record.get("timestamp"), record.get("rating")
            if not isinstance(timestamp, str) or not isinstance(rating, str):
                return False
            result = connection.execute(
                """
                INSERT OR IGNORE INTO fusion_feedback(
                    legacy_hash, generation_id, timestamp, rating, inaccurate_section,
                    report_hash, report_length, prompt_version, model, temperature, repaired, synthetic
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    content_hash, record.get("generation_id"), timestamp, rating,
                    str(record.get("inaccurate_section", "")), record.get("report_hash"),
                    record.get("report_length"), record.get("prompt_version"), record.get("model"),
                    self._number(record.get("temperature")), int(bool(record.get("repaired"))),
                    int(bool(record.get("synthetic"))),
                ),
            )
            return result.rowcount == 1
        if destination == "family_feedback":
            timestamp, user_level = record.get("timestamp"), record.get("user_level")
            if not isinstance(timestamp, str) or not isinstance(user_level, str):
                return False
            result = connection.execute(
                """
                INSERT OR IGNORE INTO family_feedback(
                    legacy_hash, timestamp, engine_level, user_level, discrepancy, discrepancy_detail, synthetic
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    content_hash, timestamp, str(record.get("engine_level", "")), user_level,
                    int(bool(record.get("discrepancy"))), record.get("discrepancy_detail"),
                    int(bool(record.get("synthetic"))),
                ),
            )
            return result.rowcount == 1
        return False
