from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pandas as pd

from backend.anomaly_detector import AnomalyDetector
from backend.anomaly_explainer import AnomalyExplainer


class DatasetChatbot:
    """Answers simple questions about the currently uploaded dataset."""

    COLUMN_ALIASES = {
        "sales": ["sales", "revenue", "income", "amount", "value", "total sales"],
        "quantity": ["quantity", "qty", "units", "items"],
        "profit": ["profit", "gross income", "earnings"],
        "category": ["category", "product line", "segment", "type", "group"],
        "date": ["date", "time", "month", "year", "day"],
    }

    def __init__(self) -> None:
        self.anomaly_detector = AnomalyDetector()
        self.anomaly_explainer = AnomalyExplainer()

    def answer(self, question: str, datasets_dir: str | Path) -> dict[str, Any]:
        normalized_question = question.strip()
        if not normalized_question:
            return {"answer": "Please ask a question about the uploaded dataset."}

        try:
            dataframe, dataset_path = self._load_current_dataset(datasets_dir)
        except ValueError as exc:
            return {"answer": str(exc)}

        return self.answer_from_dataframe(normalized_question, dataframe, dataset_path.name)

    def answer_from_dataframe(
        self,
        question: str,
        dataframe: pd.DataFrame,
        dataset_name: str,
        anomaly_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        normalized_question = question.strip()
        if not normalized_question:
            return {"answer": "Please ask a question about the uploaded dataset."}

        prepared_dataframe = self._prepare_dataframe(dataframe)
        numeric_columns, categorical_columns, datetime_columns = self._get_column_types(prepared_dataframe)
        lowered = normalized_question.lower()

        if self._is_system_question(lowered):
            return {"answer": self._system_explanation()}

        if self._is_anomaly_question(lowered):
            return {"answer": self._anomaly_answer(prepared_dataframe, anomaly_payload)}

        if self._is_numeric_columns_question(lowered):
            columns = ", ".join(numeric_columns) if numeric_columns else "none"
            return {"answer": f"The numeric columns are: {columns}."}

        if self._is_categorical_columns_question(lowered):
            columns = ", ".join(categorical_columns) if categorical_columns else "none"
            return {"answer": f"The categorical columns are: {columns}."}

        if self._is_top_records_question(lowered):
            return {"answer": self._top_records_answer(prepared_dataframe)}

        if self._is_summary_question(lowered):
            return {"answer": self._dataset_summary_answer(prepared_dataframe, dataset_name, numeric_columns, categorical_columns, datetime_columns)}

        if self._is_row_count_question(lowered):
            return {"answer": f"The dataset contains {len(prepared_dataframe):,} rows."}

        if self._is_correlation_question(lowered):
            return {"answer": self._correlation_answer(lowered, prepared_dataframe, numeric_columns)}

        if self._is_most_common_category_question(lowered):
            return {"answer": self._most_common_category_answer(prepared_dataframe, categorical_columns)}

        if self._is_top_category_by_value_question(lowered):
            return {"answer": self._top_category_by_value_answer(lowered, prepared_dataframe, numeric_columns, categorical_columns)}

        operation = self._detect_numeric_operation(lowered)
        if operation:
            return {"answer": self._numeric_operation_answer(operation, lowered, prepared_dataframe, numeric_columns)}

        return {
            "answer": (
                "I can answer questions about averages, maximums, minimums, totals, row counts, top categories, "
                "correlations, top records, anomalies, column types, dataset summaries, and how the system works."
            )
        }

    def _load_current_dataset(self, datasets_dir: str | Path) -> tuple[pd.DataFrame, Path]:
        dataset_root = Path(datasets_dir)
        files = [path for path in dataset_root.iterdir() if path.is_file() and path.suffix.lower() in {".csv", ".xlsx"}]
        if not files:
            raise ValueError("No dataset found in the datasets folder. Please upload a dataset first.")

        latest_file = max(files, key=lambda path: path.stat().st_mtime)
        if latest_file.suffix.lower() == ".csv":
            dataframe = pd.read_csv(latest_file)
        else:
            dataframe = pd.read_excel(latest_file)
        return dataframe, latest_file

    @staticmethod
    def _prepare_dataframe(dataframe: pd.DataFrame) -> pd.DataFrame:
        df = dataframe.copy()
        df.columns = [str(column).strip() for column in df.columns]
        return df.drop_duplicates().reset_index(drop=True)

    @staticmethod
    def _get_column_types(dataframe: pd.DataFrame) -> tuple[list[str], list[str], list[str]]:
        numeric_columns = dataframe.select_dtypes(include="number").columns.tolist()
        datetime_columns = [
            column for column in dataframe.columns if pd.api.types.is_datetime64_any_dtype(dataframe[column])
        ]
        categorical_columns = [
            column for column in dataframe.columns if column not in numeric_columns and column not in datetime_columns
        ]
        return numeric_columns, categorical_columns, datetime_columns

    def _numeric_operation_answer(
        self,
        operation: str,
        question: str,
        dataframe: pd.DataFrame,
        numeric_columns: list[str],
    ) -> str:
        if not numeric_columns:
            return "I could not find any numeric columns in this dataset."

        column = self._pick_column(question, numeric_columns) or self._preferred_numeric_column(numeric_columns)
        if not column:
            return "I could not determine which numeric column you want to analyze."

        series = pd.to_numeric(dataframe[column], errors="coerce").dropna()
        if series.empty:
            return f"The {column} column does not have enough numeric values for that calculation."

        if operation == "mean":
            return f"The average {column} value is {series.mean():,.2f}."
        if operation == "max":
            return f"The highest {column} value is {series.max():,.2f}."
        if operation == "min":
            return f"The lowest {column} value is {series.min():,.2f}."
        return f"The total {column} value is {series.sum():,.2f}."

    def _top_category_by_value_answer(
        self,
        question: str,
        dataframe: pd.DataFrame,
        numeric_columns: list[str],
        categorical_columns: list[str],
    ) -> str:
        if not numeric_columns or not categorical_columns:
            return "I need at least one numeric column and one category column to answer that question."

        metric_column = self._pick_column(question, numeric_columns) or self._preferred_numeric_column(numeric_columns)
        category_column = self._pick_column(question, categorical_columns) or self._preferred_categorical_column(categorical_columns)
        if not metric_column or not category_column:
            return "I could not determine which columns to use for that category comparison."

        grouped = dataframe.groupby(category_column, dropna=False)[metric_column].sum().sort_values(ascending=False)
        if grouped.empty:
            return "I could not calculate the top category because the grouped result is empty."

        label = str(grouped.index[0])
        return f"{label} has the highest total {metric_column}."

    def _most_common_category_answer(self, dataframe: pd.DataFrame, categorical_columns: list[str]) -> str:
        if not categorical_columns:
            return "I could not find a categorical column in this dataset."

        category_column = self._preferred_categorical_column(categorical_columns)
        if not category_column:
            return "I could not determine which category column to use."

        counts = dataframe[category_column].fillna("Unknown").astype(str).value_counts()
        if counts.empty:
            return f"I could not determine the most common value in {category_column}."

        label = str(counts.index[0])
        return f"The most common value in {category_column} is {label}."

    def _correlation_answer(self, question: str, dataframe: pd.DataFrame, numeric_columns: list[str]) -> str:
        if len(numeric_columns) < 2:
            return "I need at least two numeric columns to calculate a correlation."

        matches = self._match_columns(question, numeric_columns)
        if len(matches) >= 2:
            first, second = matches[0], matches[1]
        else:
            first, second = self._strongest_correlation_pair(dataframe, numeric_columns)

        correlation = pd.to_numeric(dataframe[first], errors="coerce").corr(pd.to_numeric(dataframe[second], errors="coerce"))
        if pd.isna(correlation):
            return f"I could not calculate the correlation between {first} and {second}."

        return f"The correlation between {first} and {second} is {correlation:.2f}."

    def _dataset_summary_answer(
        self,
        dataframe: pd.DataFrame,
        dataset_name: str,
        numeric_columns: list[str],
        categorical_columns: list[str],
        datetime_columns: list[str],
    ) -> str:
        return (
            f"The current dataset is {dataset_name}. It has {len(dataframe):,} rows and {len(dataframe.columns)} columns. "
            f"Numeric columns: {', '.join(numeric_columns) or 'none'}. "
            f"Categorical columns: {', '.join(categorical_columns) or 'none'}. "
            f"Date columns: {', '.join(datetime_columns) or 'none'}."
        )

    def _top_records_answer(self, dataframe: pd.DataFrame) -> str:
        preview = dataframe.head(5).copy()
        if preview.empty:
            return "There are no records available in the dataset."

        for column in preview.columns:
            if pd.api.types.is_datetime64_any_dtype(preview[column]):
                preview[column] = preview[column].dt.strftime("%Y-%m-%d")

        columns = preview.columns.tolist()[:5]
        lines = ["Here are the first 5 records:"]
        for index, (_, row) in enumerate(preview.iterrows(), start=1):
            values = [f"{column}={row[column]}" for column in columns]
            lines.append(f"{index}. " + ", ".join(values))
        if len(preview.columns) > len(columns):
            lines.append("Only the first few columns are shown here to keep the answer easy to read.")
        return "\n".join(lines)

    def _anomaly_answer(self, dataframe: pd.DataFrame, anomaly_payload: dict[str, Any] | None) -> str:
        payload = anomaly_payload or self._build_anomaly_payload(dataframe)
        anomaly_count = int(payload.get("anomaly_count", 0))
        explanations = payload.get("anomaly_explanations", []) or []

        if anomaly_count <= 0 or not explanations:
            return "No anomalies were detected in this dataset using the IQR method."

        lines = [f"I found {anomaly_count} anomalous row(s) using the IQR method."]
        for item in explanations[:5]:
            lines.append(f"- {item.get('explanation', '')}")
        if len(explanations) > 5:
            lines.append(f"There are {len(explanations) - 5} more anomaly explanations available on the dashboard and in the report.")
        return "\n".join(lines)

    def _build_anomaly_payload(self, dataframe: pd.DataFrame) -> dict[str, Any]:
        result = self.anomaly_detector.detect(dataframe)
        explanations = self.anomaly_explainer.explain(dataframe, result["anomaly_records"])
        return {
            "anomaly_count": int(result["anomaly_count"]),
            "anomaly_explanations": explanations,
        }

    @staticmethod
    def _system_explanation() -> str:
        return (
            "The system cleans the dataset by removing duplicate rows and filling missing values. "
            "It then detects numeric, categorical, and date columns, calculates descriptive statistics such as mean and median, "
            "checks correlations between numeric columns, detects anomalies with the IQR method, looks for simple trends over time, and generates clear charts."
        )

    @staticmethod
    def _is_system_question(question: str) -> bool:
        return any(
            phrase in question
            for phrase in [
                "how does the system",
                "how does the platform",
                "what algorithms",
                "how is the dataset analyzed",
                "what did the system do",
            ]
        )

    @staticmethod
    def _is_anomaly_question(question: str) -> bool:
        return any(
            phrase in question
            for phrase in [
                "explain the anomalies",
                "explain anomalies",
                "what are the anomalies",
                "anomalies in the dataset",
                "outliers in the dataset",
                "anomaly explanation",
            ]
        )

    @staticmethod
    def _is_numeric_columns_question(question: str) -> bool:
        return "numeric columns" in question or "which columns are numeric" in question

    @staticmethod
    def _is_categorical_columns_question(question: str) -> bool:
        return "categorical columns" in question or "which columns are categorical" in question

    @staticmethod
    def _is_top_records_question(question: str) -> bool:
        return any(phrase in question for phrase in ["top 5 records", "first 5 records", "top records"])

    @staticmethod
    def _is_summary_question(question: str) -> bool:
        return any(phrase in question for phrase in ["dataset summary", "summary of the dataset", "give a summary", "overview"])

    @staticmethod
    def _is_row_count_question(question: str) -> bool:
        return any(phrase in question for phrase in ["how many rows", "number of rows", "row count", "count of rows"])

    @staticmethod
    def _is_correlation_question(question: str) -> bool:
        return "correlation" in question or "relationship between" in question

    @staticmethod
    def _is_most_common_category_question(question: str) -> bool:
        return any(phrase in question for phrase in ["appears most often", "most common category", "most common value"])

    @staticmethod
    def _is_top_category_by_value_question(question: str) -> bool:
        return any(phrase in question for phrase in ["highest revenue", "highest value", "highest sales", "top category", "highest total"])

    @staticmethod
    def _detect_numeric_operation(question: str) -> str | None:
        if any(term in question for term in ["average", "mean"]):
            return "mean"
        if any(term in question for term in ["highest value", "maximum", "max", "largest"]):
            return "max"
        if any(term in question for term in ["lowest value", "minimum", "min", "smallest"]):
            return "min"
        if any(term in question for term in ["total sum", "sum of", "total", "sum"]):
            return "sum"
        return None

    def _pick_column(self, question: str, columns: list[str]) -> str | None:
        matches = self._match_columns(question, columns)
        return matches[0] if matches else None

    def _match_columns(self, question: str, columns: list[str]) -> list[str]:
        normalized_question = self._normalize_text(question)
        scores: list[tuple[int, str]] = []
        for column in columns:
            score = self._score_column(normalized_question, column)
            if score > 0:
                scores.append((score, column))
        scores.sort(key=lambda item: (-item[0], item[1]))
        return [column for _, column in scores]

    def _score_column(self, normalized_question: str, column: str) -> int:
        normalized_column = self._normalize_text(column)
        score = 0
        if normalized_column and normalized_column in normalized_question:
            score += 10

        tokens = [token for token in re.split(r"[^a-z0-9]+", column.lower()) if token]
        score += sum(2 for token in tokens if token in normalized_question)

        for alias in self._aliases_for_column(column):
            normalized_alias = self._normalize_text(alias)
            if normalized_alias and normalized_alias in normalized_question:
                score += 6
        return score

    def _aliases_for_column(self, column: str) -> list[str]:
        aliases = [column]
        lowered = column.lower().strip()
        for key, values in self.COLUMN_ALIASES.items():
            if key in lowered or lowered in values:
                aliases.extend(values)
        return aliases

    @staticmethod
    def _preferred_numeric_column(numeric_columns: list[str]) -> str | None:
        preferred_order = ["sales", "revenue", "amount", "profit", "income", "value", "score", "quantity"]
        for preferred in preferred_order:
            for column in numeric_columns:
                if preferred in column.lower():
                    return column
        return numeric_columns[0] if numeric_columns else None

    @staticmethod
    def _preferred_categorical_column(categorical_columns: list[str]) -> str | None:
        preferred_order = ["product line", "category", "segment", "type", "branch", "city", "customer type"]
        for preferred in preferred_order:
            for column in categorical_columns:
                if preferred in column.lower():
                    return column
        return categorical_columns[0] if categorical_columns else None

    def _strongest_correlation_pair(self, dataframe: pd.DataFrame, numeric_columns: list[str]) -> tuple[str, str]:
        corr_matrix = dataframe[numeric_columns].apply(pd.to_numeric, errors="coerce").corr(numeric_only=True)
        best_pair = (numeric_columns[0], numeric_columns[1])
        best_score = -1.0
        for index, first in enumerate(numeric_columns):
            for second in numeric_columns[index + 1 :]:
                value = corr_matrix.loc[first, second]
                if pd.isna(value):
                    continue
                score = abs(float(value))
                if score > best_score:
                    best_score = score
                    best_pair = (first, second)
        return best_pair

    @staticmethod
    def _normalize_text(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()
