from __future__ import annotations

from typing import Any

import pandas as pd


class InsightEngine:
    """Creates simple explanations for the analysis page and report."""

    STATISTIC_EXPLANATIONS = [
        {"term": "Mean", "explanation": "The mean shows the average value of the data."},
        {"term": "Median", "explanation": "The median is the middle value when the values are sorted."},
        {"term": "Mode", "explanation": "The mode is the value that appears most often."},
        {"term": "Minimum", "explanation": "The minimum is the smallest value in the data."},
        {"term": "Maximum", "explanation": "The maximum is the largest value in the data."},
        {"term": "Standard deviation", "explanation": "Standard deviation shows how spread out the values are."},
    ]

    def generate_insights(
        self,
        dataframe: pd.DataFrame,
        column_types: dict[str, list[str]],
        summary: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        summary_data = summary or self._build_summary_data(dataframe, column_types)
        numeric_columns = column_types.get("numeric", [])
        categorical_columns = column_types.get("categorical", [])
        datetime_columns = column_types.get("datetime", [])

        overview = [
            f"The dataset contains {summary_data['rows']:,} rows and {summary_data['columns']:,} columns.",
            f"Numeric columns: {self._format_column_list(numeric_columns)}.",
            f"Categorical columns: {self._format_column_list(categorical_columns)}.",
            f"Date columns: {self._format_column_list(datetime_columns)}.",
        ]

        highlights = self._build_highlights(dataframe, numeric_columns, categorical_columns)
        trends = self._build_trends(dataframe, numeric_columns, datetime_columns)
        relationships = self._build_relationships(dataframe, numeric_columns)
        anomaly_summary = self._build_anomaly_summary(summary_data)

        process_summary = (
            "The system cleaned the dataset, calculated statistics, created simple charts, "
            "checked for anomalies, and prepared explanations to help you understand the data."
        )
        process_steps = [
            f"Duplicate rows removed: {summary_data.get('duplicate_rows_removed', 0):,}.",
            f"Missing values handled: {summary_data.get('missing_values_handled', 0):,}.",
            "Descriptive statistics were calculated for numeric columns.",
            "A small set of charts was generated for quick understanding.",
            "Anomaly detection checked for unusual values outside the normal range.",
        ]

        summary_text = f"This dataset has {summary_data['rows']:,} rows and {summary_data['columns']:,} columns."
        if highlights:
            summary_text = f"{summary_text} {highlights[0]}"

        return {
            "summary": summary_text,
            "overview": overview,
            "highlights": highlights,
            "trends": trends,
            "trend_observations": trends,
            "relationships": relationships,
            "correlations": relationships,
            "anomaly_summary": anomaly_summary,
            "statistical_explanations": self.STATISTIC_EXPLANATIONS,
            "statistics_summary": "The system calculated mean, median, mode, minimum, maximum, and standard deviation for the numeric columns.",
            "process_summary": process_summary,
            "process_steps": process_steps,
        }

    def _build_highlights(
        self,
        dataframe: pd.DataFrame,
        numeric_columns: list[str],
        categorical_columns: list[str],
    ) -> list[str]:
        items: list[str] = []
        metric_column = self._preferred_numeric_column(numeric_columns)
        category_column = self._preferred_categorical_column(dataframe, categorical_columns)

        if metric_column:
            series = pd.to_numeric(dataframe[metric_column], errors="coerce").dropna()
            if not series.empty:
                items.append(f"The main numeric column is {metric_column}, with an average value of {series.mean():,.2f}.")

        if metric_column and category_column:
            grouped = dataframe.groupby(category_column, dropna=False)[metric_column].sum().sort_values(ascending=False)
            if not grouped.empty:
                items.append(
                    f"The top category in {category_column} is {grouped.index[0]} based on total {metric_column}."
                )

        return items

    def _build_trends(
        self,
        dataframe: pd.DataFrame,
        numeric_columns: list[str],
        datetime_columns: list[str],
    ) -> list[str]:
        metric_column = self._preferred_numeric_column(numeric_columns)
        if not metric_column:
            return ["No trend observation is available because the dataset does not contain numeric columns."]

        datetime_column = self._preferred_datetime_column(datetime_columns)
        if not datetime_column:
            return [f"A line chart can still show how {metric_column} changes across the first rows of the dataset."]

        frame = dataframe[[datetime_column, metric_column]].copy()
        frame[datetime_column] = pd.to_datetime(frame[datetime_column], errors="coerce")
        frame[metric_column] = pd.to_numeric(frame[metric_column], errors="coerce")
        frame = frame.dropna(subset=[datetime_column, metric_column]).sort_values(datetime_column)
        if len(frame) < 3:
            return ["There is not enough time-based data to describe a trend clearly."]

        grouped = frame.groupby(frame[datetime_column].dt.to_period("M").astype(str))[metric_column].sum()
        if len(grouped) < 2:
            return ["There is not enough time-based data to describe a trend clearly."]

        start_value = float(grouped.iloc[0])
        end_value = float(grouped.iloc[-1])
        if end_value > start_value:
            return [f"{metric_column} increases over time in the available date data."]
        if end_value < start_value:
            return [f"{metric_column} decreases over time in the available date data."]
        return [f"{metric_column} stays fairly stable over time in the available date data."]

    def _build_relationships(self, dataframe: pd.DataFrame, numeric_columns: list[str]) -> list[str]:
        if len(numeric_columns) < 2:
            return ["No correlation explanation is available because the dataset needs at least two numeric columns."]

        corr_matrix = dataframe[numeric_columns].apply(pd.to_numeric, errors="coerce").corr(numeric_only=True)
        best_pair: tuple[str, str, float] | None = None

        for index, first in enumerate(numeric_columns):
            for second in numeric_columns[index + 1 :]:
                value = corr_matrix.loc[first, second]
                if pd.isna(value):
                    continue
                if best_pair is None or abs(float(value)) > abs(best_pair[2]):
                    best_pair = (first, second, float(value))

        if not best_pair:
            return ["No correlation explanation is available for the numeric columns."]

        first, second, value = best_pair
        direction = "positive" if value >= 0 else "negative"
        return [f"The strongest correlation is between {first} and {second}, and it is {direction} ({value:.2f})."]

    def _build_anomaly_summary(self, summary_data: dict[str, Any]) -> list[str]:
        anomaly_count = int(summary_data.get("anomaly_count", 0))
        anomaly_explanations = summary_data.get("anomaly_explanations", []) or []

        if anomaly_count <= 0:
            return ["No anomalies were detected in the dataset."]

        items = [f"The system detected {anomaly_count:,} anomalous row(s)."]
        for item in anomaly_explanations[:3]:
            explanation = item.get("explanation", "") if isinstance(item, dict) else str(item)
            if explanation:
                items.append(explanation)
        return items

    def _build_summary_data(self, dataframe: pd.DataFrame, column_types: dict[str, list[str]]) -> dict[str, Any]:
        return {
            "rows": len(dataframe),
            "columns": len(dataframe.columns),
            "duplicate_rows_removed": 0,
            "missing_values_handled": 0,
            "anomaly_count": 0,
            "anomaly_explanations": [],
            "column_types": column_types,
        }

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

        for column in categorical_columns:
            unique_count = int(dataframe[column].nunique(dropna=True))
            if 2 <= unique_count <= 12:
                return column
        return categorical_columns[0]

    @staticmethod
    def _preferred_datetime_column(datetime_columns: list[str]) -> str | None:
        preferred_names = ["date", "time", "month", "year"]
        for preferred_name in preferred_names:
            for column in datetime_columns:
                if preferred_name in column.lower():
                    return column
        return datetime_columns[0] if datetime_columns else None

    @staticmethod
    def _format_column_list(columns: list[str]) -> str:
        return ", ".join(columns) if columns else "none"
