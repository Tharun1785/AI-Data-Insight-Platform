from __future__ import annotations

from io import BytesIO
from typing import Any

import numpy as np
import pandas as pd

from backend.anomaly_detector import AnomalyDetector
from backend.anomaly_explainer import AnomalyExplainer
from backend.email_alert import send_anomaly_alert


class DataProcessor:
    """Loads datasets, cleans them, and returns beginner-friendly summaries."""

    ALLOWED_EXTENSIONS = {".csv", ".xlsx"}
    TRACKING_COLUMN = "original_row"

    def __init__(self) -> None:
        self.dataframe: pd.DataFrame | None = None
        self.dataset_name: str | None = None
        self.anomaly_detector = AnomalyDetector()
        self.anomaly_explainer = AnomalyExplainer()
        self.anomaly_records: pd.DataFrame = pd.DataFrame()
        self.anomaly_count: int = 0
        self.anomaly_explanations: list[dict[str, Any]] = []

    def reset(self) -> None:
        self.dataframe = None
        self.dataset_name = None
        self.anomaly_records = pd.DataFrame()
        self.anomaly_count = 0
        self.anomaly_explanations = []

    def load_dataset(self, file_bytes: bytes, filename: str) -> pd.DataFrame:
        extension = self._get_extension(filename)
        if extension not in self.ALLOWED_EXTENSIONS:
            raise ValueError("Only CSV and XLSX files are supported.")

        if extension == ".csv":
            dataframe = pd.read_csv(BytesIO(file_bytes))
        else:
            dataframe = pd.read_excel(BytesIO(file_bytes))

        dataframe.columns = [str(column).strip() for column in dataframe.columns]
        dataframe[self.TRACKING_COLUMN] = dataframe.index + 2

        self.dataset_name = filename
        self.dataframe = self.clean_dataset(dataframe)
        self._run_anomaly_detection()
        return self.get_dataframe()

    def clean_dataset(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        df = dataframe.copy()
        df.columns = [str(column).strip() for column in df.columns]

        data_columns = self._visible_columns(df)
        duplicate_rows = int(df.duplicated(subset=data_columns).sum())
        missing_values_before = int(df[data_columns].isna().sum().sum())

        df = df.drop_duplicates(subset=data_columns).copy()

        detected_datetime_columns: list[str] = []
        for column in df.select_dtypes(include=["object"]).columns:
            if column == self.TRACKING_COLUMN:
                continue
            parsed = pd.to_datetime(df[column], errors="coerce")
            if parsed.notna().mean() >= 0.7:
                df[column] = parsed
                detected_datetime_columns.append(column)

        numeric_columns = self._numeric_columns(df)
        datetime_columns = self._datetime_columns(df)
        categorical_columns = self._categorical_columns(df)

        for column in numeric_columns:
            if df[column].isna().any():
                df[column] = pd.to_numeric(df[column], errors="coerce")
                df[column] = df[column].fillna(df[column].median())

        for column in categorical_columns:
            if df[column].isna().any():
                mode = df[column].mode(dropna=True)
                fill_value = mode.iloc[0] if not mode.empty else "Unknown"
                df[column] = df[column].fillna(fill_value)

        for column in datetime_columns:
            if df[column].isna().any():
                df[column] = df[column].ffill().bfill()

        df.attrs["duplicate_rows_removed"] = duplicate_rows
        df.attrs["missing_values_before_cleaning"] = missing_values_before
        df.attrs["missing_values_after_cleaning"] = int(df[data_columns].isna().sum().sum())
        df.attrs["detected_datetime_columns"] = detected_datetime_columns
        return df

    def has_dataset(self) -> bool:
        return self.dataframe is not None

    def get_dataframe(self) -> pd.DataFrame:
        self._ensure_dataset()
        return self._visible_dataframe()

    def get_column_types(self) -> dict[str, list[str]]:
        self._ensure_dataset()
        assert self.dataframe is not None

        return {
            "numeric": self._numeric_columns(self.dataframe),
            "categorical": self._categorical_columns(self.dataframe),
            "datetime": self._datetime_columns(self.dataframe),
        }

    def get_statistics(self) -> dict[str, dict[str, Any]]:
        self._ensure_dataset()
        assert self.dataframe is not None

        statistics: dict[str, dict[str, Any]] = {}
        for column in self._numeric_columns(self.dataframe):
            series = pd.to_numeric(self.dataframe[column], errors="coerce").dropna()
            if series.empty:
                continue

            mode = series.mode()
            statistics[column] = {
                "mean": round(float(series.mean()), 4),
                "median": round(float(series.median()), 4),
                "mode": round(float(mode.iloc[0]), 4) if not mode.empty else None,
                "min": round(float(series.min()), 4),
                "max": round(float(series.max()), 4),
                "std": round(float(series.std(ddof=0)), 4),
            }
        return statistics

    def get_correlation_pairs(self, limit: int = 5) -> list[dict[str, Any]]:
        self._ensure_dataset()
        assert self.dataframe is not None

        numeric_columns = self._numeric_columns(self.dataframe)
        if len(numeric_columns) < 2:
            return []

        corr_matrix = (
            self.dataframe[numeric_columns]
            .apply(pd.to_numeric, errors="coerce")
            .corr(numeric_only=True)
        )
        pairs: list[dict[str, Any]] = []
        for index, first in enumerate(numeric_columns):
            for second in numeric_columns[index + 1 :]:
                value = corr_matrix.loc[first, second]
                if pd.isna(value):
                    continue
                pairs.append(
                    {
                        "column_a": first,
                        "column_b": second,
                        "correlation": round(float(value), 4),
                    }
                )

        pairs.sort(key=lambda item: abs(item["correlation"]), reverse=True)
        return pairs[:limit]

    def get_preview(self, limit: int = 10) -> list[dict[str, Any]]:
        self._ensure_dataset()

        preview = self._visible_dataframe().head(limit).copy()
        return self._format_records(preview)

    def get_top_records(self, limit: int = 5) -> list[dict[str, Any]]:
        self._ensure_dataset()

        return self._format_records(self._visible_dataframe().head(limit).copy())

    def get_anomalies(self) -> dict[str, Any]:
        self._ensure_dataset()
        return {
            "anomaly_count": int(self.anomaly_count),
            "anomaly_records": self._format_records(self.anomaly_records.copy()),
            "anomaly_explanations": self.anomaly_explanations,
        }

    def get_anomaly_dataframe(self) -> pd.DataFrame:
        self._ensure_dataset()
        return self.anomaly_records.copy()

    def get_summary(self) -> dict[str, Any]:
        self._ensure_dataset()
        assert self.dataframe is not None

        visible_dataframe = self._visible_dataframe()
        column_types = self.get_column_types()
        missing_before = int(self.dataframe.attrs.get("missing_values_before_cleaning", 0))
        missing_after = int(self.dataframe.attrs.get("missing_values_after_cleaning", 0))
        anomaly_payload = self.get_anomalies()

        return {
            "dataset_name": self.dataset_name,
            "rows": int(len(visible_dataframe)),
            "columns": int(len(visible_dataframe.columns)),
            "column_names": visible_dataframe.columns.tolist(),
            "column_types": column_types,
            "missing_values_found": missing_before,
            "missing_values_remaining": missing_after,
            "missing_values_handled": max(missing_before - missing_after, 0),
            "duplicate_rows_removed": int(self.dataframe.attrs.get("duplicate_rows_removed", 0)),
            "preview": self.get_preview(10),
            "top_records": self.get_top_records(5),
            "statistics": self.get_statistics(),
            "correlations": self.get_correlation_pairs(),
            "anomaly_count": anomaly_payload["anomaly_count"],
            "anomaly_explanations": anomaly_payload["anomaly_explanations"],
        }

    def _run_anomaly_detection(self) -> None:
        self._ensure_dataset()
        assert self.dataframe is not None

        result = self.anomaly_detector.detect(self.dataframe)
        self.anomaly_count = int(result["anomaly_count"])
        self.anomaly_records = result["anomaly_records"]
        self.anomaly_explanations = self.anomaly_explainer.explain(self.dataframe, self.anomaly_records)

        if self.anomaly_count > 0:
            send_anomaly_alert(
                self.dataset_name or "Uploaded dataset",
                self.anomaly_count,
            )

    def _format_records(self, frame: pd.DataFrame) -> list[dict[str, Any]]:
        for column in frame.columns:
            if pd.api.types.is_datetime64_any_dtype(frame[column]):
                frame[column] = frame[column].dt.strftime("%Y-%m-%d")
        return frame.replace({np.nan: None}).to_dict(orient="records")

    def _ensure_dataset(self) -> None:
        if self.dataframe is None:
            raise ValueError("No dataset is loaded. Please upload a CSV or XLSX file.")

    def _visible_dataframe(self) -> pd.DataFrame:
        assert self.dataframe is not None
        return self.dataframe.drop(columns=[self.TRACKING_COLUMN], errors="ignore").copy()

    def _visible_columns(self, dataframe: pd.DataFrame) -> list[str]:
        return [column for column in dataframe.columns if column != self.TRACKING_COLUMN]

    def _numeric_columns(self, dataframe: pd.DataFrame) -> list[str]:
        return [
            column
            for column in dataframe.select_dtypes(include=[np.number]).columns.tolist()
            if column != self.TRACKING_COLUMN
        ]

    @staticmethod
    def _datetime_columns(dataframe: pd.DataFrame) -> list[str]:
        return [
            column
            for column in dataframe.columns
            if column != DataProcessor.TRACKING_COLUMN and pd.api.types.is_datetime64_any_dtype(dataframe[column])
        ]

    def _categorical_columns(self, dataframe: pd.DataFrame) -> list[str]:
        numeric_columns = self._numeric_columns(dataframe)
        datetime_columns = self._datetime_columns(dataframe)
        return [
            column
            for column in dataframe.columns
            if column not in numeric_columns and column not in datetime_columns and column != self.TRACKING_COLUMN
        ]

    @staticmethod
    def _get_extension(filename: str) -> str:
        lowered = filename.lower().strip()
        for extension in DataProcessor.ALLOWED_EXTENSIONS:
            if lowered.endswith(extension):
                return extension
        return ""

