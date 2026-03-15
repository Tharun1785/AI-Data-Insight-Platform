from __future__ import annotations

from typing import Any

import pandas as pd

try:
    from sklearn.linear_model import LinearRegression
except ImportError:  # pragma: no cover - graceful fallback for environments without sklearn
    LinearRegression = None


class Forecasting:
    """Predicts the next few values in a time series using linear regression."""

    FUTURE_STEPS = 5

    def generate(self, dataframe: pd.DataFrame, column_types: dict[str, list[str]]) -> dict[str, Any]:
        if LinearRegression is None:
            return {
                "available": False,
                "message": "Forecasting is unavailable because scikit-learn is not installed.",
            }

        datetime_column = self._preferred_datetime_column(column_types.get("datetime", []))
        metric_column = self._preferred_numeric_column(column_types.get("numeric", []))

        if not datetime_column or not metric_column:
            return {
                "available": False,
                "message": "Forecasting needs one date column and one numeric column.",
            }

        frame = dataframe[[datetime_column, metric_column]].copy()
        frame[datetime_column] = pd.to_datetime(frame[datetime_column], errors="coerce")
        frame[metric_column] = pd.to_numeric(frame[metric_column], errors="coerce")
        frame = frame.dropna(subset=[datetime_column, metric_column]).sort_values(datetime_column)
        if len(frame) < 2:
            return {
                "available": False,
                "message": "Not enough time-based data is available to build a forecast.",
            }

        grouped = frame.groupby(frame[datetime_column].dt.normalize())[metric_column].sum().reset_index()
        if len(grouped) < 2:
            return {
                "available": False,
                "message": "Not enough unique dates are available to build a forecast.",
            }

        grouped["ordinal"] = grouped[datetime_column].map(pd.Timestamp.toordinal)
        model = LinearRegression()
        model.fit(grouped[["ordinal"]], grouped[metric_column])

        future_dates = self._future_dates(grouped[datetime_column])
        future_ordinals = [[date.toordinal()] for date in future_dates]
        predicted_values = model.predict(future_ordinals)

        history = grouped.tail(12)
        history_labels = history[datetime_column].dt.strftime("%Y-%m-%d").tolist()
        history_values = [round(float(value), 2) for value in history[metric_column].tolist()]
        future_labels = [date.strftime("%Y-%m-%d") for date in future_dates]
        future_values = [round(float(value), 2) for value in predicted_values.tolist()]

        return {
            "available": True,
            "title": f"Future {metric_column} Prediction",
            "message": f"The model predicts the next {self.FUTURE_STEPS} values for {metric_column} using the {datetime_column} column.",
            "time_column": datetime_column,
            "metric_column": metric_column,
            "predictions": [
                {"label": label, "value": value}
                for label, value in zip(future_labels, future_values)
            ],
            "chartjs": {
                "labels": history_labels + future_labels,
                "datasets": [
                    {
                        "label": f"Historical {metric_column}",
                        "data": history_values + [None] * len(future_values),
                        "borderColor": "#111827",
                        "backgroundColor": "rgba(17, 24, 39, 0.08)",
                        "fill": False,
                        "tension": 0.2,
                        "pointRadius": 3,
                    },
                    {
                        "label": f"Forecast {metric_column}",
                        "data": [None] * len(history_values) + future_values,
                        "borderColor": "#2563eb",
                        "backgroundColor": "rgba(37, 99, 235, 0.12)",
                        "fill": False,
                        "borderDash": [6, 4],
                        "tension": 0.2,
                        "pointRadius": 3,
                    },
                ],
            },
        }

    @staticmethod
    def _future_dates(date_series: pd.Series) -> list[pd.Timestamp]:
        sorted_dates = pd.to_datetime(date_series, errors="coerce").dropna().sort_values().reset_index(drop=True)
        if len(sorted_dates) < 2:
            return []

        deltas = sorted_dates.diff().dropna()
        positive_deltas = deltas[deltas > pd.Timedelta(0)]
        step = positive_deltas.median() if not positive_deltas.empty else pd.Timedelta(days=1)
        if pd.isna(step) or step <= pd.Timedelta(0):
            step = pd.Timedelta(days=1)

        start = sorted_dates.iloc[-1]
        return [start + step * offset for offset in range(1, Forecasting.FUTURE_STEPS + 1)]

    @staticmethod
    def _preferred_numeric_column(numeric_columns: list[str]) -> str | None:
        preferred_names = ["sales", "revenue", "amount", "profit", "income", "total", "value", "score", "quantity"]
        for preferred_name in preferred_names:
            for column in numeric_columns:
                if preferred_name in column.lower():
                    return column
        return numeric_columns[0] if numeric_columns else None

    @staticmethod
    def _preferred_datetime_column(datetime_columns: list[str]) -> str | None:
        preferred_names = ["date", "time", "month", "year"]
        for preferred_name in preferred_names:
            for column in datetime_columns:
                if preferred_name in column.lower():
                    return column
        return datetime_columns[0] if datetime_columns else None
