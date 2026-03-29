"""
Milon API client.
"""

import logging
from dataclasses import dataclass
from functools import cached_property

import requests

from models import DeviceInfo, HomeStats, LoginResponse, SessionData

log = logging.getLogger(__name__)

MILON_BASE = "https://www.milonme.com/api"


@dataclass
class _AuthResult:
    token: str
    login_response: LoginResponse


class MilonClient:
    def __init__(self, api_key: str, email: str, password: str) -> None:
        self._api_key = api_key
        self._email = email
        self._password = password

    @cached_property
    def _auth(self) -> _AuthResult:
        """Authenticate once and cache the result for the lifetime of this instance."""
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
        return _AuthResult(
            token=token,
            login_response=LoginResponse.model_validate(response.json()),
        )

    @property
    def user_id(self) -> str:
        return self._auth.login_response.user_id

    @property
    def studio_id(self) -> int:
        return self._auth.login_response.d.studio_id

    @cached_property
    def training_id(self) -> int:
        log.info("Fetching active training plan ID")
        url = f"{MILON_BASE}/user/stats/home/{self.studio_id}/{self.user_id}"
        response = requests.get(url, headers=self.headers, timeout=30)
        response.raise_for_status()
        return HomeStats.model_validate(response.json()).active_training.training_id

    @property
    def headers(self) -> dict[str, str]:
        return {
            "x-api-key": self._api_key,
            "Cookie": f"rs-token={self._auth.token}",
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

    def fetch_training_stats(self) -> list[SessionData]:
        """
        Retrieve all training sessions for the active training plan.
        """
        url = f"{MILON_BASE}/user/stats/premium/{self.studio_id}/{self.user_id}/{self.training_id}"
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