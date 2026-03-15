from __future__ import annotations

from collections import defaultdict
from typing import Any

import numpy as np
import pandas as pd


class AnomalyDetector:
    """Detects anomalous rows in numeric columns using the IQR method."""

    TRACKING_COLUMN = "original_row"

    def detect(self, dataframe: pd.DataFrame) -> dict[str, Any]:
        numeric_columns = [
            column
            for column in dataframe.select_dtypes(include=[np.number]).columns.tolist()
            if column != self.TRACKING_COLUMN
        ]
        anomaly_map: dict[int, list[str]] = defaultdict(list)

        for column in numeric_columns:
            series = pd.to_numeric(dataframe[column], errors="coerce").dropna()
            if series.empty:
                continue

            q1 = float(series.quantile(0.25))
            q3 = float(series.quantile(0.75))
            iqr = q3 - q1

            lower_bound = q1 - (1.5 * iqr)
            upper_bound = q3 + (1.5 * iqr)

            mask = (series < lower_bound) | (series > upper_bound)
            for row_index in series[mask].index.tolist():
                anomaly_map[int(row_index)].append(column)

        visible_columns = [column for column in dataframe.columns if column != self.TRACKING_COLUMN]
        if not anomaly_map:
            empty_columns = [self.TRACKING_COLUMN, "row", "anomaly_columns", *visible_columns]
            return {
                "anomaly_count": 0,
                "anomaly_records": pd.DataFrame(columns=empty_columns),
            }

        anomaly_indices = sorted(anomaly_map.keys())
        anomaly_records = dataframe.loc[anomaly_indices].copy()

        if self.TRACKING_COLUMN in anomaly_records.columns:
            original_rows = [int(value) for value in anomaly_records[self.TRACKING_COLUMN].tolist()]
        else:
            original_rows = [int(index) + 2 for index in anomaly_indices]

        base_records = anomaly_records.drop(columns=[self.TRACKING_COLUMN, "row"], errors="ignore").copy()
        base_records.insert(0, self.TRACKING_COLUMN, original_rows)
        base_records.insert(1, "row", original_rows)
        base_records.insert(
            2,
            "anomaly_columns",
            [", ".join(sorted(set(anomaly_map[index]))) for index in anomaly_indices],
        )

        return {
            "anomaly_count": int(len(base_records)),
            "anomaly_records": base_records,
        }

