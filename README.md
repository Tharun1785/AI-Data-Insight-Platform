# InsightAI

InsightAI is an AI-powered data analytics web platform built with FastAPI, Pandas, NumPy, Chart.js, and vanilla JavaScript. It lets users upload CSV or Excel datasets, auto-cleans them, generates charts and statistics, produces AI-style insights, supports dataset Q&A, and exports a PDF report.

## Features

- Upload CSV, XLSX, or XLS files
- Automatic dataset cleaning and column type detection
- Statistics: mean, median, mode, min, max, standard deviation
- Dashboard with bar, line, pie, histogram, scatter, and correlation heatmap
- AI-generated insights and trend summaries
- AI data chat assistant for natural-language questions
- PDF report export with summary, stats, insights, and charts

## Project Structure

```text
frontend/
  index.html
  dashboard.html
  upload.html
  insights.html
  chat.html
  report.html
  styles.css
  script.js

backend/
  main.py
  data_processor.py
  insight_engine.py
  chart_generator.py
  chatbot.py

datasets/
reports/
requirements.txt
README.md
```

## Setup

1. Create and activate a virtual environment:

```powershell
python -m venv .venv
.venv\Scripts\activate
```

2. Install dependencies:

```powershell
pip install -r requirements.txt
```

3. Run the FastAPI server:

```powershell
uvicorn backend.main:app --reload
```

4. Open the application:

- Home: http://127.0.0.1:8000/
- Upload: http://127.0.0.1:8000/upload-page
- Dashboard: http://127.0.0.1:8000/dashboard-page
- Insights: http://127.0.0.1:8000/insights-page
- Chat: http://127.0.0.1:8000/chat-page
- Report: http://127.0.0.1:8000/report-page

## API Endpoints

- POST /upload
- GET /dataset-summary
- GET /charts
- GET /insights
- POST /ask
- GET /report

## Notes

- The app keeps the latest uploaded dataset in memory for analysis and chat.
- Uploaded files are also stored in datasets/.
- Generated PDF reports are saved in reports/ and streamed to the browser on download.
