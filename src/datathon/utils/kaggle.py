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

    if not os.getenv("KAGGLE_USERNAME") or not os.getenv("KAGGLE_KEY"):
        raise RuntimeError(
            "Missing Kaggle credentials. Set KAGGLE_USERNAME and KAGGLE_KEY in .env "
            "or provide KAGGLE_API_TOKEN."
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
