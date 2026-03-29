"""
poll_milon — Cloud Function entrypoint.

HTTP trigger. Returns JSON with a 200 on success, 500 on failure.
Designed to be called by Cloud Scheduler every 6 hours.
"""

import json
import logging

import functions_framework

import db
from milon_client import MilonClient
from parser import parse_device_names, parse_sessions
from secrets import get_secret

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
log = logging.getLogger(__name__)


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
    training_id  = get_secret("milon-training-id")
    database_url = get_secret("neon-database-url")

    # 2. Fetch from Milon API
    catalogue = client.fetch_device_names()
    sessions = client.fetch_training_stats(training_id)

    # 3. Parse into DB rows
    device_name_rows = parse_device_names(catalogue)
    training_session_rows = parse_sessions(sessions, catalogue)

    # 4. Upsert to database
    with db.get_connection(database_url) as conn:
        db.check_tables(conn)
        db.upsert_device_names(conn, device_name_rows)
        inserted, skipped = db.upsert_training_rows(conn, training_session_rows)

    result = {
        "sessions_found": len(sessions),
        "rows_upserted": inserted,
        "rows_skipped": skipped,
    }
    log.info("--- Polling done: %s ---", result)
    return (json.dumps(result), 200, {"Content-Type": "application/json"})


# For local development
if __name__ == "__main__":
    body, status, headers = poll_milon()
    print(f"Status: {status}")
    print(json.dumps(json.loads(body), indent=2))