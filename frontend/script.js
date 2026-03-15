const API_BASE = "";
const SESSION_KEY = "insightai-session-active";
const DATASET_SESSION_KEY = "insightai-dataset-loaded";
const state = {
    datasetLoaded: false,
    summary: null,
    chartInstances: [],
};

const UPLOAD_STAGES = ["Uploading dataset...", "Analyzing data...", "Preparing dashboard..."];
const DASHBOARD_STAGES = ["Loading summary...", "Loading charts...", "Loading insights...", "Loading forecast...", "Loading anomalies..."];
const ANALYSIS_STAGES = ["Loading analysis...", "Preparing explanation..."];
const SUGGESTED_QUESTIONS = [
    "What is the average value in the dataset?",
    "What is the maximum value in the dataset?",
    "What is the minimum value in the dataset?",
    "What is the total value in the dataset?",
    "How many rows are in the dataset?",
    "Which category has the highest value?",
    "What are the top 5 records?",
    "Give a summary of the dataset.",
    "What is the correlation between columns?",
    "Explain the anomalies in the dataset.",
];

if (typeof Chart !== "undefined") {
    Chart.defaults.font.family = '"Segoe UI", Arial, sans-serif';
    Chart.defaults.color = "#4b5563";
    Chart.defaults.borderColor = "#e5e7eb";
}

document.addEventListener("DOMContentLoaded", async () => {
    const page = document.body.dataset.page || "home";
    const sessionState = await initializeDatasetSession();
    state.datasetLoaded = await loadDatasetStatus();
    state.summary = state.datasetLoaded ? await loadCurrentSummary() : null;

    if (!state.summary) {
        state.datasetLoaded = false;
        window.sessionStorage.removeItem(DATASET_SESSION_KEY);
    }

    updateDatasetStatus(state.summary);
    renderRefreshNotice(sessionState.wasReloadReset);

    // Add navbar
    const navbar = document.createElement('nav');
    navbar.className = 'navbar';
    const pageTitle = document.body.dataset.page;
    const displayTitle = pageTitle ? pageTitle.charAt(0).toUpperCase() + pageTitle.slice(1).replace('-', ' ') : 'Home';
    navbar.innerHTML = `
        <div class="navbar-title">${displayTitle}</div>
        <div class="navbar-actions">
            <button class="menu-toggle">☰</button>
        </div>
    `;
    document.body.insertBefore(navbar, document.body.firstChild);

    // Add responsive menu toggle
    const menuToggle = navbar.querySelector('.menu-toggle');
    menuToggle.onclick = () => {
        document.querySelector('.sidebar').classList.toggle('active');
        document.querySelector('.sidebar-overlay').classList.toggle('active');
    };

    const overlay = document.createElement('div');
    overlay.className = 'sidebar-overlay';
    overlay.onclick = () => {
        document.querySelector('.sidebar').classList.remove('active');
        overlay.classList.remove('active');
    };
    document.body.appendChild(overlay);

    switch (page) {
        case "home":
            initHomePage();
            break;
        case "upload":
            initUploadPage();
            break;
        case "dashboard":
            initDashboardPage();
            break;
        case "analysis":
            initAnalysisPage();
            break;
        case "chat":
            initChatPage();
            break;
        case "report":
            initReportPage();
            break;
        case "email-settings":
            initEmailSettingsPage();
            break;
        default:
            break;
    }
});

async function fetchJson(url, options = {}) {
    const response = await fetch(`${API_BASE}${url}`, options);
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
        throw new Error(data.detail || "Request failed.");
    }
    return data;
}

async function initializeDatasetSession() {
    const navigationEntry = typeof performance.getEntriesByType === "function"
        ? performance.getEntriesByType("navigation")[0]
        : null;
    const isReload = navigationEntry
        ? navigationEntry.type === "reload"
        : Boolean(performance.navigation && performance.navigation.type === 1);
    const hasSession = window.sessionStorage.getItem(SESSION_KEY) === "active";
    const shouldReset = isReload || !hasSession;

    if (!shouldReset) {
        return { wasReloadReset: false };
    }

    try {
        await fetchJson("/reset", { method: "POST" });
    } catch (error) {
        // Ignore reset errors when there is no active dataset.
    }

    clearClientState();
    window.sessionStorage.setItem(SESSION_KEY, "active");
    window.sessionStorage.removeItem(DATASET_SESSION_KEY);
    return { wasReloadReset: isReload };
}

function clearClientState() {
    state.datasetLoaded = false;
    state.summary = null;
    destroyCharts();

    const chatHistory = document.getElementById("chat-history");
    if (chatHistory) {
        chatHistory.innerHTML = "";
    }
}

async function loadDatasetStatus() {
    try {
        const result = await fetchJson("/dataset-status");
        const loaded = Boolean(result.dataset_loaded);

        if (loaded) {
            window.sessionStorage.setItem(DATASET_SESSION_KEY, "true");
        } else {
            window.sessionStorage.removeItem(DATASET_SESSION_KEY);
        }

        return loaded;
    } catch (error) {
        window.sessionStorage.removeItem(DATASET_SESSION_KEY);
        return false;
    }
}

async function loadCurrentSummary() {
    try {
        const result = await fetchJson("/dataset-summary");
        return result && !result.message ? result : null;
    } catch (error) {
        return null;
    }
}

function updateDatasetStatus(summary) {
    const element = document.getElementById("dataset-status");
    if (!element) {
        return;
    }

    element.textContent = summary
        ? `Current dataset: ${summary.dataset_name || "Dataset"}`
        : "No dataset uploaded";
}

function renderRefreshNotice(didReset) {
    const notice = document.getElementById("page-notice");
    if (!notice) {
        return;
    }

    if (!didReset) {
        notice.classList.add("hidden");
        notice.textContent = "";
        return;
    }

    notice.classList.remove("hidden");
    notice.textContent = "The page was refreshed. Please upload the dataset again to continue.";
}

function initHomePage() {
    const element = document.getElementById("home-session-status");
    if (!element) {
        return;
    }

    if (!state.summary) {
        element.textContent = "No dataset is loaded yet. Upload a CSV or XLSX file to begin.";
        return;
    }

    element.textContent = `${state.summary.dataset_name || "Dataset"} is loaded with ${formatNumber(state.summary.rows)} rows and ${formatNumber(state.summary.columns)} columns.`;
}

function initUploadPage() {
    const form = document.getElementById("upload-form");
    const fileInput = document.getElementById("dataset-file");
    const dropzone = document.getElementById("dropzone");
    const selectedFile = document.getElementById("selected-file");
    const status = document.getElementById("upload-status");
    const button = document.getElementById("upload-button");

    if (state.summary) {
        renderPreviewTable(state.summary.preview, "preview-table");
        setStatusMessage(status, `${state.summary.dataset_name} is currently loaded. Upload a new file to replace it.`, "success");
    } else {
        setStatusMessage(status, "Select a CSV or XLSX file to start.", "default");
    }

    if (!form || !fileInput || !dropzone || !selectedFile || !status || !button) {
        return;
    }

    fileInput.addEventListener("change", () => {
        selectedFile.textContent = fileInput.files[0] ? fileInput.files[0].name : "No file selected";
    });

    ["dragenter", "dragover"].forEach((eventName) => {
        dropzone.addEventListener(eventName, (event) => {
            event.preventDefault();
            dropzone.classList.add("is-dragover");
        });
    });

    ["dragleave", "dragend", "drop"].forEach((eventName) => {
        dropzone.addEventListener(eventName, (event) => {
            event.preventDefault();
            dropzone.classList.remove("is-dragover");
        });
    });

    dropzone.addEventListener("drop", (event) => {
        const files = event.dataTransfer.files;
        if (!files || !files.length) {
            return;
        }

        const transfer = new DataTransfer();
        Array.from(files).forEach((singleFile) => transfer.items.add(singleFile));
        fileInput.files = transfer.files;
        selectedFile.textContent = files[0].name;
    });

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        const file = fileInput.files[0];

        if (!file) {
            setStatusMessage(status, "Please choose a file to upload.", "error");
            return;
        }

        if (!/\.(csv|xlsx)$/i.test(file.name)) {
            setStatusMessage(status, "Only CSV and XLSX files are supported.", "error");
            return;
        }

        const formData = new FormData();
        formData.append("file", file);

        button.disabled = true;
        const loader = startLoader("upload-loader", UPLOAD_STAGES);
        setStatusMessage(status, "Uploading dataset...", "default");
        renderEmptyMessage("preview-table", "Preparing dataset preview...");

        try {
            const result = await fetchJson("/upload", {
                method: "POST",
                body: formData,
            });

            state.datasetLoaded = true;
            state.summary = result.summary;
            window.sessionStorage.setItem(DATASET_SESSION_KEY, "true");
            updateDatasetStatus(result.summary);
            renderPreviewTable(result.summary.preview, "preview-table");
            loader.complete("Upload complete.");
            setStatusMessage(status, "Dataset uploaded successfully. Redirecting to the dashboard...", "success");
            window.setTimeout(() => {
                window.location.href = "/dashboard-page";
            }, 600);
        } catch (error) {
            loader.fail(error.message);
            setStatusMessage(status, error.message, "error");
            renderEmptyMessage("preview-table", "Upload a dataset to preview the first 10 rows.");
            button.disabled = false;
        }
    });
}

async function initDashboardPage() {
    let anomalyCount = 0;
    if (state.summary) {
        try {
            const anomalyPayload = await fetchJson("/anomalies");
            anomalyCount = anomalyPayload && typeof anomalyPayload.anomaly_count === "number" ? anomalyPayload.anomaly_count : 0;
        } catch (error) {
            // Ignore, use 0
        }
    }
    renderDashboardStats(state.summary, anomalyCount);
    renderSummaryCards(state.summary);
    updateDownloadButton(Boolean(state.summary), "download-anomalies-button", "/download-anomalies");

    if (!state.summary) {
        renderEmptyMessage("charts-grid", "No dataset uploaded. Upload a dataset to view analysis.");
        renderInfoList("key-insights-list", ["Upload a dataset to see key insights."]);
        setElementText("forecast-summary", "Upload a dataset with a date column to view the next predicted values.");
        renderEmptyMessage("forecast-chart-area", "Future trend prediction will appear here after dataset upload.");
        setElementText("anomaly-count", "No dataset uploaded. Please upload a dataset to begin analysis.");
        renderEmptyMessage("anomaly-table", "No dataset uploaded. Please upload a dataset to begin analysis.");
        return;
    }

    const loader = startLoader("dashboard-loader", DASHBOARD_STAGES);

    try {
        const [chartPayload, anomalyPayload, insightPayload, forecastPayload] = await Promise.all([
            fetchJson("/charts"),
            fetchJson("/anomalies"),
            fetchJson("/business-insights"),
            fetchJson("/forecast"),
        ]);

        renderCharts(chartPayload.charts || []);
        renderKeyInsights(insightPayload);
        renderForecastSection(forecastPayload);
        renderAnomalySection(anomalyPayload);
        loader.complete("Dashboard ready.");
    } catch (error) {
        renderEmptyMessage("charts-grid", error.message);
        renderInfoList("key-insights-list", ["Key insights could not be loaded."]);
        setElementText("forecast-summary", "Future trend prediction could not be loaded.");
        renderEmptyMessage("forecast-chart-area", "Future trend prediction could not be loaded.");
        setElementText("anomaly-count", error.message);
        renderEmptyMessage("anomaly-table", "Anomaly results could not be loaded.");
        loader.fail(error.message);
    }
}

async function initAnalysisPage() {
    if (!state.summary) {
        renderInfoList("analysis-overview", ["Upload a dataset to see the analysis page."]);
        renderInfoList("analysis-statistics", ["Statistics explanations will appear here after upload."]);
        renderInfoList("analysis-trends", ["Trend observations will appear here after upload."]);
        renderInfoList("analysis-anomalies", ["Anomaly explanations will appear here after upload."]);
        return;
    }

    const loader = startLoader("analysis-loader", ANALYSIS_STAGES);

    try {
        const [insights, anomalies] = await Promise.all([
            fetchJson("/insights"),
            fetchJson("/anomalies"),
        ]);

        renderInfoList("analysis-overview", buildOverviewItems(state.summary));
        renderInfoList("analysis-statistics", buildStatisticsExplanation(state.summary, insights));
        renderInfoList("analysis-trends", buildTrendObservations(insights));
        renderInfoList("analysis-anomalies", buildAnomalyExplanations(anomalies));
        loader.complete("Analysis ready.");
    } catch (error) {
        renderInfoList("analysis-overview", [error.message]);
        renderInfoList("analysis-statistics", ["Statistics could not be loaded."]);
        renderInfoList("analysis-trends", ["Trend observations could not be loaded."]);
        renderInfoList("analysis-anomalies", ["Anomaly explanations could not be loaded."]);
        loader.fail(error.message);
    }
}

function initChatPage() {
    renderSuggestedQuestions();
    renderChatIntro();

    const form = document.getElementById("chat-form");
    const input = document.getElementById("chat-question");
    const submit = document.getElementById("chat-submit");

    if (!form || !input || !submit) {
        return;
    }

    input.disabled = !state.summary;
    submit.disabled = !state.summary;
    input.placeholder = state.summary ? "Type your question" : "Upload a dataset first";

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        if (!state.summary) {
            return;
        }

        const question = input.value.trim();
        if (!question) {
            return;
        }

        input.value = "";
        await sendChatQuestion(question, submit);
    });
}

function initReportPage() {
    const button = document.getElementById("download-report-button");
    const anomalyButton = document.getElementById("download-anomaly-excel-button");

    if (!state.summary) {
        renderInfoList("report-details", ["Upload a dataset to enable report download."]);
        updateDownloadButton(false, "download-report-button", "/download-report");
        updateDownloadButton(false, "download-anomaly-excel-button", "/download-anomaly-excel");
        return;
    }

    renderInfoList("report-details", [
        `${state.summary.dataset_name || "Dataset"}`,
        `${formatNumber(state.summary.rows)} rows`,
        `${formatNumber(state.summary.columns)} columns`,
        `${formatNumber(state.summary.anomaly_count || 0)} anomalies detected`,
    ]);
    updateDownloadButton(true, "download-report-button", "/download-report");
    updateDownloadButton(Boolean(state.summary.anomaly_count), "download-anomaly-excel-button", "/download-anomaly-excel");
}

async function initEmailSettingsPage() {
    const form = document.getElementById("email-settings-form");
    const senderEmailInput = document.getElementById("sender-email");
    const senderPasswordInput = document.getElementById("sender-password");
    const receiverEmailInput = document.getElementById("email-address");
    const status = document.getElementById("email-settings-status");
    const button = document.getElementById("save-email-button");

    if (!form || !senderEmailInput || !senderPasswordInput || !receiverEmailInput || !status || !button) {
        return;
    }

    button.disabled = true;
    try {
        const result = await fetchJson("/email-settings");
        senderEmailInput.value = result.sender_email || "";
        senderPasswordInput.value = "";
        receiverEmailInput.value = result.receiver_email || result.email || "";
        setStatusMessage(
            status,
            (result.sender_email || result.receiver_email)
                ? "Saved email settings loaded. Enter a new app password only if you want to change it."
                : "No email settings are saved yet.",
            (result.sender_email || result.receiver_email) ? "success" : "default"
        );
    } catch (error) {
        setStatusMessage(status, error.message, "error");
    } finally {
        button.disabled = false;
    }

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        const senderEmail = senderEmailInput.value.trim();
        const senderPassword = senderPasswordInput.value;
        const receiverEmail = receiverEmailInput.value.trim();

        if (senderEmail && !isValidEmail(senderEmail)) {
            setStatusMessage(status, "Please enter a valid sender email address.", "error");
            return;
        }

        if (receiverEmail && !isValidEmail(receiverEmail)) {
            setStatusMessage(status, "Please enter a valid alert email address.", "error");
            return;
        }

        button.disabled = true;
        setStatusMessage(status, "Saving email settings...", "default");

        try {
            const result = await fetchJson("/email-settings", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    sender_email: senderEmail,
                    sender_password: senderPassword,
                    receiver_email: receiverEmail,
                }),
            });
            senderEmailInput.value = result.sender_email || "";
            senderPasswordInput.value = "";
            receiverEmailInput.value = result.receiver_email || result.email || "";
            setStatusMessage(status, result.message || "Email settings saved.", "success");
        } catch (error) {
            setStatusMessage(status, error.message, "error");
        } finally {
            button.disabled = false;
        }
    });
}

function renderSuggestedQuestions() {
    const container = document.getElementById("suggested-questions");
    if (!container) {
        return;
    }

    container.innerHTML = SUGGESTED_QUESTIONS.map((question) => `
        <button class="chip" type="button" data-question="${escapeHtml(question)}">${escapeHtml(question)}</button>
    `).join("");

    container.addEventListener("click", async (event) => {
        const button = event.target.closest("button[data-question]");
        if (!button || !state.summary) {
            return;
        }

        const submit = document.getElementById("chat-submit");
        if (!submit) {
            return;
        }

        await sendChatQuestion(button.dataset.question || "", submit);
    });
}

function renderChatIntro() {
    const history = document.getElementById("chat-history");
    if (!history) {
        return;
    }

    history.innerHTML = "";
    if (!state.summary) {
        appendChatBubble("bot", "Upload a dataset first. Then you can ask about values, rows, categories, correlations, and anomalies.");
        return;
    }

    appendChatBubble("bot", `${state.summary.dataset_name} is ready. Ask a question about the dataset.`);
}

async function sendChatQuestion(question, submit) {
    if (!question) {
        return;
    }

    submit.disabled = true;
    appendChatBubble("user", question);
    const pendingBubble = appendChatBubble("bot", "Loading answer...");

    try {
        const result = await fetchJson("/ask", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question }),
        });
        pendingBubble.textContent = result.answer || "No answer was returned.";
    } catch (error) {
        pendingBubble.textContent = error.message;
    } finally {
        submit.disabled = false;
        scrollChatToBottom();
    }
}

function renderSummaryCards(summary) {
    const container = document.getElementById("dashboard-summary-cards");
    if (!container) {
        return;
    }

    const rows = summary ? formatNumber(summary.rows) : "0";
    const columns = summary ? formatNumber(summary.columns) : "0";
    const numeric = summary ? formatNumber(summary.column_types.numeric.length) : "0";
    const categorical = summary ? formatNumber(summary.column_types.categorical.length) : "0";

    container.innerHTML = [
        createSummaryCard("Rows", rows),
        createSummaryCard("Columns", columns),
        createSummaryCard("Numeric Columns", numeric),
        createSummaryCard("Categorical Columns", categorical),
    ].join("");
}

function renderDashboardStats(summary, anomalyCount = 0) {
    const container = document.getElementById("dashboard-stats");
    if (!container) {
        return;
    }

    const rows = summary ? formatNumber(summary.rows) : "0";
    const columns = summary ? formatNumber(summary.columns) : "0";
    const numeric = summary ? formatNumber(summary.column_types.numeric.length) : "0";
    const categorical = summary ? formatNumber(summary.column_types.categorical.length) : "0";
    const anomalies = formatNumber(anomalyCount);

    container.innerHTML = [
        createStatCard("Rows", rows),
        createStatCard("Columns", columns),
        createStatCard("Numeric Columns", numeric),
        createStatCard("Categorical Columns", categorical),
        createStatCard("Anomalies Detected", anomalies),
    ].join("");
}

function createStatCard(title, value) {
    return `
        <div class="stat-card">
            <div class="stat-title">${escapeHtml(title)}</div>
            <div class="stat-value">${escapeHtml(String(value))}</div>
        </div>
    `;
}

function createSummaryCard(label, value) {
    return `
        <article class="summary-card">
            <span>${escapeHtml(label)}</span>
            <strong>${escapeHtml(String(value))}</strong>
        </article>
    `;
}

function renderCharts(charts) {
    const container = document.getElementById("charts-grid");
    if (!container) {
        return;
    }

    destroyCharts();

    const simpleCharts = (charts || []).filter((chart) => ["bar", "line", "pie"].includes(chart.type)).slice(0, 3);
    if (!simpleCharts.length) {
        renderEmptyMessage("charts-grid", "No charts are available for this dataset.");
        return;
    }

    if (typeof Chart === "undefined") {
        renderEmptyMessage("charts-grid", "Chart.js could not be loaded.");
        return;
    }

    container.innerHTML = simpleCharts.map((chart, index) => `
        <article class="chart-card">
            <h3>${escapeHtml(chart.title || `${chart.type} chart`)}</h3>
            <p class="section-text">${escapeHtml(chart.description || "Simple chart generated from the dataset.")}</p>
            <div class="chart-canvas">
                <canvas id="chart-${index}"></canvas>
            </div>
            <p class="section-text"><strong>Chart Explanation:</strong> ${escapeHtml(chart.explanation || chart.description || "This chart shows a simple pattern in the dataset.")}</p>
        </article>
    `).join("");

    simpleCharts.forEach((chart, index) => {
        const canvas = document.getElementById(`chart-${index}`);
        if (!canvas) {
            return;
        }

        const chartInstance = new Chart(canvas, {
            type: chart.type,
            data: chart.chartjs,
            options: getChartOptions(chart.type),
        });
        state.chartInstances.push(chartInstance);
    });
}

function renderKeyInsights(payload) {
    const insights = payload && Array.isArray(payload.insights) ? payload.insights : [];
    if (!insights.length) {
        renderInfoList("key-insights-list", [payload && payload.message ? payload.message : "No key insights are available for this dataset yet."]);
        return;
    }

    renderInfoList("key-insights-list", insights.slice(0, 5));
}

function renderForecastSection(payload) {
    const summaryElement = document.getElementById("forecast-summary");
    const container = document.getElementById("forecast-chart-area");
    if (!summaryElement || !container) {
        return;
    }

    if (!payload || payload.message === "Dataset not uploaded") {
        container.className = "empty-state";
        summaryElement.textContent = "Upload a dataset with a date column to view the next predicted values.";
        renderEmptyMessage("forecast-chart-area", "Future trend prediction will appear here after dataset upload.");
        return;
    }

    if (!payload.available || !payload.chartjs) {
        container.className = "empty-state";
        summaryElement.textContent = payload.message || "Future trend prediction is not available for this dataset.";
        renderEmptyMessage("forecast-chart-area", summaryElement.textContent);
        return;
    }

    container.className = "";
    summaryElement.textContent = payload.message || "The next predicted values are shown below.";

    container.innerHTML = `
        <div class="chart-canvas">
            <canvas id="forecast-chart"></canvas>
        </div>
        <div class="info-list">${buildForecastValuesList(payload.predictions || [])}</div>
    `;

    if (typeof Chart === "undefined") {
        container.className = "empty-state";
        renderEmptyMessage("forecast-chart-area", "Chart.js could not be loaded.");
        return;
    }

    const canvas = document.getElementById("forecast-chart");
    if (!canvas) {
        return;
    }

    const forecastChart = new Chart(canvas, {
        type: "line",
        data: payload.chartjs,
        options: getForecastChartOptions(),
    });
    state.chartInstances.push(forecastChart);
}

function buildForecastValuesList(predictions) {
    if (!predictions.length) {
        return '<div class="info-item">No predicted values are available yet.</div>';
    }

    return predictions.map((prediction) => `
        <div class="info-item">
            <strong>${escapeHtml(prediction.label || "Future point")}</strong>: ${escapeHtml(formatStatistic(prediction.value))}
        </div>
    `).join("");
}
function renderAnomalySection(payload) {
    const count = payload && typeof payload.anomaly_count === "number" ? payload.anomaly_count : 0;
    const records = payload && Array.isArray(payload.anomaly_records) ? payload.anomaly_records : [];

    setElementText(
        "anomaly-count",
        count ? `${formatNumber(count)} anomalies detected.` : "No anomalies were detected in this dataset."
    );

    if (!records.length) {
        renderEmptyMessage("anomaly-table", "No anomaly records are available.");
        return;
    }

    const flattened = flattenAnomalyRows(records);
    if (!flattened.length) {
        renderEmptyMessage("anomaly-table", "No anomaly records are available.");
        return;
    }

    const container = document.getElementById("anomaly-table");
    if (!container) {
        return;
    }

    container.innerHTML = `
        <table class="data-table">
            <thead>
                <tr>
                    <th>Row</th>
                    <th>Column causing anomaly</th>
                    <th>Anomaly value</th>
                </tr>
            </thead>
            <tbody>
                ${flattened.map((row) => `
                    <tr>
                        <td>${escapeHtml(String(row.row))}</td>
                        <td>${escapeHtml(row.column)}</td>
                        <td>${escapeHtml(formatCell(row.value))}</td>
                    </tr>
                `).join("")}
            </tbody>
        </table>
    `;
}

function flattenAnomalyRows(records) {
    const flattened = [];

    records.forEach((record) => {
        const rowNumber = record.original_row !== undefined && record.original_row !== null
            ? record.original_row
            : (record.row !== undefined && record.row !== null ? record.row : "-");
        const columns = String(record.anomaly_columns || "")
            .split(",")
            .map((value) => value.trim())
            .filter(Boolean);

        if (!columns.length) {
            return;
        }

        columns.forEach((columnName) => {
            flattened.push({
                row: rowNumber,
                column: columnName,
                value: record[columnName],
            });
        });
    });

    return flattened;
}

function buildOverviewItems(summary) {
    return [
        `Dataset name: ${summary.dataset_name || "Dataset"}`,
        `Rows: ${formatNumber(summary.rows)}`,
        `Columns: ${formatNumber(summary.columns)}`,
        `Numeric columns: ${summary.column_types.numeric.join(", ") || "none"}`,
        `Categorical columns: ${summary.column_types.categorical.join(", ") || "none"}`,
    ];
}

function buildStatisticsExplanation(summary, insights) {
    const items = [
        "The system analyzed the dataset and calculated statistical values such as average, minimum, and maximum to understand the distribution of the data.",
        "The mean shows the average value, the minimum shows the smallest value, and the maximum shows the largest value.",
        "The standard deviation shows how spread out the values are.",
    ];

    const statEntries = Object.entries(summary.statistics || {}).slice(0, 3);
    statEntries.forEach(([column, values]) => {
        items.push(
            `${column}: average ${formatStatistic(values.mean)}, minimum ${formatStatistic(values.min)}, maximum ${formatStatistic(values.max)}.`
        );
    });

    if (insights && Array.isArray(insights.statistical_explanations)) {
        insights.statistical_explanations.slice(0, 2).forEach((item) => {
            items.push(`${item.term}: ${item.explanation}`);
        });
    }

    return items;
}

function buildTrendObservations(insights) {
    if (insights && Array.isArray(insights.trends) && insights.trends.length) {
        return insights.trends;
    }
    return ["No strong trend was detected in the current dataset."];
}

function buildAnomalyExplanations(anomalies) {
    const count = anomalies && typeof anomalies.anomaly_count === "number" ? anomalies.anomaly_count : 0;
    const explanations = anomalies && Array.isArray(anomalies.anomaly_explanations) ? anomalies.anomaly_explanations : [];

    if (!count || !explanations.length) {
        return ["No anomalies were detected using the IQR method."];
    }

    const items = [
        `The system found ${formatNumber(count)} anomalous row(s) by looking for values outside the normal range.`,
    ];
    explanations.slice(0, 5).forEach((item) => {
        items.push(item.explanation || "");
    });
    return items;
}

function updateDownloadButton(enabled, id, href) {
    const button = document.getElementById(id);
    if (!button) {
        return;
    }

    if (!enabled) {
        button.classList.add("is-disabled");
        button.setAttribute("aria-disabled", "true");
        button.removeAttribute("href");
        return;
    }

    button.classList.remove("is-disabled");
    button.removeAttribute("aria-disabled");
    button.setAttribute("href", href);
}

function appendChatBubble(role, text) {
    const history = document.getElementById("chat-history");
    if (!history) {
        return document.createElement("div");
    }

    const bubble = document.createElement("div");
    bubble.className = `chat-bubble ${role}`;
    bubble.textContent = text;
    history.appendChild(bubble);
    scrollChatToBottom();
    return bubble;
}

function scrollChatToBottom() {
    const history = document.getElementById("chat-history");
    if (!history) {
        return;
    }
    history.scrollTop = history.scrollHeight;
}

function renderPreviewTable(records, containerId) {
    const container = document.getElementById(containerId);
    if (!container) {
        return;
    }

    if (!records || !records.length) {
        renderEmptyMessage(containerId, "No preview rows are available.");
        return;
    }

    const columns = Object.keys(records[0]);
    container.innerHTML = `
        <table class="data-table">
            <thead>
                <tr>${columns.map((column) => `<th>${escapeHtml(column)}</th>`).join("")}</tr>
            </thead>
            <tbody>
                ${records.map((record) => `
                    <tr>
                        ${columns.map((column) => `<td>${escapeHtml(formatCell(record[column]))}</td>`).join("")}
                    </tr>
                `).join("")}
            </tbody>
        </table>
    `;
}

function renderInfoList(id, items) {
    const container = document.getElementById(id);
    if (!container) {
        return;
    }

    const values = items && items.length ? items : ["No information is available yet."];
    container.innerHTML = values.map((item) => `<div class="info-item">${escapeHtml(item)}</div>`).join("");
}

function renderEmptyMessage(id, message) {
    const container = document.getElementById(id);
    if (!container) {
        return;
    }

    container.innerHTML = `<div class="empty-state">${escapeHtml(message)}</div>`;
}

function startLoader(id, stages) {
    const container = document.getElementById(id);
    if (!container) {
        return { complete() {}, fail() {} };
    }

    container.classList.remove("hidden");
    let index = 0;
    renderLoader(container, stages[index], progressWidth(index, stages.length));

    const intervalId = window.setInterval(() => {
        index = Math.min(index + 1, stages.length - 1);
        renderLoader(container, stages[index], progressWidth(index, stages.length));
        if (index === stages.length - 1) {
            window.clearInterval(intervalId);
        }
    }, 700);

    return {
        complete(message) {
            window.clearInterval(intervalId);
            renderLoader(container, message || "Ready.", 100);
            window.setTimeout(() => {
                container.classList.add("hidden");
            }, 500);
        },
        fail(message) {
            window.clearInterval(intervalId);
            container.classList.remove("hidden");
            container.innerHTML = `<div class="status-message is-error">${escapeHtml(message)}</div>`;
        },
    };
}

function renderLoader(container, message, width) {
    container.innerHTML = `
        <div class="loader-top">
            <span class="loader-spinner"></span>
            <span>${escapeHtml(message)}</span>
        </div>
        <div class="loader-progress">
            <span style="width: ${width}%;"></span>
        </div>
    `;
}

function progressWidth(index, total) {
    return Math.round(((index + 1) / total) * 100);
}

function setStatusMessage(element, message, tone) {
    if (!element) {
        return;
    }

    element.textContent = message;
    element.className = "status-message";
    if (tone === "success") {
        element.classList.add("is-success");
    }
    if (tone === "error") {
        element.classList.add("is-error");
    }
}

function setElementText(id, value) {
    const element = document.getElementById(id);
    if (element) {
        element.textContent = value;
    }
}

function getChartOptions(type) {
    const options = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                display: type === "pie",
                position: "bottom",
            },
        },
    };

    if (type !== "pie") {
        options.scales = {
            x: {
                ticks: {
                    maxRotation: 35,
                    minRotation: 0,
                },
            },
            y: {
                beginAtZero: true,
            },
        };
    }

    return options;
}

function getForecastChartOptions() {
    const options = getChartOptions("line");
    options.plugins.legend.display = true;
    return options;
}
function destroyCharts() {
    state.chartInstances.forEach((instance) => instance.destroy());
    state.chartInstances = [];
}

function formatNumber(value) {
    return Number(value || 0).toLocaleString();
}

function formatStatistic(value) {
    if (value === null || value === undefined || Number.isNaN(Number(value))) {
        return "-";
    }
    return Number(value).toLocaleString(undefined, { maximumFractionDigits: 2 });
}

function formatCell(value) {
    if (value === null || value === undefined || value === "") {
        return "-";
    }
    return String(value);
}

function isValidEmail(value) {
    return /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(value);
}

function escapeHtml(value) {
    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}












