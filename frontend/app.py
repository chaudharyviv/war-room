# ============================================================
# app.py — Strategic AI War Room Frontend (Streamlit)
# ============================================================

import streamlit as st
import requests
import os
from datetime import datetime

# ─────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(layout="wide")
st.title("🚨 Strategic AI Incident Commander")


# ─────────────────────────────────────────────
# API Helpers
# ─────────────────────────────────────────────

def api_get(endpoint):
    try:
        r = requests.get(f"{BACKEND_URL}{endpoint}")
        if r.status_code == 200:
            return r.json()
        return None
    except Exception as e:
        st.error(f"API GET Error: {e}")
        return None


def api_post(endpoint, payload):
    try:
        r = requests.post(f"{BACKEND_URL}{endpoint}", json=payload)
        if r.status_code == 200:
            return r.json()
        return None
    except Exception as e:
        st.error(f"API POST Error: {e}")
        return None


# ─────────────────────────────────────────────
# Load Incidents
# ─────────────────────────────────────────────

incidents = api_get("/incidents") or []

if not incidents:
    st.info("No incidents available.")
    st.stop()

incident_ids = [i["id"] for i in incidents]

selected_id = st.selectbox("Select Incident", incident_ids)

incident = api_get(f"/incidents/{selected_id}")
findings = api_get(f"/incidents/{selected_id}/findings") or []

if not incident:
    st.error("Incident not found.")
    st.stop()

# ─────────────────────────────────────────────
# Incident Overview
# ─────────────────────────────────────────────

st.markdown("---")
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Severity", incident.get("severity", "N/A"))

with col2:
    st.metric("Status", incident.get("status", "N/A"))

with col3:
    st.metric("Total Findings", len(findings))

st.markdown("---")

# ─────────────────────────────────────────────
# Hypothesis Panel
# ─────────────────────────────────────────────

st.subheader("🧠 Current Hypothesis")

hypothesis = incident.get("hypothesis")

if hypothesis:
    st.success(f"Root Cause: {hypothesis.get('root_cause')}")
    st.progress(hypothesis.get("confidence", 0))
else:
    st.info("No hypothesis formed yet.")

# ─────────────────────────────────────────────
# Executive Summary
# ─────────────────────────────────────────────

st.markdown("---")
if st.button("📣 Generate Executive Summary"):
    with st.spinner("Generating..."):
        summary = api_get(f"/incidents/{selected_id}/executive-summary")

    if summary:
        st.success(summary.get("summary"))
    else:
        st.error("Failed to generate summary.")

# ─────────────────────────────────────────────
# Threads Section
# ─────────────────────────────────────────────

st.markdown("---")
st.subheader("🧵 Investigation Threads")

threads = incident.get("threads", [])

for thread in threads:

    if thread == "summary":
        continue

    with st.expander(f"{thread.upper()} TEAM"):

        messages = api_get(
            f"/incidents/{selected_id}/threads/{thread}"
        ) or []

        # Display last 10 messages
        for msg in messages[-10:]:
            if msg["sender_type"] == "engineer":
                st.markdown(
                    f"**{msg['sender']}**: {msg['content']}"
                )
            else:
                st.markdown(
                    f"_Agent_: {msg['content']}"
                )

        st.markdown("---")

        engineer_name = st.text_input(
            f"Your Name ({thread})",
            key=f"name_{thread}"
        )

        engineer_message = st.text_area(
            f"Share update for {thread}",
            key=f"msg_{thread}"
        )

        if st.button(f"Send to {thread}", key=f"btn_{thread}"):

            if not engineer_name or not engineer_message:
                st.warning("Please enter your name and message.")
            else:
                payload = {
                    "thread": thread,
                    "engineer_name": engineer_name,
                    "content": engineer_message
                }

                response = api_post(
                    f"/incidents/{selected_id}/message",
                    payload
                )

                if response:
                    st.success("Update sent.")
                    st.rerun()
                else:
                    st.error("Failed to send message.")

# ─────────────────────────────────────────────
# Timeline Section
# ─────────────────────────────────────────────

st.markdown("---")
st.subheader("📜 Timeline")

timeline = api_get(f"/incidents/{selected_id}/timeline") or []

if timeline:
    for event in timeline[-20:]:
        st.markdown(
            f"**{event['event_type'].upper()}** "
            f"({event['timestamp']}): {event['description']}"
        )
else:
    st.info("No timeline events yet.")

# ─────────────────────────────────────────────
# Resolve Incident
# ─────────────────────────────────────────────

st.markdown("---")

if incident.get("status") != "resolved":
    if st.button("✅ Resolve Incident"):
        result = api_post(
            f"/incidents/{selected_id}/resolve",
            {}
        )
        if result:
            st.success("Incident resolved.")
            st.rerun()
else:
    st.success("Incident is resolved.")