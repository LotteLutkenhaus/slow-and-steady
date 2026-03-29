"""
Milon API client.
"""

import logging
from functools import cached_property

import requests

from models import DeviceInfo, SessionData

log = logging.getLogger(__name__)

MILON_BASE = "https://www.milonme.com/api"


class MilonClient:
    def __init__(self, api_key: str, email: str, password: str) -> None:
        self._api_key = api_key
        self._email = email
        self._password = password

    def token(self) -> str:
        """
        Authenticate with the API to obtain a session token (rs-token cookie).
        """
        log.info("Authenticating with milonme.com")
        response = requests.post(
            f"{MILON_BASE}/user/login",
            headers={
                "x-api-key": self._api_key,
                "content-type": "application/json",
            },
            json={"email": self._email, "password": self._password, "long_session": 0},
            timeout=30,
        )
        response.raise_for_status()

        token = None
        for part in response.headers.get("Set-Cookie", "").split(";"):
            part = part.strip()
            if part.startswith("rs-token="):
                token = part[len("rs-token="):]
                break

        if not token:
            raise RuntimeError("Login succeeded but rs-token was not found in response")

        log.info("Authentication successful")
        return token

    @cached_property
    def headers(self) -> dict[str, str]:
        """
        Return the cached headers; the token has a TTL of 60 minutes so we can cache it for the
        duration of the session.
        """
        return {
            "x-api-key": self._api_key,
            "Cookie": f"rs-token={self.token}",
        }

    def fetch_device_names(self) -> dict[int, DeviceInfo]:
        """
        Retrieve all Milon device info and return as a lookup (device_id -> DeviceInfo).
        """
        log.info("Fetching device name catalogue")
        response = requests.get(
            f"{MILON_BASE}/devices/en_GB",
            headers=self.headers,
            timeout=30,
        )
        response.raise_for_status()

        # API returns string keys; convert to int for consistent lookups
        return {
            int(device_id): DeviceInfo.model_validate(info)
            for device_id, info in response.json().items()
        }


    def fetch_training_stats(
        self,
        studio_id: str,
        user_id: str,
        training_id: str,
    ) -> list[SessionData]:
        url = f"{MILON_BASE}/user/stats/premium/{studio_id}/{user_id}/{training_id}"
        log.info("Fetching training stats from %s", url)
        response = requests.get(
            url,
            headers=self.headers,
            timeout=60,
        )
        response.raise_for_status()

        sessions = [SessionData.model_validate(s) for s in response.json()]
        log.info("Received %d session(s)", len(sessions))
        return sessions
