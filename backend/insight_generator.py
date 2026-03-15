from __future__ import annotations

from typing import Any

import pandas as pd


class InsightGenerator:
    """Generates simple business insights from the processed dataset."""

    def generate(
        self,
        dataframe: pd.DataFrame,
        column_types: dict[str, list[str]],
        anomaly_payload: dict[str, Any] | None = None,
    ) -> list[str]:
        insights: list[str] = []

        numeric_columns = column_types.get("numeric", [])
        categorical_columns = column_types.get("categorical", [])
        datetime_columns = column_types.get("datetime", [])

        top_category = self._top_category_insight(dataframe, categorical_columns, numeric_columns)
        if top_category:
            insights.append(top_category)

        trend = self._trend_insight(dataframe, datetime_columns, numeric_columns)
        if trend:
            insights.append(trend)

        correlation = self._correlation_insight(dataframe, numeric_columns)
        if correlation:
            insights.append(correlation)

        outlier = self._outlier_insight(anomaly_payload)
        if outlier:
            insights.append(outlier)

        high_average = self._high_average_insight(dataframe, numeric_columns)
        if high_average:
            insights.append(high_average)

        cleaned: list[str] = []
        for insight in insights:
            if insight and insight not in cleaned:
                cleaned.append(insight)

        return cleaned[:5] or ["No additional business insights are available for this dataset yet."]

    @staticmethod
    def _preferred_numeric_column(numeric_columns: list[str]) -> str | None:
        preferred_names = ["sales", "revenue", "amount", "profit", "income", "total", "value", "score", "quantity"]
        for preferred_name in preferred_names:
            for column in numeric_columns:
                if preferred_name in column.lower():
                    return column
        return numeric_columns[0] if numeric_columns else None

    @staticmethod
    def _preferred_categorical_column(dataframe: pd.DataFrame, categorical_columns: list[str]) -> str | None:
        if not categorical_columns:
            return None

        preferred_names = ["category", "product", "segment", "type", "branch", "city", "group"]
        for preferred_name in preferred_names:
            for column in categorical_columns:
                if preferred_name in column.lower():
                    return column

        ranked_columns: list[tuple[int, str]] = []
        for column in categorical_columns:
            unique_count = int(dataframe[column].nunique(dropna=True))
            if 2 <= unique_count <= 12:
                ranked_columns.append((unique_count, column))

        if ranked_columns:
            ranked_columns.sort(key=lambda item: item[0])
            return ranked_columns[0][1]
        return categorical_columns[0]

    @staticmethod
    def _preferred_datetime_column(datetime_columns: list[str]) -> str | None:
        preferred_names = ["date", "time", "month", "year"]
        for preferred_name in preferred_names:
            for column in datetime_columns:
                if preferred_name in column.lower():
                    return column
        return datetime_columns[0] if datetime_columns else None

    def _top_category_insight(
        self,
        dataframe: pd.DataFrame,
        categorical_columns: list[str],
        numeric_columns: list[str],
    ) -> str | None:
        category_column = self._preferred_categorical_column(dataframe, categorical_columns)
        metric_column = self._preferred_numeric_column(numeric_columns)
        if not category_column or not metric_column:
            return None

        grouped = dataframe.groupby(category_column, dropna=False)[metric_column].sum().sort_values(ascending=False)
        if grouped.empty:
            return None

        top_label = "Unknown" if pd.isna(grouped.index[0]) else str(grouped.index[0])
        return f"The category '{top_label}' has the highest total {metric_column}."

    def _trend_insight(
        self,
        dataframe: pd.DataFrame,
        datetime_columns: list[str],
        numeric_columns: list[str],
    ) -> str | None:
        datetime_column = self._preferred_datetime_column(datetime_columns)
        metric_column = self._preferred_numeric_column(numeric_columns)
        if not datetime_column or not metric_column:
            return None

        frame = dataframe[[datetime_column, metric_column]].copy()
        frame[datetime_column] = pd.to_datetime(frame[datetime_column], errors="coerce")
        frame[metric_column] = pd.to_numeric(frame[metric_column], errors="coerce")
        frame = frame.dropna(subset=[datetime_column, metric_column]).sort_values(datetime_column)
        if len(frame) < 2:
            return None

        grouped = frame.groupby(frame[datetime_column].dt.to_period("M").astype(str))[metric_column].sum()
        if len(grouped) < 2:
            return None

        first_value = float(grouped.iloc[0])
        last_value = float(grouped.iloc[-1])
        if last_value > first_value:
            return f"{metric_column} shows an increasing trend over time."
        if last_value < first_value:
            return f"{metric_column} shows a decreasing trend over time."
        return f"{metric_column} remains mostly stable over time."

    @staticmethod
    def _correlation_insight(dataframe: pd.DataFrame, numeric_columns: list[str]) -> str | None:
        if len(numeric_columns) < 2:
            return None

        corr_matrix = dataframe[numeric_columns].apply(pd.to_numeric, errors="coerce").corr(numeric_only=True)
        best_pair: tuple[str, str] | None = None
        best_value = 0.0

        for index, first in enumerate(numeric_columns):
            for second in numeric_columns[index + 1 :]:
                value = corr_matrix.loc[first, second]
                if pd.isna(value):
                    continue
                abs_value = abs(float(value))
                if abs_value > best_value:
                    best_value = abs_value
                    best_pair = (first, second)

        if not best_pair:
            return None

        strength = "strong" if best_value >= 0.7 else "moderate" if best_value >= 0.4 else "light"
        return f"The strongest relationship is between {best_pair[0]} and {best_pair[1]}, with a {strength} correlation."

    @staticmethod
    def _outlier_insight(anomaly_payload: dict[str, Any] | None) -> str | None:
        if not anomaly_payload:
            return None

        anomaly_count = int(anomaly_payload.get("anomaly_count", 0))
        records = anomaly_payload.get("anomaly_records", []) or []
        if anomaly_count <= 0 or not records:
            return None

        anomaly_columns: list[str] = []
        for record in records:
            for value in str(record.get("anomaly_columns", "")).split(","):
                cleaned = value.strip()
                if cleaned and cleaned not in anomaly_columns:
                    anomaly_columns.append(cleaned)

        if anomaly_columns:
            return f"Unusual values were detected in the {', '.join(anomaly_columns[:3])} column(s)."
        return f"The system detected {anomaly_count} unusual row(s) in the dataset."

    @staticmethod
    def _high_average_insight(dataframe: pd.DataFrame, numeric_columns: list[str]) -> str | None:
        if not numeric_columns:
            return None

        averages: list[tuple[float, str]] = []
        for column in numeric_columns:
            series = pd.to_numeric(dataframe[column], errors="coerce").dropna()
            if series.empty:
                continue
            averages.append((float(series.mean()), column))

        if not averages:
            return None

        averages.sort(reverse=True)
        average_value, column_name = averages[0]
        return f"{column_name} has the highest average value at {average_value:,.2f}."
