# Slow and Steady

The Milon Me app is not the best way to track progress. This project is part of a pipeline to 
retrieve data from the Milon API, store it in a Neon PostgreSQL database, and eventually use it for
analysis and visualization in a dashboard. 

This repo contais a Google Cloud function that polls the Milon API every 6 hours, retrieves training
data, and upserts it into the database. 

---

## Prerequisites

- [gcloud CLI](https://cloud.google.com/sdk/docs/install) installed and authenticated
- Python 3.12
- A [Neon](https://neon.tech) project with the schema applied (see below)
- A GCP project with the following APIs enabled:
  - Cloud Functions
  - Cloud Scheduler
  - Secret Manager

---

## Database setup

Create the tables in your Neon database before deploying:

```sql
CREATE TABLE device_names (
    device_id    int PRIMARY KEY,
    name         text,
    device_type  text,
    muscle_group text
);

CREATE TABLE training_sessions (
    session_ts        timestamptz NOT NULL,
    iteration         int,
    device_id         int NOT NULL,
    device_name       text,
    muscle_group      text,
    circuit           int,
    concentric_weight float,
    eccentric_weight  float,
    quality_score     int,
    reps              int,
    actid             text,
    ngid              int,
    PRIMARY KEY (session_ts, device_id, circuit)
);

CREATE INDEX idx_ts_device ON training_sessions (device_id, session_ts);
CREATE INDEX idx_ts_desc   ON training_sessions (session_ts DESC);
```

---

## Local development

### 1. Authenticate with GCP

```bash
gcloud auth application-default login
```

This lets `get_secret()` call Secret Manager with your personal credentials

### 2. Set the project

```bash
export GOOGLE_CLOUD_PROJECT=your-gcp-project-id
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run locally

```bash
python main.py
```

---

## Secret Manager setup

Create each secret once. The function always reads the `latest` version.

```bash
echo -n "value" | gcloud secrets create milon-email          --data-file=-
echo -n "value" | gcloud secrets create milon-password       --data-file=-
echo -n "value" | gcloud secrets create milon-api-key        --data-file=-
echo -n "value" | gcloud secrets create neon-database-url    --data-file=-
```

To update an existing secret:

```bash
echo -n "new-value" | gcloud secrets versions add milon-api-key --data-file=-
```

---

## Deploy

```bash
gcloud functions deploy poll_milon \
  --gen2 \
  --runtime python312 \
  --trigger-http \
  --allow-unauthenticated \
  --region europe-west4 \
  --source . \
  --entry-point poll_milon
```

Grant the function's service account access to Secret Manager:

```bash
gcloud projects add-iam-policy-binding your-gcp-project-id \
  --member="serviceAccount:your-function-sa@your-gcp-project-id.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

---

## Cloud Scheduler

Trigger the function every 6 hours:

```bash
gcloud scheduler jobs create http poll-milon-scheduler \
  --schedule="0 */6 * * *" \
  --uri="https://europe-west4-your-gcp-project-id.cloudfunctions.net/poll_milon" \
  --http-method=GET \
  --location=europe-west4
```

---

## Response format

On success (`200`):

```json
{
  "sessions_found": 12,
  "rows_upserted": 48,
  "rows_skipped": 192
}
```

On failure (`500`):

```json
{
  "error": "Internal error, check logs"
}
```