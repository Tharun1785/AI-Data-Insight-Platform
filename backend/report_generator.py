from __future__ import annotations

from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from backend.chart_generator import ChartGenerator


class ReportGenerator:
    """Creates a simple professional PDF analytics report."""

    def __init__(self) -> None:
        self.chart_generator = ChartGenerator()

    def build_report(
        self,
        output_path: Path,
        summary: dict[str, Any],
        insights_data: dict[str, Any],
        dataframe: pd.DataFrame,
        column_types: dict[str, list[str]],
    ) -> None:
        document = SimpleDocTemplate(
            str(output_path),
            pagesize=A4,
            rightMargin=32,
            leftMargin=32,
            topMargin=36,
            bottomMargin=34,
        )
        styles = self._build_styles()
        story: list[Any] = []

        self._append_title_page(story, styles, summary)
        self._append_dataset_overview(story, styles, summary)
        self._append_statistical_analysis(story, styles, summary, insights_data)
        self._append_charts(story, styles, dataframe, column_types)
        self._append_data_explanations(story, styles, insights_data)
        self._append_ai_insights(story, styles, insights_data)
        self._append_anomaly_explanations(story, styles, summary)
        self._append_correlation_analysis(story, styles, dataframe, column_types)
        self._append_business_recommendations(story, styles, dataframe, column_types, summary, insights_data)
        self._append_future_enhancements(story, styles)

        document.build(story, onFirstPage=self._decorate_page, onLaterPages=self._decorate_page)

    def _build_styles(self) -> dict[str, ParagraphStyle]:
        base = getSampleStyleSheet()
        return {
            "title": ParagraphStyle(
                "TitleStyle",
                parent=base["Title"],
                fontName="Helvetica-Bold",
                fontSize=26,
                leading=32,
                alignment=TA_CENTER,
                textColor=colors.HexColor("#0f172a"),
                spaceAfter=12,
            ),
            "subtitle": ParagraphStyle(
                "SubtitleStyle",
                parent=base["Heading2"],
                fontName="Helvetica",
                fontSize=12,
                leading=16,
                alignment=TA_CENTER,
                textColor=colors.HexColor("#475569"),
                spaceAfter=8,
            ),
            "section": ParagraphStyle(
                "SectionStyle",
                parent=base["Heading2"],
                fontName="Helvetica-Bold",
                fontSize=16,
                leading=20,
                textColor=colors.HexColor("#1d4ed8"),
                spaceBefore=4,
                spaceAfter=10,
            ),
            "body": ParagraphStyle(
                "BodyStyle",
                parent=base["BodyText"],
                fontName="Helvetica",
                fontSize=10,
                leading=15,
                textColor=colors.HexColor("#334155"),
                spaceAfter=8,
            ),
            "caption": ParagraphStyle(
                "CaptionStyle",
                parent=base["BodyText"],
                fontName="Helvetica-Bold",
                fontSize=11,
                leading=14,
                textColor=colors.HexColor("#0f172a"),
                spaceAfter=6,
            ),
            "bullet": ParagraphStyle(
                "BulletStyle",
                parent=base["BodyText"],
                fontName="Helvetica",
                fontSize=10,
                leading=15,
                leftIndent=12,
                textColor=colors.HexColor("#334155"),
                spaceAfter=5,
            ),
            "small": ParagraphStyle(
                "SmallStyle",
                parent=base["BodyText"],
                fontName="Helvetica",
                fontSize=9,
                leading=13,
                alignment=TA_CENTER,
                textColor=colors.HexColor("#64748b"),
                spaceAfter=4,
            ),
        }

    def _append_title_page(self, story: list[Any], styles: dict[str, ParagraphStyle], summary: dict[str, Any]) -> None:
        generated_at = datetime.now().strftime("%B %d, %Y %I:%M %p")
        story.append(Spacer(1, 1.2 * inch))
        story.append(Paragraph("AI Data Insight Platform Report", styles["title"]))
        story.append(Paragraph(summary.get("dataset_name") or "Uploaded dataset", styles["subtitle"]))
        story.append(Paragraph(f"Generated on {generated_at}", styles["small"]))
        story.append(Spacer(1, 0.3 * inch))

        overview_rows = [
            ["Rows", f"{summary['rows']:,}"],
            ["Columns", f"{summary['columns']:,}"],
            ["Missing values handled", f"{summary.get('missing_values_handled', 0):,}"],
            ["Duplicate rows removed", f"{summary.get('duplicate_rows_removed', 0):,}"],
            ["Anomalies detected", f"{summary.get('anomaly_count', 0):,}"],
        ]
        story.append(self._styled_table(overview_rows, [2.5 * inch, 2.5 * inch]))
        story.append(Spacer(1, 0.3 * inch))
        story.append(
            Paragraph(
                "This report includes dataset structure, statistical analysis, charts, explanations, AI insights, anomaly explanations, and correlation analysis.",
                styles["body"],
            )
        )
        story.append(PageBreak())
    def _append_dataset_overview(self, story: list[Any], styles: dict[str, ParagraphStyle], summary: dict[str, Any]) -> None:
        story.append(Paragraph("1. Dataset Overview", styles["section"]))
        story.append(
            Paragraph(
                "This section describes the uploaded data after cleaning and preparation.",
                styles["body"],
            )
        )

        rows = [
            ["Dataset name", summary.get("dataset_name") or "Uploaded dataset"],
            ["Rows", f"{summary['rows']:,}"],
            ["Columns", f"{summary['columns']:,}"],
            ["Numeric columns", ", ".join(summary["column_types"]["numeric"]) or "none"],
            ["Categorical columns", ", ".join(summary["column_types"]["categorical"]) or "none"],
            ["Date columns", ", ".join(summary["column_types"]["datetime"]) or "none"],
            ["Anomaly count", f"{summary.get('anomaly_count', 0):,}"],
        ]
        story.append(self._styled_table(rows, [2.1 * inch, 4.9 * inch]))
        story.append(Spacer(1, 0.15 * inch))

        story.append(Paragraph("Business Context of the Dataset", styles["caption"]))
        story.append(
            Paragraph(
                "This dataset can be interpreted as structured transactional sales data that helps explain how customers buy products, how revenue is distributed, and where commercial performance is strongest.",
                styles["body"],
            )
        )
        for item in [
            "Customer purchasing patterns show which customers, channels, or segments contribute most to sales activity.",
            "Product category performance highlights which product groups generate the strongest revenue and demand.",
            "Pricing influence on revenue helps teams understand how unit price and sales values work together.",
            "Regional sales performance helps compare branches, cities, or business areas when location columns are available.",
        ]:
            story.append(Paragraph(item, styles["bullet"], bulletText="-"))
        story.append(
            Paragraph(
                "Analyzing this kind of dataset helps businesses improve inventory planning, refine pricing strategy, and make better marketing decisions based on real transaction behavior.",
                styles["body"],
            )
        )
        story.append(PageBreak())

    def _append_statistical_analysis(
        self,
        story: list[Any],
        styles: dict[str, ParagraphStyle],
        summary: dict[str, Any],
        insights_data: dict[str, Any],
    ) -> None:
        story.append(Paragraph("2. Statistical Analysis", styles["section"]))
        story.append(
            Paragraph(
                "The table below shows the main numeric statistics in simple form.",
                styles["body"],
            )
        )

        stats = summary.get("statistics", {})
        if stats:
            rows = [["Column", "Mean", "Median", "Mode", "Min", "Max", "Std Dev"]]
            for column, values in list(stats.items())[:10]:
                rows.append(
                    [
                        column,
                        str(values["mean"]),
                        str(values["median"]),
                        str(values["mode"]),
                        str(values["min"]),
                        str(values["max"]),
                        str(values["std"]),
                    ]
                )
            story.append(
                self._styled_table(
                    rows,
                    [1.55 * inch, 0.82 * inch, 0.82 * inch, 0.82 * inch, 0.82 * inch, 0.82 * inch, 0.82 * inch],
                    header=True,
                    font_size=8,
                )
            )
            story.append(Spacer(1, 0.18 * inch))
        else:
            story.append(Paragraph("No numeric columns were available for statistical analysis.", styles["body"]))

        story.append(Paragraph("What these values mean", styles["caption"]))
        for item in insights_data.get("statistical_explanations", []):
            story.append(Paragraph(f"{item['term']}: {item['explanation']}", styles["bullet"], bulletText="-"))

        story.append(Paragraph("Business Interpretation of Statistics", styles["caption"]))
        for item in self._statistical_business_interpretation(summary):
            story.append(Paragraph(item, styles["bullet"], bulletText="-"))
        story.append(PageBreak())
    def _append_charts(
        self,
        story: list[Any],
        styles: dict[str, ParagraphStyle],
        dataframe: pd.DataFrame,
        column_types: dict[str, list[str]],
    ) -> None:
        story.append(Paragraph("3. Charts", styles["section"]))
        story.append(
            Paragraph(
                "These charts were created automatically to show the most useful patterns in the dataset.",
                styles["body"],
            )
        )

        chart_payload = self.chart_generator.generate_chart_configs(dataframe, column_types)
        charts = chart_payload.get("charts", [])
        if not charts:
            story.append(Paragraph("No charts could be generated for this dataset.", styles["body"]))
            story.append(PageBreak())
            return

        for chart in charts:
            figure = self.chart_generator._build_matplotlib_chart(chart)
            if figure is None:
                continue

            story.append(Paragraph(chart.get("title", "Chart"), styles["caption"]))
            story.append(Image(BytesIO(self._figure_to_png_bytes(figure)), width=6.6 * inch, height=3.7 * inch))
            story.append(Spacer(1, 0.08 * inch))
            story.append(Paragraph("Chart Interpretation", styles["caption"]))
            story.append(Paragraph(chart.get("explanation", "This chart highlights an important pattern in the data."), styles["body"]))
            story.append(Paragraph(self._chart_business_interpretation(chart), styles["body"]))
            story.append(Spacer(1, 0.18 * inch))

        story.append(PageBreak())

    def _append_data_explanations(
        self,
        story: list[Any],
        styles: dict[str, ParagraphStyle],
        insights_data: dict[str, Any],
    ) -> None:
        story.append(Paragraph("4. Data Explanations", styles["section"]))
        story.append(Paragraph(insights_data.get("process_summary", "No processing explanation available."), styles["body"]))

        story.append(Paragraph("Data Processing Details", styles["caption"]))
        for step in insights_data.get("process_steps", []):
            story.append(Paragraph(step, styles["bullet"], bulletText="-"))
        for item in [
            "Missing value handling reduces the risk of blank cells distorting averages, totals, and trend calculations.",
            "Duplicate removal prevents the same transaction or record from being counted more than once in charts and statistics.",
            "Dataset cleaning standardizes data types and structure so values are easier to compare consistently across the report.",
            "Anomaly detection looks for unusual values that may represent exceptional transactions, errors, or rare business events.",
        ]:
            story.append(Paragraph(item, styles["bullet"], bulletText="-"))
        story.append(
            Paragraph(
                "Together, these preprocessing steps improve the reliability and accuracy of the analysis so business users can trust the reported findings.",
                styles["body"],
            )
        )
        story.append(PageBreak())

    def _append_ai_insights(
        self,
        story: list[Any],
        styles: dict[str, ParagraphStyle],
        insights_data: dict[str, Any],
    ) -> None:
        story.append(Paragraph("5. AI Insights", styles["section"]))
        story.append(Paragraph(insights_data.get("summary", "No AI summary available."), styles["body"]))
        story.append(
            Paragraph(
                "The following insights translate the raw numbers into practical business meaning so non-technical users can quickly understand where attention is needed.",
                styles["body"],
            )
        )

        groups = [
            ("Highlights", insights_data.get("highlights", []), "These highlight the most important performance patterns discovered in the dataset."),
            ("Trend Analysis", insights_data.get("trends", []), "These observations explain how values change over time and why the direction matters to planning."),
            ("Relationship Insights", insights_data.get("relationships", []), "These observations explain how variables move together and how one measure may influence another."),
        ]
        for title, items, intro in groups:
            story.append(Paragraph(title, styles["caption"]))
            story.append(Paragraph(intro, styles["body"]))
            if items:
                for item in items:
                    story.append(Paragraph(item, styles["bullet"], bulletText="-"))
            else:
                story.append(Paragraph("No items available in this section.", styles["body"]))
        story.append(PageBreak())
    def _append_anomaly_explanations(
        self,
        story: list[Any],
        styles: dict[str, ParagraphStyle],
        summary: dict[str, Any],
    ) -> None:
        story.append(Paragraph("6. Anomaly Explanations", styles["section"]))
        anomaly_explanations = summary.get("anomaly_explanations", []) or []
        anomaly_count = int(summary.get("anomaly_count", 0))

        if anomaly_count <= 0 or not anomaly_explanations:
            story.append(Paragraph("No anomalies were detected using the IQR method.", styles["body"]))
        else:
            story.append(
                Paragraph(
                    f"The system detected {anomaly_count} anomalous row(s). The explanations below describe why these values stand out.",
                    styles["body"],
                )
            )

            rows = [["Row", "Column", "Value"]]
            for item in anomaly_explanations[:10]:
                rows.append([
                    str(item.get("row", "-")),
                    str(item.get("column", "-")),
                    str(item.get("value", "-")),
                ])
            story.append(self._styled_table(rows, [1.0 * inch, 2.2 * inch, 2.8 * inch], header=True))
            story.append(Spacer(1, 0.18 * inch))

            story.append(Paragraph("Plain-language explanations", styles["caption"]))
            for item in anomaly_explanations[:12]:
                story.append(Paragraph(item.get("explanation", ""), styles["bullet"], bulletText="-"))

            if len(anomaly_explanations) > 12:
                story.append(
                    Paragraph(
                        f"Only the first 12 anomaly explanations are shown in this report. {len(anomaly_explanations) - 12} additional explanations were omitted for brevity.",
                        styles["body"],
                    )
                )

        story.append(Paragraph("Business Importance of Anomaly Detection", styles["caption"]))
        for item in [
            "Anomalies may represent unusually large transactions that deserve closer operational review.",
            "They can also indicate potential pricing errors, data entry problems, or unusual customer behavior.",
            "In some businesses, anomaly detection helps flag possible fraud or activity that falls outside expected norms.",
            "Monitoring anomalies supports stronger controls, faster investigation, and better data quality over time.",
        ]:
            story.append(Paragraph(item, styles["bullet"], bulletText="-"))
        story.append(PageBreak())

    def _append_correlation_analysis(
        self,
        story: list[Any],
        styles: dict[str, ParagraphStyle],
        dataframe: pd.DataFrame,
        column_types: dict[str, list[str]],
    ) -> None:
        story.append(Paragraph("7. Correlation Analysis", styles["section"]))
        numeric_columns = column_types.get("numeric", [])
        if len(numeric_columns) < 2:
            story.append(Paragraph("At least two numeric columns are needed for correlation analysis.", styles["body"]))
            story.append(PageBreak())
            return

        corr_matrix = dataframe[numeric_columns].apply(pd.to_numeric, errors="coerce").corr(numeric_only=True)
        pairs = self._top_correlation_pairs(corr_matrix)

        if pairs:
            rows = [["Column 1", "Column 2", "Correlation"]]
            for first, second, value in pairs[:8]:
                rows.append([first, second, f"{value:.2f}"])
            story.append(self._styled_table(rows, [2.25 * inch, 2.25 * inch, 1.1 * inch], header=True))
            story.append(Spacer(1, 0.18 * inch))

        heatmap = self._correlation_heatmap_png(corr_matrix)
        if heatmap:
            story.append(Paragraph("Correlation Heatmap", styles["caption"]))
            story.append(Image(BytesIO(heatmap), width=6.5 * inch, height=4.1 * inch))
            story.append(Spacer(1, 0.18 * inch))

        story.append(Paragraph("Business Meaning of Correlations", styles["caption"]))
        for item in self._correlation_business_meaning(pairs):
            story.append(Paragraph(item, styles["bullet"], bulletText="-"))
        story.append(PageBreak())
    def _append_business_recommendations(
        self,
        story: list[Any],
        styles: dict[str, ParagraphStyle],
        dataframe: pd.DataFrame,
        column_types: dict[str, list[str]],
        summary: dict[str, Any],
        insights_data: dict[str, Any],
    ) -> None:
        story.append(Paragraph("8. Business Recommendations", styles["section"]))
        story.append(
            Paragraph(
                "The suggestions below translate the analysis into practical actions that business teams can use for planning, monitoring, and growth.",
                styles["body"],
            )
        )
        for item in self._business_recommendations(dataframe, column_types, summary, insights_data):
            story.append(Paragraph(item, styles["bullet"], bulletText="-"))
        story.append(PageBreak())

    def _append_future_enhancements(self, story: list[Any], styles: dict[str, ParagraphStyle]) -> None:
        story.append(Paragraph("9. Future Enhancements", styles["section"]))
        story.append(
            Paragraph(
                "Future versions of the AI Data Insight Platform can expand from descriptive reporting into more advanced decision support and predictive analytics.",
                styles["body"],
            )
        )
        for item in [
            "Predictive sales forecasting could estimate future demand and support more accurate planning.",
            "Customer segmentation analysis could group buyers by behavior, value, or purchasing preferences.",
            "Real-time monitoring dashboards could alert teams quickly when performance changes or anomalies appear.",
            "Advanced machine learning models for demand prediction could improve replenishment, pricing, and promotional decisions.",
        ]:
            story.append(Paragraph(item, styles["bullet"], bulletText="-"))
        story.append(
            Paragraph(
                "These improvements would help businesses move further toward data-driven decision making and faster operational response.",
                styles["body"],
            )
        )

    def _statistical_business_interpretation(self, summary: dict[str, Any]) -> list[str]:
        items = [
            "Mean represents the typical value in the dataset and helps estimate normal business performance.",
            "Median helps describe central tendency without being overly influenced by extreme values or outlier transactions.",
            "Standard deviation indicates how much pricing or sales values vary, which helps identify stable versus volatile performance.",
            "Higher variation in pricing may indicate different product segments such as budget products and premium products.",
            "Businesses can use these statistics to understand pricing distribution, customer demand patterns, and the spread of transaction values.",
        ]

        stats = summary.get("statistics", {}) or {}
        if stats:
            highest_variation = max(
                stats.items(),
                key=lambda item: float(item[1].get("std", 0) or 0),
            )
            items.append(
                f"The highest observed variability appears in {highest_variation[0]}, which suggests this metric should be monitored closely for planning and forecasting."
            )
        return items

    def _chart_business_interpretation(self, chart: dict[str, Any]) -> str:
        chart_type = str(chart.get("type", "")).lower()
        labels = chart.get("labels", []) or []
        values = [float(value) for value in (chart.get("values", []) or []) if value is not None]
        if not labels or not values:
            return "This visualization provides a quick view of the data and helps decision makers identify where to investigate next."

        top_index = max(range(len(values)), key=lambda index: values[index])
        top_label = str(labels[top_index])
        title = str(chart.get("title", "Chart"))

        if chart_type == "bar":
            metric, dimension = self._split_chart_title(title, " by ")
            metric_name = metric or "the measured value"
            dimension_name = dimension or "the business category"
            return (
                f"{top_label} generates the highest {metric_name}, which suggests that {dimension_name.lower()} deserves close attention for inventory planning, sales focus, and marketing investment."
            )

        if chart_type == "line":
            first_value = values[0]
            last_value = values[-1]
            if last_value > first_value:
                trend_text = "is increasing, which may reflect growth in demand or stronger recent performance"
            elif last_value < first_value:
                trend_text = "is decreasing, which may point to seasonality, weaker demand, or the need for corrective action"
            else:
                trend_text = "is stable, which may indicate predictable and consistent performance"
            metric_name = title.replace(" over time", "")
            return f"The {metric_name} trend {trend_text}. Businesses can use this pattern to plan stock, promotions, and timing of campaigns."

        if chart_type == "pie":
            total = sum(values) or 1.0
            share = (values[top_index] / total) * 100
            category_name = title.replace(" distribution", "")
            return (
                f"{top_label} represents the largest share of {category_name.lower()} at about {share:.1f}%. This helps businesses decide whether to strengthen a leading segment or diversify support across smaller categories."
            )

        return "This visualization provides a quick view of the data and helps decision makers identify where to investigate next."
    def _correlation_business_meaning(self, pairs: list[tuple[str, str, float]]) -> list[str]:
        items = [
            "Strong correlations help businesses understand which variables move together and which measures should be monitored as a group.",
            "These relationships can support pricing decisions, promotional planning, and performance management.",
        ]

        if pairs:
            first, second, value = pairs[0]
            strength = "strong" if abs(value) >= 0.7 else "moderate" if abs(value) >= 0.4 else "light"
            implication = self._correlation_implication(first, second)
            items.append(
                f"The {strength} correlation between {first} and {second} suggests that {implication}"
            )
        return items

    def _business_recommendations(
        self,
        dataframe: pd.DataFrame,
        column_types: dict[str, list[str]],
        summary: dict[str, Any],
        insights_data: dict[str, Any],
    ) -> list[str]:
        recommendations: list[str] = []

        top_category_recommendation = self._top_category_recommendation(dataframe, column_types)
        if top_category_recommendation:
            recommendations.append(top_category_recommendation)

        recommendations.extend(self._trend_recommendations(insights_data))

        if int(summary.get("anomaly_count", 0)) > 0:
            recommendations.append("Investigate anomaly transactions to confirm whether they represent legitimate high-value sales, pricing issues, or unusual activity that needs control review.")

        recommendations.extend(self._relationship_recommendations(insights_data))
        recommendations.append("Use forecasting for future planning so teams can prepare inventory, staffing, and marketing activity before demand changes occur.")

        unique_recommendations: list[str] = []
        for item in recommendations:
            if item and item not in unique_recommendations:
                unique_recommendations.append(item)
        return unique_recommendations[:6]

    def _top_category_recommendation(self, dataframe: pd.DataFrame, column_types: dict[str, list[str]]) -> str | None:
        numeric_columns = column_types.get("numeric", [])
        categorical_columns = column_types.get("categorical", [])
        category_column = self.chart_generator._preferred_categorical_column(dataframe, categorical_columns)
        metric_column = self.chart_generator._preferred_numeric_column(numeric_columns)
        if not category_column or not metric_column:
            return None

        grouped = dataframe.groupby(category_column, dropna=False)[metric_column].sum().sort_values(ascending=False)
        if grouped.empty:
            return None

        label = str(grouped.index[0])
        return f"Focus marketing, inventory, and promotional effort on {label}, because it is currently the highest-performing category by total {metric_column}."

    @staticmethod
    def _trend_recommendations(insights_data: dict[str, Any]) -> list[str]:
        items: list[str] = []
        for trend in insights_data.get("trends", []) or []:
            lowered = str(trend).lower()
            if "increase" in lowered:
                items.append("Analyze the factors behind the upward trend and make sure inventory and operations can support continued growth.")
            elif "decrease" in lowered:
                items.append("Investigate seasonal patterns, pricing decisions, and customer demand drivers to understand the declining trend and respond early.")
            elif "stable" in lowered:
                items.append("Use the stable pattern as a planning baseline and test targeted campaigns to improve performance without disrupting consistency.")
        items.append("Analyze seasonal sales patterns over time to improve timing for campaigns, discounts, and stock replenishment.")
        return items

    @staticmethod
    def _relationship_recommendations(insights_data: dict[str, Any]) -> list[str]:
        items: list[str] = []
        for relationship in insights_data.get("relationships", []) or []:
            lowered = str(relationship).lower()
            if "correlation" in lowered:
                items.append("Monitor strongly related variables together so pricing models and promotional strategies are based on how business measures influence one another.")
                break
        return items

    @staticmethod
    def _split_chart_title(title: str, separator: str) -> tuple[str | None, str | None]:
        if separator not in title:
            return None, None
        left, right = title.split(separator, 1)
        return left.strip(), right.strip()

    @staticmethod
    def _correlation_implication(first: str, second: str) -> str:
        combined = f"{first} {second}".lower()
        if ("price" in combined or "unit price" in combined) and ("sales" in combined or "revenue" in combined):
            return "pricing strategies directly influence revenue performance, so pricing decisions should be reviewed carefully."
        if ("quantity" in combined or "units" in combined) and ("sales" in combined or "revenue" in combined):
            return "sales performance is closely linked to transaction volume, so demand planning and stock management matter."
        if "tax" in combined and ("sales" in combined or "income" in combined):
            return "changes in transaction value directly affect related financial measures, which is useful for financial monitoring."
        return "changes in one variable are closely linked to the other, which helps teams design pricing, monitoring, and planning strategies."

    def _correlation_heatmap_png(self, corr_matrix: pd.DataFrame) -> bytes | None:
        if corr_matrix.empty:
            return None

        figure, axis = plt.subplots(figsize=(7.6, 4.9))
        image = axis.imshow(corr_matrix.values, cmap="Blues", vmin=-1, vmax=1)
        axis.set_xticks(range(len(corr_matrix.columns)))
        axis.set_yticks(range(len(corr_matrix.index)))
        axis.set_xticklabels(corr_matrix.columns, rotation=30, ha="right")
        axis.set_yticklabels(corr_matrix.index)
        axis.set_title("Correlation Heatmap")

        for row in range(len(corr_matrix.index)):
            for column in range(len(corr_matrix.columns)):
                axis.text(column, row, f"{corr_matrix.iloc[row, column]:.2f}", ha="center", va="center", fontsize=8)

        figure.colorbar(image, ax=axis, fraction=0.046, pad=0.04)
        return self._figure_to_png_bytes(figure)

    @staticmethod
    def _top_correlation_pairs(corr_matrix: pd.DataFrame) -> list[tuple[str, str, float]]:
        pairs: list[tuple[str, str, float]] = []
        for index, first in enumerate(corr_matrix.columns):
            for second in corr_matrix.columns[index + 1 :]:
                value = corr_matrix.loc[first, second]
                if pd.isna(value):
                    continue
                pairs.append((first, second, float(value)))
        pairs.sort(key=lambda item: abs(item[2]), reverse=True)
        return pairs

    def _styled_table(
        self,
        rows: list[list[str]],
        col_widths: list[float],
        *,
        header: bool = False,
        font_size: int = 9,
    ) -> Table:
        table = Table(rows, colWidths=col_widths, repeatRows=1 if header else 0)
        commands = [
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#e2e8f0")),
            ("BACKGROUND", (0, 0), (-1, -1), colors.white),
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#0f172a")),
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), font_size),
            ("LEADING", (0, 0), (-1, -1), font_size + 2),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]
        if header:
            commands.extend(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dbeafe")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1e3a8a")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ]
            )
        else:
            commands.append(("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]))
        table.setStyle(TableStyle(commands))
        return table

    @staticmethod
    def _decorate_page(canvas, document) -> None:
        canvas.saveState()
        width, height = A4
        canvas.setFillColor(colors.HexColor("#eff6ff"))
        canvas.rect(0, height - 24, width, 24, fill=1, stroke=0)
        canvas.setFillColor(colors.HexColor("#1d4ed8"))
        canvas.setFont("Helvetica-Bold", 9)
        canvas.drawString(32, height - 16, "AI Data Insight Platform Report")
        canvas.setFillColor(colors.HexColor("#64748b"))
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(width - 32, 18, f"Page {canvas.getPageNumber()}")
        canvas.restoreState()

    @staticmethod
    def _figure_to_png_bytes(figure: plt.Figure) -> bytes:
        buffer = BytesIO()
        figure.tight_layout()
        figure.savefig(buffer, format="png", dpi=150, bbox_inches="tight")
        plt.close(figure)
        buffer.seek(0)
        return buffer.read()
