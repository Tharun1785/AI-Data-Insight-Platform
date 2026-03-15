from __future__ import annotations

from io import BytesIO
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd

from backend.chart_explainer import ChartExplainer


class ChartGenerator:
    """Generates a simple set of bar, line, and pie charts."""

    COLORS = ["#111827", "#1f2937", "#374151", "#4b5563", "#6b7280", "#9ca3af", "#d1d5db", "#e5e7eb"]

    def __init__(self) -> None:
        self.chart_explainer = ChartExplainer()

    def generate_chart_configs(self, dataframe: pd.DataFrame, column_types: dict[str, list[str]]) -> dict[str, Any]:
        charts = self._attach_explanations(self._build_chart_specs(dataframe, column_types))
        return {"charts": charts[:3]}

    def generate_report_charts(self, dataframe: pd.DataFrame, column_types: dict[str, list[str]]) -> list[tuple[str, bytes]]:
        charts = self._attach_explanations(self._build_chart_specs(dataframe, column_types))
        report_charts: list[tuple[str, bytes]] = []

        for chart in charts[:3]:
            figure = self._build_matplotlib_chart(chart)
            if figure is None:
                continue
            report_charts.append((chart["title"], self._figure_to_png_bytes(figure)))

        return report_charts

    def _attach_explanations(self, charts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        for chart in charts:
            chart["explanation"] = self.chart_explainer.explain(chart)
        return charts

    def _build_chart_specs(self, dataframe: pd.DataFrame, column_types: dict[str, list[str]]) -> list[dict[str, Any]]:
        numeric_columns = column_types.get("numeric", [])
        categorical_columns = column_types.get("categorical", [])
        datetime_columns = column_types.get("datetime", [])

        charts: list[dict[str, Any]] = []

        bar_chart = self._build_bar_chart(dataframe, categorical_columns, numeric_columns)
        if bar_chart:
            charts.append(bar_chart)

        line_chart = self._build_line_chart(dataframe, datetime_columns, numeric_columns)
        if line_chart:
            charts.append(line_chart)

        pie_chart = self._build_pie_chart(dataframe, categorical_columns, numeric_columns)
        if pie_chart:
            charts.append(pie_chart)

        return charts

    def _build_bar_chart(
        self,
        dataframe: pd.DataFrame,
        categorical_columns: list[str],
        numeric_columns: list[str],
    ) -> dict[str, Any] | None:
        category_column = self._preferred_categorical_column(dataframe, categorical_columns)
        metric_column = self._preferred_numeric_column(numeric_columns)

        if category_column and metric_column:
            grouped = (
                dataframe.groupby(category_column, dropna=False)[metric_column]
                .sum()
                .sort_values(ascending=False)
                .head(8)
            )
            if grouped.empty:
                return None

            labels = ["Unknown" if pd.isna(label) else str(label) for label in grouped.index]
            values = [round(float(value), 2) for value in grouped.values]
            title = f"{metric_column} by {category_column}"
            description = "This bar chart compares the main numeric value across categories."
            dataset_label = metric_column
        elif category_column:
            grouped = dataframe[category_column].fillna("Unknown").astype(str).value_counts().head(8)
            if grouped.empty:
                return None

            labels = grouped.index.astype(str).tolist()
            values = grouped.values.astype(float).tolist()
            title = f"Records by {category_column}"
            description = "This bar chart shows how many records belong to each category."
            dataset_label = "Count"
        elif metric_column:
            series = pd.to_numeric(dataframe[metric_column], errors="coerce").dropna().head(8)
            if series.empty:
                return None

            labels = [f"Row {index + 1}" for index in range(len(series))]
            values = [round(float(value), 2) for value in series.tolist()]
            title = f"{metric_column} by row"
            description = "This bar chart shows the first few values in the main numeric column."
            dataset_label = metric_column
        else:
            return None

        return {
            "type": "bar",
            "title": title,
            "description": description,
            "labels": labels,
            "values": values,
            "chartjs": {
                "labels": labels,
                "datasets": [
                    {
                        "label": dataset_label,
                        "data": values,
                        "backgroundColor": self.COLORS[: len(labels)],
                    }
                ],
            },
        }

    def _build_line_chart(
        self,
        dataframe: pd.DataFrame,
        datetime_columns: list[str],
        numeric_columns: list[str],
    ) -> dict[str, Any] | None:
        metric_column = self._preferred_numeric_column(numeric_columns)
        if not metric_column:
            return None

        datetime_column = self._preferred_datetime_column(datetime_columns)
        if datetime_column:
            line_data = self._time_series_data(dataframe, datetime_column, metric_column)
        else:
            line_data = self._row_series_data(dataframe, metric_column)

        if not line_data:
            return None

        return {
            "type": "line",
            "title": line_data["title"],
            "description": line_data["description"],
            "labels": line_data["labels"],
            "values": line_data["values"],
            "chartjs": {
                "labels": line_data["labels"],
                "datasets": [
                    {
                        "label": metric_column,
                        "data": line_data["values"],
                        "borderColor": "#111827",
                        "backgroundColor": "rgba(17, 24, 39, 0.08)",
                        "fill": True,
                        "tension": 0.2,
                        "pointRadius": 3,
                    }
                ],
            },
        }

    def _build_pie_chart(
        self,
        dataframe: pd.DataFrame,
        categorical_columns: list[str],
        numeric_columns: list[str],
    ) -> dict[str, Any] | None:
        category_column = self._preferred_categorical_column(dataframe, categorical_columns)

        if category_column:
            grouped = dataframe[category_column].fillna("Unknown").astype(str).value_counts().head(6)
            if grouped.empty:
                return None

            labels = grouped.index.astype(str).tolist()
            values = grouped.values.astype(float).tolist()
            title = f"{category_column} distribution"
            description = "This pie chart shows how records are distributed across categories."
            dataset_label = category_column
        else:
            metric_column = self._preferred_numeric_column(numeric_columns)
            if not metric_column:
                return None

            series = pd.to_numeric(dataframe[metric_column], errors="coerce").dropna()
            if series.empty:
                return None

            bins = pd.cut(series, bins=5, include_lowest=True)
            grouped = bins.value_counts().sort_index()
            labels = [str(label) for label in grouped.index]
            values = grouped.values.astype(float).tolist()
            title = f"{metric_column} distribution"
            description = "This pie chart shows how the main numeric values are spread across ranges."
            dataset_label = metric_column

        return {
            "type": "pie",
            "title": title,
            "description": description,
            "labels": labels,
            "values": values,
            "chartjs": {
                "labels": labels,
                "datasets": [
                    {
                        "label": dataset_label,
                        "data": values,
                        "backgroundColor": self.COLORS[: len(labels)],
                        "borderColor": "#ffffff",
                        "borderWidth": 1,
                    }
                ],
            },
        }

    def _time_series_data(self, dataframe: pd.DataFrame, datetime_column: str, metric_column: str) -> dict[str, Any] | None:
        frame = dataframe[[datetime_column, metric_column]].copy()
        frame[datetime_column] = pd.to_datetime(frame[datetime_column], errors="coerce")
        frame[metric_column] = pd.to_numeric(frame[metric_column], errors="coerce")
        frame = frame.dropna(subset=[datetime_column, metric_column]).sort_values(datetime_column)
        if frame.empty:
            return None

        grouped = frame.groupby(frame[datetime_column].dt.to_period("M").astype(str))[metric_column].sum().head(12)
        if grouped.empty:
            return None

        return {
            "title": f"{metric_column} over time",
            "description": "This line chart shows how the main numeric value changes over time.",
            "labels": grouped.index.astype(str).tolist(),
            "values": [round(float(value), 2) for value in grouped.values],
        }

    def _row_series_data(self, dataframe: pd.DataFrame, metric_column: str) -> dict[str, Any] | None:
        series = pd.to_numeric(dataframe[metric_column], errors="coerce").dropna().head(12)
        if series.empty:
            return None

        return {
            "title": f"{metric_column} by row order",
            "description": "This line chart shows the first values in the main numeric column.",
            "labels": [f"Row {index + 1}" for index in range(len(series))],
            "values": [round(float(value), 2) for value in series.tolist()],
        }

    def _build_matplotlib_chart(self, chart: dict[str, Any]):
        chart_type = chart.get("type")
        labels = chart.get("labels", [])
        values = chart.get("values", [])
        title = chart.get("title", "Chart")

        if not labels or not values:
            return None

        if chart_type == "bar":
            figure, axis = plt.subplots(figsize=(8, 4.5))
            axis.bar(labels, values, color="#111827")
            axis.set_title(title)
            axis.tick_params(axis="x", rotation=20)
            axis.grid(axis="y", alpha=0.2)
            return figure

        if chart_type == "line":
            figure, axis = plt.subplots(figsize=(8, 4.5))
            axis.plot(labels, values, color="#111827", marker="o", linewidth=2)
            axis.set_title(title)
            axis.tick_params(axis="x", rotation=20)
            axis.grid(axis="y", alpha=0.2)
            return figure

        if chart_type == "pie":
            figure, axis = plt.subplots(figsize=(7, 5))
            axis.pie(
                values,
                labels=labels,
                autopct="%1.0f%%",
                startangle=120,
                colors=self.COLORS[: len(labels)],
                wedgeprops={"linewidth": 1, "edgecolor": "white"},
            )
            axis.set_title(title)
            return figure

        return None

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

    @staticmethod
    def _figure_to_png_bytes(figure: plt.Figure) -> bytes:
        buffer = BytesIO()
        figure.tight_layout()
        figure.savefig(buffer, format="png", dpi=150, bbox_inches="tight")
        plt.close(figure)
        buffer.seek(0)
        return buffer.read()
