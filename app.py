import streamlit as st
import serial
import time
import re
import pandas as pd
import altair as alt
import smtplib
import sqlite3
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from playsound import playsound
import os

# --- PAGE CONFIG ---
st.set_page_config(page_title="PPE Detection System", layout="wide")
st.title("🦺 Real-Time PPE Detection Dashboard")

# --- SESSION STATE INIT ---
if "paused" not in st.session_state:
    st.session_state.paused = False
if "ser" not in st.session_state:
    try:
        st.session_state.ser = serial.Serial("COM3", 115200, timeout=1)  # CHANGE THIS IF NEEDED
        time.sleep(2)
        st.success("Connected to COM3")
    except Exception as e:
        st.error(f"Serial Error: {e}")
        st.stop()

ser = st.session_state.ser

# --- PAUSE BUTTON ---
pause_button = st.button("⏸️ Pause" if not st.session_state.paused else "▶️ Resume")
if pause_button:
    st.session_state.paused = not st.session_state.paused

# --- CONFIG ---
ppe_items = ["Helmet", "Goggle", "Vest", "Unauthorized Labourer"]
detected = {item: False for item in ppe_items}
last_seen = {item: 0 for item in ppe_items}
PERSIST_SECONDS = 3
BUZZER_SOUND = r"C:\Users\keert\Downloads\streamlit_esp32_ppe_app\siren-alert-96052.mp3"
buzzer_played = False

history = []
missing_start_time = None
cooldown_end = datetime.min

# --- DATABASE INIT ---
conn = sqlite3.connect("alerts.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    missing_items TEXT,
    alert_type TEXT,
    status TEXT
)
""")
conn.commit()

# --- SIDEBAR SETTINGS ---
st.sidebar.header("⚙️ Alert Settings")
enable_email = st.sidebar.checkbox("Enable Email Alerts", value=True)
enable_inapp = st.sidebar.checkbox("Enable In-App Alerts", value=True)
alert_threshold = st.sidebar.slider("Alert if PPE missing for (seconds):", 1, 30, 5)
cooldown_seconds = st.sidebar.slider("Cooldown period (seconds):", 10, 300, 60)
monitored_items = ["Helmet", "Goggle", "Vest"]
recipients = st.sidebar.text_area("Recipient Email(s) [comma-separated]:", "22d124@psgitech.ac.in").split(',')

# --- UI PLACEHOLDERS ---
status_container = st.empty()
summary_container = st.empty()
alert_banner = st.empty()
chart_container = st.empty()

# --- EMAIL FUNCTION ---
def send_email(subject, body):
    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = st.secrets["EMAIL_USER"]
        msg["To"] = ", ".join(recipients)
        server = smtplib.SMTP(st.secrets["EMAIL_HOST"], st.secrets["EMAIL_PORT"])
        server.starttls()
        server.login(st.secrets["EMAIL_USER"], st.secrets["EMAIL_PASS"])
        server.sendmail(st.secrets["EMAIL_USER"], recipients, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        st.error(f"Email failed: {e}")
        return False

# --- UI UPDATE FUNCTION ---
def update_ui():
    with status_container.container():
        cols = st.columns(len(ppe_items))
        for idx, item in enumerate(ppe_items):
            color = "red" if (item == "Unauthorized Labourer" and detected[item]) else ("green" if detected[item] else "red")
            symbol = "🛑" if item == "Unauthorized Labourer" and detected[item] else ("🟢" if detected[item] else "🔴")
            cols[idx].markdown(f"<h3 style='color:{color}; text-align:center'>{item}</h3>", unsafe_allow_html=True)
            cols[idx].markdown(f"<h1 style='text-align:center'>{symbol}</h1>", unsafe_allow_html=True)

    if all(detected[i] for i in monitored_items):
        summary_container.success("✅ PPE Verified")
    elif not any(detected[i] for i in monitored_items):
        summary_container.error("❌ No PPE Detected")
    else:
        missing = [k for k in monitored_items if not detected[k]]
        summary_container.warning(f"⚠️ Partial PPE Missing: {', '.join(missing)}")

    if len(history) > 1:
        df = pd.DataFrame(history).reset_index()
        chart = alt.Chart(df.tail(20)).transform_fold(
            ppe_items
        ).mark_line().encode(
            x='index:Q',
            y='value:Q',
            color='key:N'
        ).properties(title="Detection Trend")
        chart_container.altair_chart(chart, use_container_width=True)

# --- ALERT FUNCTION ---
def trigger_alert(missing_items, alert_type):
    now = datetime.now()
    msg = f"🚨 {alert_type}:\n{', '.join(missing_items)}\nTime: {now.strftime('%Y-%m-%d %H:%M:%S')}"
    if enable_email:
        sent = send_email(f"🚨 {alert_type}", msg)
        status = "sent" if sent else "failed"
        cursor.execute("INSERT INTO alerts (timestamp, missing_items, alert_type, status) VALUES (?, ?, ?, ?)",
                       (now, ", ".join(missing_items), alert_type, status))
        conn.commit()
    if enable_inapp:
        alert_banner.warning(f"🚨 {alert_type}: {', '.join(missing_items)} | {now.strftime('%H:%M:%S')}")
        cursor.execute("INSERT INTO alerts (timestamp, missing_items, alert_type, status) VALUES (?, ?, ?, ?)",
                       (now, ", ".join(missing_items), alert_type, "shown"))
        conn.commit()

# --- PARSE LINE FUNCTION ---
def parse_line(line):
    global missing_start_time, cooldown_end, buzzer_played
    now = datetime.now()
    line_lower = line.lower()

    # Detect Unauthorized Labour (British + American spelling)
    if re.search(r"unauthori[sz]ed labour(?!er).*detected", line_lower):
        last_seen["Unauthorized Labourer"] = time.time()

    # Detect PPE items
    for item in monitored_items:
        if item.lower() in line_lower and "not" not in line_lower:
            last_seen[item] = time.time()

    current_time = time.time()
    for item in ppe_items:
        detected[item] = (current_time - last_seen[item]) <= PERSIST_SECONDS

    history.append(detected.copy())

    # Trigger alert for missing PPE
    missing = [item for item in monitored_items if not detected[item]]
    if missing:
        if missing_start_time is None:
            missing_start_time = current_time
        elif current_time - missing_start_time >= alert_threshold and now >= cooldown_end:
            trigger_alert(missing, "PPE Missing")
            cooldown_end = now + timedelta(seconds=cooldown_seconds)
            missing_start_time = None
    else:
        missing_start_time = None
        buzzer_played = False  # Reset buzzer

    # 🔊 Play buzzer if no PPE detected for 5 seconds
    if not any(detected[i] for i in monitored_items):
        if missing_start_time and current_time - missing_start_time >= 5:
            if not buzzer_played:
                if os.path.exists(BUZZER_SOUND):
                    playsound(BUZZER_SOUND)
                buzzer_played = True

    # Trigger alert for unauthorized labourer
    if detected["Unauthorized Labourer"] and now >= cooldown_end:
        trigger_alert(["Unauthorized Labourer"], "Unauthorized Labourer")
        cooldown_end = now + timedelta(seconds=cooldown_seconds)

# --- ALERT HISTORY SIDEBAR ---
with st.sidebar.expander("📜 Alert History"):
    alert_df = pd.read_sql_query("SELECT * FROM alerts ORDER BY timestamp DESC LIMIT 100", conn)
    st.dataframe(alert_df)

# --- MAIN LOOP ---
while True:
    if st.session_state.paused:
        time.sleep(0.5)
        continue

    if ser.in_waiting > 0:
        line = ser.readline().decode('utf-8', errors='ignore').strip()
        if line:
            st.write(f"📨 `{line}`")
            parse_line(line)
            update_ui()