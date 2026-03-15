from __future__ import annotations

import os
import smtplib
import threading
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from backend.settings_manager import SettingsManager


SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
settings_manager = SettingsManager()


def send_anomaly_alert(dataset_name: str, anomaly_count: int) -> None:
    """Send anomaly alerts in a background thread so dataset processing stays responsive."""
    if anomaly_count <= 0:
        return

    threading.Thread(
        target=_send_anomaly_alert_sync,
        args=(dataset_name, anomaly_count),
        daemon=True,
    ).start()


def _send_anomaly_alert_sync(dataset_name: str, anomaly_count: int) -> None:
    settings = settings_manager.get_email_settings(include_password=True)
    sender_email = settings.get("sender_email", "").strip() or os.getenv("SENDER_EMAIL", "").strip()
    sender_password = settings.get("sender_password", "") or os.getenv("SENDER_PASSWORD", "").strip()
    receiver_email = settings.get("receiver_email", "").strip() or os.getenv("RECEIVER_EMAIL", "").strip()

    if not sender_email or not sender_password or not receiver_email:
        print("Email alert configuration not set.")
        return

    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = receiver_email
    message["Subject"] = "Dataset Anomaly Alert"
    message.attach(
        MIMEText(
            (
                "Hello,\n\n"
                "The anomaly detection system has detected unusual values in the dataset.\n\n"
                f"Dataset Name: {dataset_name}\n"
                f"Number of Anomalies Detected: {anomaly_count}\n\n"
                "Please review the anomaly section in the dashboard.\n\n"
                "Regards\n"
                "AI Data Insight Platform"
            ),
            "plain",
        )
    )

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=20) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, [receiver_email], message.as_string())
    except Exception as exc:
        print("Email alert failed:", exc)


class EmailAlert:
    """Compatibility wrapper for older code paths."""

    def send_anomaly_alert(self, dataset_name: str, anomaly_count: int) -> None:
        send_anomaly_alert(dataset_name, anomaly_count)
