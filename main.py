"""
poll_milon — Cloud Function entrypoint.

HTTP trigger. Returns JSON with a 200 on success, 500 on failure.
Designed to be called by Cloud Scheduler every 6 hours.
"""

import json
import logging
import os
from datetime import datetime

import functions_framework

import db
from milon_client import MilonClient
from parser import parse_device_names, parse_sessions
from secrets import get_secret

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
log = logging.getLogger(__name__)


def _current_yymm() -> str:
    """
    We need to provide the year and month to fetch data for in this format: YYMM, e.g. "2603" for
    March 2026.
    """
    now = datetime.now()
    return f"{now.year % 100:02d}{now.month:02d}"


def _prev_yymm(yymm: str) -> str:
    year, month = int(yymm[:2]), int(yymm[2:])
    if month == 1:
        return f"{year - 1:02d}12"
    return f"{year:02d}{month - 1:02d}"


@functions_framework.http
def poll_milon():
    log.info("--- Polling starting ---")

    # 1. Load secrets
    log.info("Loading secrets")
    client = MilonClient(
        api_key=get_secret("milon-api-key"),
        email=get_secret("milon-email"),
        password=get_secret("milon-password"),
    )
    database_url = get_secret("neon-database-url")

    # 2. Fetch device catalogue once
    catalogue = client.fetch_device_names()

    # 3. Walk backwards month by month to retrieve training sessions, upserting the DB as we go
    total_sessions = 0
    total_inserted = 0
    total_skipped = 0
    yymm = _current_yymm()

    with db.get_connection(database_url) as conn:
        db.check_tables(conn)
        db.upsert_device_names(conn, parse_device_names(catalogue))

        while True:
            log.info("Fetching month %s", yymm)
            sessions = client.fetch_training_stats(yymm)

            if not sessions:
                log.info("No sessions returned for %s, stopping", yymm)
                break

            rows = parse_sessions(sessions, catalogue)
            inserted, skipped = db.upsert_training_rows(conn, rows)

            total_sessions += len(sessions)
            total_inserted += inserted
            total_skipped += skipped

            if inserted == 0:
                log.info("No new rows for %s — already synced, stopping", yymm)
                break

            yymm = _prev_yymm(yymm)

    result = {
        "sessions_found": total_sessions,
        "rows_upserted": total_inserted,
        "rows_skipped": total_skipped,
    }
    log.info("--- Polling done: %s ---", result)
    return (json.dumps(result), 200, {"Content-Type": "application/json"})


# For local development
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    def get_secret(name: str) -> str:  # noqa: F811 — intentional override for local dev
        env_key = "NEON_DEV_DATABASE_URL" if name == "neon-database-url" else name.upper().replace("-", "_")
        value = os.environ.get(env_key)
        if not value:
            raise RuntimeError(f"Missing environment variable: {env_key}")
        return value

    body, status, headers = poll_milon()
    print(f"Status: {status}")
    print(json.dumps(json.loads(body), indent=2))