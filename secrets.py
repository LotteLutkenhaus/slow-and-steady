"""
Secret Manager access.

All secrets are fetched from Google Secret Manager using the GCP project ID
from the GOOGLE_CLOUD_PROJECT environment variable (set automatically in
Cloud Functions). Results are cached in memory for the lifetime of the
function instance so subsequent invocations in the same instance don't re-fetch.

For local development, run `gcloud auth application-default login` once.
get_secret() will then reach Secret Manager with your personal credentials.
"""

import os

from google.cloud import secretmanager

_cache: dict[str, str] = {}


def get_secret(name: str) -> str:
    """Return the latest version of a secret by name.

    Args:
        name: Secret Manager secret name, e.g. ``"milon-email"``.

    Returns:
        The secret payload as a stripped string.
    """
    if name in _cache:
        return _cache[name]

    project_id = os.environ["GOOGLE_CLOUD_PROJECT"]
    client = secretmanager.SecretManagerServiceClient()
    resource_name = f"projects/{project_id}/secrets/{name}/versions/latest"
    response = client.access_secret_version(request={"name": resource_name})
    value = response.payload.data.decode("utf-8").strip()
    _cache[name] = value
    return value
