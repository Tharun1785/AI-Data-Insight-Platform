from __future__ import annotations

from typing import Any


class ChartExplainer:
    """Builds short beginner-friendly explanations for dashboard charts."""

    def explain(self, chart: dict[str, Any]) -> str:
        chart_type = str(chart.get("type", "")).lower()
        labels = chart.get("labels", []) or []
        values = chart.get("values", []) or []

        if chart_type == "bar":
            return self._bar_explanation(labels, values)
        if chart_type == "line":
            return self._line_explanation(labels, values)
        if chart_type == "pie":
            return self._pie_explanation(labels, values)

        return "This chart highlights a simple pattern in the dataset."

    @staticmethod
    def _bar_explanation(labels: list[Any], values: list[Any]) -> str:
        if labels and values:
            top_index = max(range(len(values)), key=lambda index: float(values[index]))
            return (
                "This chart shows the distribution of values across categories. "
                f"The tallest bar is {labels[top_index]}, which has the highest value."
            )
        return "This chart shows the distribution of values across categories."

    @staticmethod
    def _line_explanation(labels: list[Any], values: list[Any]) -> str:
        if len(values) >= 2:
            first_value = float(values[0])
            last_value = float(values[-1])
            if last_value > first_value:
                trend = "an upward trend, which suggests growth over time"
            elif last_value < first_value:
                trend = "a downward trend, which suggests the value is decreasing over time"
            else:
                trend = "a stable pattern, which suggests little overall change"
            return f"This chart shows how values change over time. It has {trend}."
        return "This chart shows how values change over time."

    @staticmethod
    def _pie_explanation(labels: list[Any], values: list[Any]) -> str:
        if labels and values:
            top_index = max(range(len(values)), key=lambda index: float(values[index]))
            return (
                "This chart shows the percentage contribution of each category. "
                f"The largest slice belongs to {labels[top_index]}."
            )
        return "This chart shows the percentage contribution of each category."
