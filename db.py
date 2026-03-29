import logging

import psycopg2

from models import DeviceNameRow, TrainingSessionRow

log = logging.getLogger(__name__)

REQUIRED_TABLES = {"device_names", "training_sessions"}


def get_connection(database_url: str):
    return psycopg2.connect(database_url)


def check_tables(conn) -> None:
    """
    Raise RuntimeError if any required tables are missing.
    """
    with conn.cursor() as cur:
        cur.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = ANY(%s)",
            (list(REQUIRED_TABLES),),
        )
        found = {row[0] for row in cur.fetchall()}

    missing = REQUIRED_TABLES - found
    if missing:
        raise RuntimeError(
            f"Required table(s) not found: {', '.join(sorted(missing))}. "
            "Please run the schema SQL before deploying."
        )


def upsert_device_names(conn, rows: list[DeviceNameRow]) -> None:
    log.info("Upserting %d device name(s)", len(rows))
    sql = """
        INSERT INTO device_names (device_id, name, device_type, muscle_group)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (device_id) DO UPDATE
            SET name         = EXCLUDED.name,
                device_type  = EXCLUDED.device_type,
                muscle_group = EXCLUDED.muscle_group
    """
    with conn.cursor() as cur:
        for row in rows:
            cur.execute(sql, (row.device_id, row.name, row.device_type, row.muscle_group))
    conn.commit()


def upsert_training_rows(conn, rows: list[TrainingSessionRow]) -> tuple[int, int]:
    """
    Insert training session rows, skipping any that already exist.
    Returns (inserted, skipped).
    """
    sql = """
        INSERT INTO training_sessions (
            session_ts, iteration, device_id, device_name, muscle_group,
            circuit, concentric_weight, eccentric_weight, quality_score, reps, actid, ngid
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        ON CONFLICT (session_ts, device_id, circuit) DO NOTHING
    """
    inserted = 0
    skipped = 0
    with conn.cursor() as cur:
        for row in rows:
            cur.execute(sql, (
                row.session_ts,
                row.iteration,
                row.device_id,
                row.device_name,
                row.muscle_group,
                row.circuit,
                row.concentric_weight,
                row.eccentric_weight,
                row.quality_score,
                row.reps,
                row.actid,
                row.ngid,
            ))
            if cur.rowcount == 1:
                inserted += 1
            else:
                skipped += 1
    conn.commit()
    log.info("Upsert complete: %d inserted, %d skipped", inserted, skipped)
    return inserted, skipped