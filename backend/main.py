from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from backend.chart_generator import ChartGenerator
from backend.chatbot import DatasetChatbot
from backend.data_processor import DataProcessor
from backend.forecasting import Forecasting
from backend.insight_engine import InsightEngine
from backend.insight_generator import InsightGenerator
from backend.report_generator import ReportGenerator
from backend.settings_manager import SettingsManager


BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
DATASETS_DIR = BASE_DIR / "datasets"
REPORTS_DIR = BASE_DIR / "reports"

DATASETS_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(exist_ok=True)

app = FastAPI(title="AI Data Insight Platform", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

processor = DataProcessor()
insight_engine = InsightEngine()
insight_generator = InsightGenerator()
forecasting = Forecasting()
chart_generator = ChartGenerator()
chatbot = DatasetChatbot()
report_generator = ReportGenerator()
settings_manager = SettingsManager()
current_dataset: Any | None = None
current_dataset_file: Path | None = None


@app.post("/upload")
async def upload_dataset(file: UploadFile = File(...)) -> dict[str, Any]:
    global current_dataset, current_dataset_file

    filename = (file.filename or "dataset.csv").strip()
    if not filename.lower().endswith((".csv", ".xlsx")):
        raise HTTPException(status_code=400, detail="Only CSV and XLSX files are supported.")

    file_bytes = await file.read()
    try:
        dataframe = processor.load_dataset(file_bytes, filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Unable to read file: {exc}") from exc

    current_dataset = dataframe
    current_dataset_file = DATASETS_DIR / f"current_dataset{Path(filename).suffix.lower()}"
    current_dataset_file.write_bytes(file_bytes)

    summary = processor.get_summary()
    column_types = processor.get_column_types()
    anomaly_payload = processor.get_anomalies()
    return {
        "message": "Dataset uploaded successfully.",
        "summary": summary,
        "anomalies": anomaly_payload,
        "charts": chart_generator.generate_chart_configs(dataframe, column_types),
        "insights": insight_engine.generate_insights(dataframe, column_types, summary),
        "business_insights": {
            "insights": insight_generator.generate(dataframe, column_types, anomaly_payload),
        },
        "forecast": forecasting.generate(dataframe, column_types),
    }


@app.post("/reset")
def reset_dataset() -> dict[str, str]:
    global current_dataset, current_dataset_file

    processor.reset()
    current_dataset = None
    current_dataset_file = None
    return {"message": "The current analysis session was cleared."}


@app.get("/dataset-status")
def dataset_status() -> dict[str, bool]:
    return {"dataset_loaded": dataset_is_loaded()}


@app.get("/dataset-summary")
def dataset_summary() -> dict[str, Any]:
    if not dataset_is_loaded():
        return dataset_not_uploaded_payload()

    return processor.get_summary()


@app.get("/statistics")
def statistics() -> dict[str, Any]:
    if not dataset_is_loaded():
        return dataset_not_uploaded_payload()

    return {"statistics": processor.get_summary().get("statistics", {})}


@app.get("/anomalies")
def anomalies() -> dict[str, Any]:
    if not dataset_is_loaded():
        return dataset_not_uploaded_payload()

    return processor.get_anomalies()


@app.get("/download-anomalies")
def download_anomalies() -> Any:
    if not dataset_is_loaded():
        return JSONResponse(content=dataset_not_uploaded_payload())

    try:
        anomaly_path = REPORTS_DIR / "anomaly_records.csv"
        processor.get_anomaly_dataframe().to_csv(anomaly_path, index=False)
        return FileResponse(anomaly_path, media_type="text/csv", filename=anomaly_path.name)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unable to build anomaly download: {exc}") from exc


@app.get("/download-anomaly-dataset")
def download_anomaly_dataset() -> Any:
    if not dataset_is_loaded():
        return JSONResponse(content=dataset_not_uploaded_payload())

    anomaly_dataframe = processor.get_anomaly_dataframe()
    if anomaly_dataframe.empty:
        return JSONResponse(content={"message": "No anomalies detected in the dataset."})

    try:
        anomaly_path = REPORTS_DIR / "anomaly_records.csv"
        anomaly_dataframe.to_csv(anomaly_path, index=False)
        return FileResponse(anomaly_path, media_type="text/csv", filename=anomaly_path.name)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unable to build anomaly dataset download: {exc}") from exc


@app.get("/download-anomaly-excel")
def download_anomaly_excel() -> Any:
    if not dataset_is_loaded():
        return JSONResponse(content=dataset_not_uploaded_payload())

    anomaly_dataframe = processor.get_anomaly_dataframe()
    if anomaly_dataframe.empty:
        return JSONResponse(content={"message": "No anomalies detected."})

    try:
        anomaly_path = REPORTS_DIR / "anomaly_dataset.xlsx"
        anomaly_dataframe.to_excel(anomaly_path, index=False)
        return FileResponse(
            anomaly_path,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=anomaly_path.name,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unable to build anomaly Excel download: {exc}") from exc


@app.get("/charts")
def charts() -> dict[str, Any]:
    if not dataset_is_loaded():
        return dataset_not_uploaded_payload()

    return chart_generator.generate_chart_configs(processor.get_dataframe(), processor.get_column_types())


@app.get("/business-insights")
def business_insights() -> dict[str, Any]:
    if not dataset_is_loaded():
        return dataset_not_uploaded_payload()

    return {
        "insights": insight_generator.generate(
            processor.get_dataframe(),
            processor.get_column_types(),
            processor.get_anomalies(),
        )
    }


@app.get("/forecast")
def forecast() -> dict[str, Any]:
    if not dataset_is_loaded():
        return dataset_not_uploaded_payload()

    return forecasting.generate(processor.get_dataframe(), processor.get_column_types())


@app.get("/insights")
def insights() -> dict[str, Any]:
    if not dataset_is_loaded():
        return dataset_not_uploaded_payload()

    summary = processor.get_summary()
    return insight_engine.generate_insights(processor.get_dataframe(), processor.get_column_types(), summary)


@app.post("/ask")
def ask_question(payload: dict[str, str]) -> dict[str, str]:
    if not dataset_is_loaded():
        return dataset_not_uploaded_payload()

    question = payload.get("question", "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="A question is required.")

    try:
        answer = chatbot.answer_from_dataframe(
            question,
            processor.get_dataframe(),
            processor.dataset_name or "Uploaded dataset",
            processor.get_anomalies(),
        )
        return {"answer": answer.get("answer", "No answer available.")}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unable to answer question: {exc}") from exc


@app.get("/email-settings")
@app.get("/settings/email")
def get_email_settings() -> dict[str, str]:
    saved_settings = settings_manager.get_email_settings()
    receiver_email = saved_settings.get("receiver_email", "")
    return {
        "sender_email": saved_settings.get("sender_email", ""),
        "receiver_email": receiver_email,
        "email": receiver_email,
    }


@app.post("/email-settings")
@app.post("/settings/email")
def save_email_settings(payload: dict[str, str]) -> dict[str, str]:
    sender_email = payload.get("sender_email", "").strip()
    sender_password = payload.get("sender_password", "")
    receiver_email = payload.get("receiver_email", payload.get("email", "")).strip()

    if sender_email and not is_valid_email_address(sender_email):
        raise HTTPException(status_code=400, detail="Please enter a valid sender email address.")
    if receiver_email and not is_valid_email_address(receiver_email):
        raise HTTPException(status_code=400, detail="Please enter a valid alert email address.")

    saved_settings = settings_manager.save_email_settings(sender_email, sender_password, receiver_email)
    receiver_email = saved_settings.get("receiver_email", "")
    return {
        "sender_email": saved_settings.get("sender_email", ""),
        "receiver_email": receiver_email,
        "email": receiver_email,
        "message": "Email settings saved successfully.",
    }


@app.get("/download-report")
@app.get("/report")
def download_report() -> Any:
    if not dataset_is_loaded():
        return JSONResponse(content=dataset_not_uploaded_payload())

    try:
        dataframe = processor.get_dataframe()
        column_types = processor.get_column_types()
        summary = processor.get_summary()
        insights_data = insight_engine.generate_insights(dataframe, column_types, summary)
        report_path = REPORTS_DIR / "AI_Data_Insight_Report.pdf"
        report_generator.build_report(report_path, summary, insights_data, dataframe, column_types)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unable to build report: {exc}") from exc

    return StreamingResponse(
        report_path.open("rb"),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{report_path.name}"'},
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
def serve_home() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/upload-page")
def serve_upload_page() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "upload.html")


@app.get("/dashboard-page")
def serve_dashboard_page() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "dashboard.html")


@app.get("/analysis-page")
def serve_analysis_page() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "analysis.html")


@app.get("/insights-page")
def serve_insights_page() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "analysis.html")


@app.get("/chat-page")
def serve_chat_page() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "chat.html")


@app.get("/report-page")
def serve_report_page() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "report.html")


@app.get("/email-settings-page")
def serve_email_settings_page() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "email_settings.html")


app.mount("/frontend", StaticFiles(directory=FRONTEND_DIR), name="frontend")


def dataset_is_loaded() -> bool:
    return current_dataset is not None and processor.has_dataset()


def dataset_not_uploaded_payload() -> dict[str, str]:
    return {"message": "Dataset not uploaded"}


def is_valid_email_address(value: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", value))
