from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


class DatasetHistoryManager:
    """Tracks uploaded datasets, their metadata, and the active dataset selection."""

    SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xls"}

    def __init__(self, datasets_dir: str | Path) -> None:
        self.datasets_dir = Path(datasets_dir)
        self.datasets_dir.mkdir(exist_ok=True)
        self.history_path = self.datasets_dir / "dataset_history.json"
        self.active_path = self.datasets_dir / "active_dataset.json"

    def create_storage_name(self, filename: str) -> str:
        original = Path(filename or "dataset.csv")
        extension = original.suffix.lower() or ".csv"
        safe_stem = re.sub(r"[^A-Za-z0-9._-]+", "_", original.stem).strip("._") or "dataset"
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
        return f"{timestamp}_{safe_stem}{extension}"

    def record_upload(
        self,
        filename: str,
        stored_filename: str,
        row_count: int,
        column_count: int,
    ) -> dict[str, Any]:
        history = self._sync_history()
        entry = {
            "id": stored_filename,
            "filename": filename,
            "stored_filename": stored_filename,
            "upload_time": self._utc_now(),
            "row_count": int(row_count),
            "column_count": int(column_count),
        }
        history = [item for item in history if item.get("id") != entry["id"]]
        history.append(entry)
        self._write_history(history)
        self.set_active_dataset(entry["id"])
        return self._public_record(entry, entry["id"])

    def list_datasets(self) -> list[dict[str, Any]]:
        history = self._sync_history()
        active_id = self.get_active_dataset_id()
        ordered = sorted(history, key=lambda item: item.get("upload_time", ""), reverse=True)
        return [self._public_record(item, active_id) for item in ordered if self.get_dataset_path(item).exists()]

    def get_dataset_record(self, dataset_id: str) -> dict[str, Any]:
        history = self._sync_history()
        for item in history:
            if item.get("id") == dataset_id:
                path = self.get_dataset_path(item)
                if not path.exists():
                    raise ValueError("The requested dataset file is missing.")
                return item
        raise ValueError("Dataset not found in history.")

    def set_active_dataset(self, dataset_id: str) -> dict[str, Any]:
        record = self.get_dataset_record(dataset_id)
        self.active_path.write_text(json.dumps({"id": dataset_id}, indent=2), encoding="utf-8")
        return record

    def get_active_dataset_id(self) -> str | None:
        history = sorted(self._sync_history(), key=lambda item: item.get("upload_time", ""), reverse=True)
        valid_ids = {item["id"] for item in history}

        if self.active_path.exists():
            try:
                payload = json.loads(self.active_path.read_text(encoding="utf-8"))
                dataset_id = payload.get("id")
                if dataset_id and str(dataset_id) in valid_ids:
                    return str(dataset_id)
            except json.JSONDecodeError:
                pass

        if history:
            dataset_id = history[0]["id"]
            self.active_path.write_text(json.dumps({"id": dataset_id}, indent=2), encoding="utf-8")
            return dataset_id
        return None

    def get_active_dataset_record(self) -> dict[str, Any] | None:
        active_id = self.get_active_dataset_id()
        if not active_id:
            return None
        try:
            return self.get_dataset_record(active_id)
        except ValueError:
            return None

    def get_dataset_path(self, record_or_id: dict[str, Any] | str) -> Path:
        stored_filename = record_or_id if isinstance(record_or_id, str) else record_or_id.get("stored_filename") or record_or_id.get("id")
        return self.datasets_dir / str(stored_filename)

    def _sync_history(self) -> list[dict[str, Any]]:
        history = self._read_history()
        history_by_id = {str(item.get("id") or item.get("stored_filename")): self._normalize_record(item) for item in history}

        changed = False
        for path in self._dataset_files():
            dataset_id = path.name
            if dataset_id in history_by_id:
                continue

            metadata = self._inspect_dataset_file(path)
            history_by_id[dataset_id] = {
                "id": dataset_id,
                "filename": path.name,
                "stored_filename": path.name,
                "upload_time": datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat().replace("+00:00", "Z"),
                "row_count": metadata["row_count"],
                "column_count": metadata["column_count"],
            }
            changed = True

        filtered_history = [
            record
            for record in history_by_id.values()
            if self.get_dataset_path(record).exists()
        ]
        filtered_history.sort(key=lambda item: item.get("upload_time", ""))

        if changed or len(filtered_history) != len(history):
            self._write_history(filtered_history)

        return filtered_history

    def _read_history(self) -> list[dict[str, Any]]:
        if not self.history_path.exists():
            return []

        try:
            payload = json.loads(self.history_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []

        if not isinstance(payload, list):
            return []
        return [self._normalize_record(item) for item in payload if isinstance(item, dict)]

    def _write_history(self, history: list[dict[str, Any]]) -> None:
        self.history_path.write_text(json.dumps(history, indent=2), encoding="utf-8")

    def _dataset_files(self) -> list[Path]:
        return [
            path
            for path in self.datasets_dir.iterdir()
            if path.is_file() and path.suffix.lower() in self.SUPPORTED_EXTENSIONS
        ]

    def _inspect_dataset_file(self, path: Path) -> dict[str, int]:
        try:
            if path.suffix.lower() == ".csv":
                dataframe = pd.read_csv(path)
            else:
                dataframe = pd.read_excel(path)
        except Exception:
            return {"row_count": 0, "column_count": 0}

        return {
            "row_count": int(len(dataframe)),
            "column_count": int(len(dataframe.columns)),
        }

    def _normalize_record(self, record: dict[str, Any]) -> dict[str, Any]:
        dataset_id = str(record.get("id") or record.get("stored_filename") or record.get("filename") or "")
        filename = str(record.get("filename") or dataset_id or "dataset")
        stored_filename = str(record.get("stored_filename") or dataset_id or filename)
        upload_time = str(record.get("upload_time") or self._utc_now())
        return {
            "id": dataset_id or stored_filename,
            "filename": filename,
            "stored_filename": stored_filename,
            "upload_time": upload_time,
            "row_count": int(record.get("row_count") or 0),
            "column_count": int(record.get("column_count") or 0),
        }

    def _public_record(self, record: dict[str, Any], active_id: str | None) -> dict[str, Any]:
        normalized = self._normalize_record(record)
        return {
            "id": normalized["id"],
            "filename": normalized["filename"],
            "upload_time": normalized["upload_time"],
            "row_count": normalized["row_count"],
            "column_count": normalized["column_count"],
            "is_active": normalized["id"] == active_id,
        }

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


