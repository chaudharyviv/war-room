# ============================================================
# app.py — Strategic AI War Room (Frontend)
# ============================================================

import streamlit as st
import requests
import os

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
    except:
        return None


def api_post(endpoint, payload):
    try:
        r = requests.post(f"{BACKEND_URL}{endpoint}", json=payload)
        if r.status_code == 200:
            return r.json()
        return None
    except:
        return None


# ─────────────────────────────────────────────
# Incident Creation Section
# ─────────────────────────────────────────────

st.markdown("## 🆕 Initiate War Room")

with st.form("create_incident_form"):
    title = st.text_input("Incident Title")
    description = st.text_area("Description")
    severity = st.selectbox("Severity", ["P1", "P2", "P3"])
    affected_system = st.text_input("Affected System")

    submitted = st.form_submit_button("🚀 Create Incident")

    if submitted:
        if not title or not description or not affected_system:
            st.error("All fields are required.")
        else:
            payload = {
                "title": title,
                "description": description,
                "severity": severity,
                "affected_system": affected_system
            }

            result = api_post("/incidents", payload)

            if result:
                st.success("War Room initiated successfully.")
                st.rerun()
            else:
                st.error("Failed to create incident.")

st.markdown("---")

# ─────────────────────────────────────────────
# Load Incidents
# ─────────────────────────────────────────────

incidents = api_get("/incidents") or []

if not incidents:
    st.info("No active incidents yet.")
    st.stop()

incident_ids = [i["id"] for i in incidents]
selected_id = st.selectbox("Select Incident", incident_ids)

incident = api_get(f"/incidents/{selected_id}")
findings = api_get(f"/incidents/{selected_id}/findings") or []
timeline = api_get(f"/incidents/{selected_id}/timeline") or []

if not incident:
    st.error("Incident not found.")
    st.stop()

# ─────────────────────────────────────────────
# Incident Overview
# ─────────────────────────────────────────────

st.markdown("## 📊 Incident Overview")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Severity", incident.get("severity"))

with col2:
    st.metric("Status", incident.get("status"))

with col3:
    st.metric("Findings", len(findings))

# ─────────────────────────────────────────────
# Hypothesis
# ─────────────────────────────────────────────

st.markdown("## 🧠 Current Hypothesis")

hypothesis = incident.get("hypothesis")

if hypothesis:
    st.success(f"Root Cause: {hypothesis.get('root_cause')}")
    st.progress(hypothesis.get("confidence", 0))
else:
    st.info("No hypothesis formed yet.")

# ─────────────────────────────────────────────
# Executive Summary
# ─────────────────────────────────────────────

if st.button("📣 Generate Executive Summary"):
    summary = api_get(f"/incidents/{selected_id}/executive-summary")
    if summary:
        st.success(summary.get("summary"))

# ─────────────────────────────────────────────
# Threads
# ─────────────────────────────────────────────

st.markdown("## 🧵 Investigation Threads")

threads = incident.get("threads", [])

for thread in threads:

    if thread == "summary":
        continue

    with st.expander(f"{thread.upper()} TEAM"):

        messages = api_get(
            f"/incidents/{selected_id}/threads/{thread}"
        ) or []

        for msg in messages[-10:]:
            if msg["sender_type"] == "system":
                st.markdown(f"🟢 **SYSTEM:** {msg['content']}")
            elif msg["sender_type"] == "engineer":
                st.markdown(f"👤 **{msg['sender']}**: {msg['content']}")
            else:
                st.markdown(f"🤖 _Agent_: {msg['content']}")

        st.markdown("---")

        engineer_name = st.text_input(
            f"Your Name ({thread})",
            key=f"name_{thread}"
        )

        message_input = st.text_area(
            f"Update for {thread}",
            key=f"msg_{thread}"
        )

        if st.button(f"Send to {thread}", key=f"btn_{thread}"):

            if engineer_name and message_input:
                payload = {
                    "thread": thread,
                    "engineer_name": engineer_name,
                    "content": message_input
                }

                api_post(
                    f"/incidents/{selected_id}/message",
                    payload
                )

                st.rerun()

# ─────────────────────────────────────────────
# Timeline
# ─────────────────────────────────────────────

st.markdown("## 📜 Timeline")

for event in timeline[-20:]:
    st.markdown(
        f"**{event['event_type'].upper()}** "
        f"({event['timestamp']}): {event['description']}"
    )

# ─────────────────────────────────────────────
# Resolve Incident
# ─────────────────────────────────────────────

if incident.get("status") != "resolved":
    if st.button("✅ Resolve Incident"):
        api_post(f"/incidents/{selected_id}/resolve", {})
        st.rerun()
else:
    st.success("Incident resolved.")