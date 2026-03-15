from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class SettingsManager:
    """Persists email settings in a simple JSON file."""

    def __init__(self, settings_path: Path | None = None) -> None:
        self.settings_path = settings_path or Path(__file__).resolve().parent.parent / "settings.json"

    def get_email_settings(self, include_password: bool = False) -> dict[str, str]:
        settings = self._load_settings()
        email_settings = self._normalize_email_settings(settings)

        if settings != email_settings:
            self._write_settings(email_settings)

        payload = {
            "sender_email": str(email_settings.get("sender_email", "")).strip(),
            "receiver_email": str(email_settings.get("receiver_email", "")).strip(),
        }
        if include_password:
            payload["sender_password"] = str(email_settings.get("sender_password", ""))
        return payload

    def save_email_settings(
        self,
        sender_email: str,
        sender_password: str,
        receiver_email: str,
    ) -> dict[str, str]:
        existing_settings = self.get_email_settings(include_password=True)
        saved_password = sender_password if sender_password != "" else existing_settings.get("sender_password", "")

        settings = {
            "sender_email": sender_email.strip(),
            "sender_password": saved_password,
            "receiver_email": receiver_email.strip(),
        }
        self._write_settings(settings)
        return self.get_email_settings(include_password=True)

    def _load_settings(self) -> dict[str, Any]:
        self._ensure_settings_file()
        try:
            return json.loads(self.settings_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            default_settings = self._default_settings()
            self._write_settings(default_settings)
            return default_settings

    def _write_settings(self, settings: dict[str, Any]) -> None:
        self.settings_path.parent.mkdir(parents=True, exist_ok=True)
        self.settings_path.write_text(
            json.dumps(settings, indent=2),
            encoding="utf-8",
        )

    def _ensure_settings_file(self) -> None:
        if self.settings_path.exists():
            return
        self._write_settings(self._default_settings())

    def _normalize_email_settings(self, settings: dict[str, Any]) -> dict[str, Any]:
        legacy_email_settings = settings.get("email", {}) if isinstance(settings.get("email", {}), dict) else {}
        return {
            "sender_email": str(
                settings.get("sender_email")
                or legacy_email_settings.get("sender_email")
                or ""
            ).strip(),
            "sender_password": str(
                settings.get("sender_password")
                or legacy_email_settings.get("sender_password")
                or ""
            ),
            "receiver_email": str(
                settings.get("receiver_email")
                or legacy_email_settings.get("receiver_email")
                or legacy_email_settings.get("recipient_email")
                or ""
            ).strip(),
        }

    @staticmethod
    def _default_settings() -> dict[str, Any]:
        return {
            "sender_email": "",
            "sender_password": "",
            "receiver_email": "",
        }
