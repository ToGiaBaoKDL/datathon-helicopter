from __future__ import annotations

import json
import os

from dotenv import load_dotenv

from datathon.utils.paths import project_root


def load_kaggle_credentials() -> None:
    load_dotenv(dotenv_path=project_root() / ".env", override=False)


def ensure_kaggle_cli_and_auth() -> None:
    token = (os.getenv("KAGGLE_API_TOKEN") or "").strip()
    if not token:
        raise RuntimeError(
            "Missing KAGGLE_API_TOKEN. Set it in .env or as an environment variable."
        )

    username, key = _parse_token(token)
    if not key:
        raise RuntimeError("Invalid KAGGLE_API_TOKEN format.")

    os.environ.setdefault("KAGGLE_USERNAME", username or "")
    os.environ.setdefault("KAGGLE_KEY", key)


def _parse_token(token: str) -> tuple[str | None, str]:
    if token.startswith("{"):
        try:
            parsed = json.loads(token)
        except json.JSONDecodeError:
            return None, ""
        if isinstance(parsed, dict):
            username = parsed.get("username")
            key = parsed.get("key")
            if isinstance(key, str) and key:
                return (username if isinstance(username, str) else None), key
        return None, ""

    if ":" in token:
        username, key = token.split(":", 1)
        username = username.strip()
        key = key.strip()
        if key:
            return username or None, key
        return None, ""

    return None, token
