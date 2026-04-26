from __future__ import annotations

import json
import os
import shutil
import subprocess

from dotenv import load_dotenv

from datathon.utils.paths import project_root


def load_kaggle_credentials() -> None:
    load_dotenv(dotenv_path=project_root() / ".env", override=False)
    _hydrate_credentials_from_token()


def ensure_kaggle_cli_and_auth() -> None:
    if shutil.which("kaggle") is None:
        raise RuntimeError(
            "Kaggle CLI not found. Install with 'uv add kaggle' and configure API credentials."
        )

    _hydrate_credentials_from_token()

    has_api_token = bool((os.getenv("KAGGLE_API_TOKEN") or "").strip())
    has_user_key = bool(os.getenv("KAGGLE_USERNAME") and os.getenv("KAGGLE_KEY"))

    if not (has_api_token or has_user_key):
        raise RuntimeError(
            "Missing Kaggle credentials. Set KAGGLE_API_TOKEN in .env "
            "(json, username:key, or raw key)."
        )


def validate_competition_access(competition: str) -> None:
    subprocess.run(
        [
            "kaggle",
            "competitions",
            "files",
            "-q",
            competition,
        ],
        check=True,
    )


def _hydrate_credentials_from_token() -> None:
    token = (os.getenv("KAGGLE_API_TOKEN") or "").strip()
    if not token:
        return

    if token.startswith("{"):
        try:
            parsed = json.loads(token)
        except json.JSONDecodeError:
            parsed = None

        if isinstance(parsed, dict):
            username = parsed.get("username")
            key = parsed.get("key")
            if isinstance(username, str) and username:
                os.environ.setdefault("KAGGLE_USERNAME", username)
            if isinstance(key, str) and key:
                os.environ.setdefault("KAGGLE_KEY", key)
        return

    if ":" in token and not os.getenv("KAGGLE_USERNAME"):
        username, key = token.split(":", 1)
        username = username.strip()
        key = key.strip()
        if username and key:
            os.environ.setdefault("KAGGLE_USERNAME", username)
            os.environ.setdefault("KAGGLE_KEY", key)
        return

    os.environ.setdefault("KAGGLE_KEY", token)
