from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


class AnomalyExplainer:
    """Creates simple natural-language explanations for detected anomalies."""

    def explain(self, dataframe: pd.DataFrame, anomaly_records: pd.DataFrame) -> list[dict[str, Any]]:
        if anomaly_records.empty:
            return []

        bounds = self._calculate_bounds(dataframe)
        explanations: list[dict[str, Any]] = []

        for _, record in anomaly_records.iterrows():
            row_number = int(record.get("original_row", record.get("row", -1)))
            anomaly_columns = self._extract_anomaly_columns(record)
            for column in anomaly_columns:
                if column not in bounds:
                    continue

                value = record.get(column)
                if value is None or pd.isna(value):
                    continue

                lower_bound = bounds[column]["lower_bound"]
                upper_bound = bounds[column]["upper_bound"]
                numeric_value = float(value)
                direction = "high" if numeric_value > upper_bound else "low"
                explanation = self._build_explanation(column, numeric_value, lower_bound, upper_bound, direction, row_number)

                explanations.append(
                    {
                        "row": row_number,
                        "original_row": row_number,
                        "column": column,
                        "value": self._display_value(value),
                        "lower_bound": round(lower_bound, 4),
                        "upper_bound": round(upper_bound, 4),
                        "direction": direction,
                        "explanation": explanation,
                    }
                )

        return explanations

    @staticmethod
    def _calculate_bounds(dataframe: pd.DataFrame) -> dict[str, dict[str, float]]:
        bounds: dict[str, dict[str, float]] = {}
        numeric_columns = [
            column
            for column in dataframe.select_dtypes(include=[np.number]).columns.tolist()
            if column != "original_row"
        ]

        for column in numeric_columns:
            series = pd.to_numeric(dataframe[column], errors="coerce").dropna()
            if series.empty:
                continue

            q1 = float(series.quantile(0.25))
            q3 = float(series.quantile(0.75))
            iqr = q3 - q1
            lower_bound = q1 - (1.5 * iqr)
            upper_bound = q3 + (1.5 * iqr)

            bounds[column] = {
                "lower_bound": lower_bound,
                "upper_bound": upper_bound,
            }

        return bounds

    @staticmethod
    def _extract_anomaly_columns(record: pd.Series) -> list[str]:
        return [
            value.strip()
            for value in str(record.get("anomaly_columns", "")).split(",")
            if value.strip()
        ]

    def _build_explanation(
        self,
        column: str,
        value: float,
        lower_bound: float,
        upper_bound: float,
        direction: str,
        row_number: int,
    ) -> str:
        range_text = f"{self._display_value(lower_bound)} to {self._display_value(upper_bound)}"
        direction_text = "unusually high" if direction == "high" else "unusually low"
        return (
            f"Row {row_number}: The value {self._display_value(value)} in column {column} is {direction_text} "
            f"compared to the normal dataset range of {range_text}."
        )

    @staticmethod
    def _display_value(value: Any) -> str:
        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            return str(value)

        if numeric_value.is_integer():
            return f"{int(numeric_value):,}"
        return f"{numeric_value:,.2f}"
