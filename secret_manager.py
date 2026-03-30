"""
Secret Manager access.

All secrets are fetched from Google Secret Manager. The GCP project ID is
resolved from the GOOGLE_CLOUD_PROJECT environment variable if set, otherwise
derived from the application default credentials (which works automatically in
Cloud Functions 2nd gen and locally after `gcloud auth application-default login`).

Results are cached in memory for the lifetime of the function instance so
subsequent invocations in the same instance don't re-fetch.
"""

import os

import google.auth
from google.cloud import secretmanager

_cache: dict[str, str] = {}


def _project_id() -> str:
    if project_id := os.environ.get("GOOGLE_CLOUD_PROJECT"):
        return project_id
    _, project_id = google.auth.default()

    assert project_id, "Could not determine GCP project ID from environment or credentials"
    return project_id


def get_secret(name: str) -> str:
    """Return the latest version of a secret by name.

    Args:
        name: Secret Manager secret name, e.g. ``"milon-email"``.

    Returns:
        The secret payload as a stripped string.
    """
    if name in _cache:
        return _cache[name]

    project_id = _project_id()
    client = secretmanager.SecretManagerServiceClient()
    resource_name = f"projects/{project_id}/secrets/{name}/versions/latest"
    response = client.access_secret_version(request={"name": resource_name})
    value = response.payload.data.decode("utf-8").strip()
    _cache[name] = value
    return value
