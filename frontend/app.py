# ============================================================
# app.py — Enterprise War Room Frontend
# ============================================================

import streamlit as st
import requests
import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional

# Configuration
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(
    page_title="Strategic AI War Room",
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for enterprise look
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f2937;
        margin-bottom: 1rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        margin: 0.5rem 0;
    }
    .status-badge {
        padding: 0.25rem 0.75rem;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.875rem;
        display: inline-block;
    }
    .status-critical { background: #ef4444; color: white; }
    .status-high { background: #f59e0b; color: white; }
    .status-normal { background: #10b981; color: white; }
    .status-resolved { background: #6b7280; color: white; }
    
    .team-card {
        border: 2px solid #e5e7eb;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
        background: white;
    }
    .team-standby { border-left: 4px solid #9ca3af; }
    .team-investigating { border-left: 4px solid #3b82f6; }
    .team-blocked { border-left: 4px solid #ef4444; }
    .team-found { border-left: 4px solid #10b981; }
    
    .message-system {
        background: #f3f4f6;
        border-left: 4px solid #6b7280;
        padding: 0.75rem;
        margin: 0.5rem 0;
        border-radius: 4px;
    }
    .message-engineer {
        background: #dbeafe;
        border-left: 4px solid #3b82f6;
        padding: 0.75rem;
        margin: 0.5rem 0;
        border-radius: 4px;
    }
    .message-agent {
        background: #fef3c7;
        border-left: 4px solid #f59e0b;
        padding: 0.75rem;
        margin: 0.5rem 0;
        border-radius: 4px;
    }
    .message-commander {
        background: #fce7f3;
        border-left: 4px solid #ec4899;
        padding: 0.75rem;
        margin: 0.5rem 0;
        border-radius: 4px;
        font-weight: 500;
    }
    
    .action-pending { background: #fef3c7; }
    .action-in_progress { background: #dbeafe; }
    .action-completed { background: #d1fae5; }
    .action-blocked { background: #fee2e2; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# Enhanced API Helpers with Better Error Handling
# ─────────────────────────────────────────────

def api_get(endpoint: str) -> Optional[Any]:
    """GET request to backend with improved error handling"""
    try:
        url = f"{BACKEND_URL}{endpoint}"
        st.session_state['last_api_call'] = url  # For debugging
        
        r = requests.get(url, timeout=10)
        
        if r.status_code == 200:
            return r.json()
        else:
            st.error(f"API Error ({r.status_code}): {r.text}")
            return None
            
    except requests.exceptions.ConnectionError:
        st.error(f"❌ Cannot connect to backend at {BACKEND_URL}. Make sure the server is running.")
        return None
    except requests.exceptions.Timeout:
        st.error("❌ Backend request timed out. Please try again.")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"❌ Request failed: {str(e)}")
        return None
    except json.JSONDecodeError:
        st.error("❌ Invalid response from backend (not JSON)")
        return None
    except Exception as e:
        st.error(f"❌ Unexpected error: {str(e)}")
        return None


def api_post(endpoint: str, payload: Dict) -> Optional[Any]:
    """POST request to backend with improved error handling"""
    try:
        url = f"{BACKEND_URL}{endpoint}"
        st.session_state['last_api_call'] = url
        st.session_state['last_payload'] = payload
        
        r = requests.post(url, json=payload, timeout=10)
        
        if r.status_code == 200:
            return r.json()
        elif r.status_code == 500:
            # Try to parse error details
            try:
                error_detail = r.json()
                st.error(f"❌ Server Error: {error_detail.get('detail', 'Unknown error')}")
            except:
                st.error(f"❌ Server Error (500): {r.text}")
            return None
        else:
            st.error(f"❌ API Error ({r.status_code}): {r.text}")
            return None
            
    except requests.exceptions.ConnectionError:
        st.error(f"❌ Cannot connect to backend at {BACKEND_URL}. Make sure the server is running.")
        return None
    except requests.exceptions.Timeout:
        st.error("❌ Backend request timed out. Please try again.")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"❌ Request failed: {str(e)}")
        return None
    except Exception as e:
        st.error(f"❌ Unexpected error: {str(e)}")
        return None


def format_timestamp(ts: str) -> str:
    """Format ISO timestamp to readable format"""
    try:
        dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
        return dt.strftime("%H:%M:%S")
    except:
        return ts


def get_status_badge(status: str) -> str:
    """Get HTML badge for status"""
    status_classes = {
        "declared": "status-critical",
        "investigating": "status-high",
        "identified": "status-high",
        "mitigating": "status-normal",
        "resolved": "status-resolved",
        "P0": "status-critical",
        "P1": "status-critical",
        "P2": "status-high",
        "P3": "status-normal",
        "P4": "status-normal",
    }
    css_class = status_classes.get(status, "status-normal")
    return f'<span class="status-badge {css_class}">{status}</span>'


# ─────────────────────────────────────────────
# Sidebar Navigation
# ─────────────────────────────────────────────

with st.sidebar:
    st.markdown("# 🚨 War Room")
    
    page = st.radio(
        "Navigate",
        ["Dashboard", "Create Incident", "Active Incidents", "Resolved Incidents"],
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    st.markdown("### Quick Stats")
    
    all_incidents = api_get("/incidents") or []
    active_count = len([i for i in all_incidents if i.get("status") not in ["resolved", "postmortem"]])
    
    st.metric("Active Incidents", active_count)
    st.metric("Total Incidents", len(all_incidents))
    
    # Debug info (remove in production)
    if st.checkbox("Show Debug Info"):
        st.json({
            "backend_url": BACKEND_URL,
            "last_call": st.session_state.get('last_api_call', 'None'),
            "last_payload": st.session_state.get('last_payload', 'None')
        })


# ─────────────────────────────────────────────
# Page: Dashboard
# ─────────────────────────────────────────────

if page == "Dashboard":
    st.markdown('<div class="main-header">🎯 Strategic Command Dashboard</div>', unsafe_allow_html=True)
    
    incidents = api_get("/incidents?status=investigating") or []
    
    if not incidents:
        st.info("✅ No active incidents. System operational.")
    else:
        # Show active incidents
        for inc in incidents[:5]:
            with st.container():
                cols = st.columns([3, 1, 1, 1])
                
                with cols[0]:
                    st.markdown(f"**{inc['title']}**")
                    st.caption(inc.get('affected_system', 'N/A'))
                
                with cols[1]:
                    st.markdown(get_status_badge(inc['severity']), unsafe_allow_html=True)
                
                with cols[2]:
                    st.markdown(get_status_badge(inc['status']), unsafe_allow_html=True)
                
                with cols[3]:
                    if st.button("Open", key=f"dash_{inc['id']}"):
                        st.session_state.selected_incident = inc['id']
                        st.rerun()
                
                st.markdown("---")


# ─────────────────────────────────────────────
# Page: Create Incident
# ─────────────────────────────────────────────

elif page == "Create Incident":
    st.markdown('<div class="main-header">🆕 Declare New Incident</div>', unsafe_allow_html=True)
    
    with st.form("create_incident_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            title = st.text_input("Incident Title *", placeholder="e.g., Database Connection Pool Exhaustion")
            affected_system = st.text_input("Affected System *", placeholder="e.g., Production Database Cluster")
            severity = st.selectbox("Severity *", ["P0", "P1", "P2", "P3", "P4"], index=1)
        
        with col2:
            commander = st.text_input("Incident Commander", placeholder="Optional")
            
            st.markdown("##### Impact Assessment")
            affected_users = st.number_input("Affected Users (approx)", min_value=0, value=0, step=100)
            affected_services = st.text_input("Affected Services", placeholder="Comma-separated")
        
        description = st.text_area(
            "Description *",
            placeholder="Detailed description of the incident, symptoms, and initial observations...",
            height=150
        )
        
        submitted = st.form_submit_button("🚀 Declare Incident", use_container_width=True)
        
        if submitted:
            if not title or not description or not affected_system:
                st.error("⚠️ Please fill in all required fields (marked with *)")
            else:
                # Build payload
                payload = {
                    "title": title,
                    "description": description,
                    "severity": severity,
                    "affected_system": affected_system,
                    "incident_commander": commander if commander else None,
                }
                
                # Add impact only if there's data
                if affected_users > 0 or affected_services:
                    payload["impact"] = {}
                    if affected_users > 0:
                        payload["impact"]["affected_users"] = affected_users
                    if affected_services:
                        payload["impact"]["affected_services"] = [s.strip() for s in affected_services.split(",") if s.strip()]
                
                # Show progress
                with st.spinner("Declaring incident..."):
                    result = api_post("/incidents", payload)
                
                if result:
                    st.success("✅ Incident declared successfully! War Room activated.")
                    st.balloons()
                    st.session_state.selected_incident = result.get('id')
                    st.rerun()
                else:
                    st.error("❌ Failed to declare incident. Please check the backend logs.")


# ─────────────────────────────────────────────
# Page: Active/Resolved Incidents
# ─────────────────────────────────────────────

elif page in ["Active Incidents", "Resolved Incidents"]:
    status_filter = None if page == "Active Incidents" else "resolved"
    
    st.markdown(f'<div class="main-header">📋 {page}</div>', unsafe_allow_html=True)
    
    incidents = api_get(f"/incidents{'?status=' + status_filter if status_filter else ''}") or []
    
    if not incidents:
        st.info(f"No {page.lower()} found.")
    else:
        for inc in incidents:
            with st.expander(f"**{inc['title']}** - {inc['severity']}", expanded=False):
                cols = st.columns([2, 1, 1, 1])
                
                with cols[0]:
                    st.write(f"**System:** {inc.get('affected_system', 'N/A')}")
                    if inc.get('incident_commander'):
                        st.write(f"**Commander:** {inc['incident_commander']}")
                
                with cols[1]:
                    st.markdown(get_status_badge(inc['severity']), unsafe_allow_html=True)
                
                with cols[2]:
                    st.markdown(get_status_badge(inc['status']), unsafe_allow_html=True)
                
                with cols[3]:
                    if st.button("View Details", key=f"view_{inc['id']}"):
                        st.session_state.selected_incident = inc['id']
                        st.rerun()


# ─────────────────────────────────────────────
# Incident Detail View (shown when incident selected)
# ─────────────────────────────────────────────

if 'selected_incident' in st.session_state:
    incident_id = st.session_state.selected_incident
    
    # Clear button
    if st.sidebar.button("← Back to Dashboard"):
        del st.session_state.selected_incident
        st.rerun()
    
    # Load incident data with loading indicator
    with st.spinner("Loading incident details..."):
        incident = api_get(f"/incidents/{incident_id}")
        stats = api_get(f"/incidents/{incident_id}/stats")
    
    if not incident:
        st.error("Incident not found")
        del st.session_state.selected_incident
        st.rerun()
    
    # Header
    st.markdown(f'<div class="main-header">{incident["title"]}</div>', unsafe_allow_html=True)
    
    # Top metrics
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Severity", incident['severity'])
    with col2:
        status_display = incident['status'].title() if isinstance(incident['status'], str) else str(incident['status'])
        st.metric("Status", status_display)
    with col3:
        st.metric("Teams Active", stats.get('teams_active', 0) if stats else 0)
    with col4:
        st.metric("Findings", stats.get('total_findings', 0) if stats else 0)
    with col5:
        confidence = 0
        if incident.get('hypothesis') and isinstance(incident['hypothesis'], dict):
            confidence = incident['hypothesis'].get('confidence', 0)
        st.metric("Confidence", f"{confidence:.0%}")
    
    st.markdown("---")
    
    # Main content tabs - add Team Debate if collaboration is active
    base_tabs = ["🧵 War Room", "📊 Overview", "🎯 Actions", "📈 Timeline", "👥 Teams"]
    
    if incident.get('collaboration_active'):
        base_tabs.insert(1, "🤝 Team Debate")
        tabs = st.tabs(base_tabs)
        tab1, tab_debate, tab2, tab3, tab4, tab5 = tabs
    else:
        tabs = st.tabs(base_tabs)
        tab1, tab2, tab3, tab4, tab5 = tabs
        tab_debate = None
    
    # Tab 1: War Room (Thread Communications)
    with tab1:
        threads = incident.get('threads', [])
        
        if not threads:
            st.warning("No threads available for this incident.")
        else:
            # Thread selector
            selected_thread = st.selectbox(
                "Select Thread",
                threads,
                format_func=lambda x: f"{'📋 ' if x == 'summary' else '🔧 '}{x.upper()} TEAM"
            )
            
            st.markdown(f"### {selected_thread.upper()} Thread")
            
            # Load messages
            messages = api_get(f"/incidents/{incident_id}/threads/{selected_thread}") or []
            
            # Message display area
            message_container = st.container()
            
            with message_container:
                if not messages:
                    st.info(f"No messages in {selected_thread} thread yet.")
                else:
                    for msg in messages:
                        sender_type = msg.get('sender_type', 'engineer')
                        css_class = f"message-{sender_type}"
                        
                        # Emoji based on sender type
                        emoji = {
                            'system': '🟢',
                            'engineer': '👤',
                            'agent': '🤖',
                            'commander': '⭐'
                        }.get(sender_type, '💬')
                        
                        is_critical = msg.get('is_critical', False)
                        
                        st.markdown(
                            f'<div class="{css_class}">'
                            f'<strong>{emoji} {msg["sender"]}</strong> '
                            f'<span style="float:right;color:#6b7280;font-size:0.875rem;">{format_timestamp(msg.get("timestamp", ""))}</span>'
                            f'{"<br><span style=\"color:red;font-weight:bold;\">🚨 CRITICAL</span>" if is_critical else ""}'
                            f'<br>{msg["content"]}'
                            f'</div>',
                            unsafe_allow_html=True
                        )
            
            st.markdown("---")
            
            # Input form (only for non-summary threads)
            if selected_thread != "summary":
                st.markdown(f"### 📝 Post Update to {selected_thread.upper()}")
                
                with st.form(f"post_{selected_thread}", clear_on_submit=True):
                    col_name, col_priority = st.columns([3, 1])
                    
                    with col_name:
                        engineer_name = st.text_input(
                            "Your Name",
                            key=f"name_{selected_thread}",
                            placeholder="Engineer Name"
                        )
                    
                    with col_priority:
                        priority = st.selectbox(
                            "Priority",
                            ["normal", "high", "critical"],
                            key=f"priority_{selected_thread}"
                        )
                    
                    message_input = st.text_area(
                        "Update",
                        key=f"msg_{selected_thread}",
                        placeholder="Share your findings, blockers, or questions...",
                        height=100
                    )
                    
                    submit_msg = st.form_submit_button("📤 Send Update", use_container_width=True)
                    
                    if submit_msg:
                        if engineer_name and message_input:
                            payload = {
                                "thread": selected_thread,
                                "engineer_name": engineer_name,
                                "content": message_input,
                                "priority": priority
                            }
                            
                            result = api_post(f"/incidents/{incident_id}/message", payload)
                            
                            if result:
                                st.success("✅ Update posted!")
                                st.rerun()
                        else:
                            st.warning("Please enter your name and message.")
    
    # Team Debate Tab (only shown when collaboration is active)
    if tab_debate is not None:
        with tab_debate:
            st.markdown("### 🤝 Team Collaboration Dialogue")
            
            collab_teams = incident.get('collaboration_teams', [])
            collab_consensus = incident.get('collaboration_consensus')
            
            if not collab_teams:
                st.info("No active collaboration at this time.")
            else:
                # Show participating teams
                st.markdown(f"**Participating Teams:** {', '.join([t.upper() for t in collab_teams])}")
                st.markdown("---")
                
                # Show consensus if reached
                if collab_consensus:
                    consensus_type = collab_consensus.get('consensus_type', 'unknown')
                    
                    emoji_map = {
                        'unanimous': '✅',
                        'majority': '🤝',
                        'commander_decision': '⚖️'
                    }
                    emoji = emoji_map.get(consensus_type, '✅')
                    
                    st.success(f"{emoji} **CONSENSUS REACHED**")
                    
                    cols = st.columns([2, 1])
                    with cols[0]:
                        st.markdown(f"**Root Cause:**\n\n{collab_consensus.get('consensus_hypothesis')}")
                    with cols[1]:
                        st.metric("Confidence", f"{collab_consensus.get('confidence', 0):.0%}")
                        st.caption(f"Type: {consensus_type.replace('_', ' ').title()}")
                    
                    st.markdown("**Supporting Teams:**")
                    st.write(", ".join([t.upper() for t in collab_consensus.get('supporting_teams', [])]))
                    
                    with st.expander("📝 Reasoning"):
                        st.write(collab_consensus.get('reasoning'))
                    
                    st.markdown("---")
                
                # Show dialogue history from each team
                st.markdown("### 💬 Dialogue History")
                
                for team in collab_teams:
                    with st.expander(f"{team.upper()} Team Dialogue", expanded=not collab_consensus):
                        messages = api_get(f"/incidents/{incident_id}/threads/{team}") or []
                        
                        # Filter to collaboration messages (from agents, marked with specific keywords)
                        collab_messages = [
                            msg for msg in messages
                            if msg.get('sender_type') == 'agent' and
                            any(keyword in msg.get('content', '').upper() 
                                for keyword in ['MY POSITION', 'CRITIQUE', 'MY RESPONSE', 'CONSENSUS'])
                        ]
                        
                        if not collab_messages:
                            st.info(f"No collaboration messages from {team} team yet.")
                        else:
                            for msg in collab_messages:
                                # Determine message type from content
                                content = msg.get('content', '')
                                
                                if 'MY POSITION' in content:
                                    st.markdown('<div style="background:#e3f2fd;padding:1rem;margin:0.5rem 0;border-radius:8px;border-left:4px solid #2196f3">', unsafe_allow_html=True)
                                    st.markdown("**🧠 Initial Position**")
                                elif 'CRITIQUE' in content:
                                    st.markdown('<div style="background:#fff3e0;padding:1rem;margin:0.5rem 0;border-radius:8px;border-left:4px solid #ff9800">', unsafe_allow_html=True)
                                    st.markdown("**💬 Critique**")
                                elif 'MY RESPONSE' in content:
                                    st.markdown('<div style="background:#f3e5f5;padding:1rem;margin:0.5rem 0;border-radius:8px;border-left:4px solid #9c27b0">', unsafe_allow_html=True)
                                    st.markdown("**🔄 Response & Revision**")
                                else:
                                    st.markdown('<div style="background:#f5f5f5;padding:1rem;margin:0.5rem 0;border-radius:8px">', unsafe_allow_html=True)
                                
                                st.markdown(content)
                                st.caption(f"Timestamp: {format_timestamp(msg.get('timestamp', ''))}")
                                st.markdown('</div>', unsafe_allow_html=True)
                
                # Show process explanation
                with st.expander("ℹ️ About Team Collaboration"):
                    st.markdown("""
                    **How it works:**
                    
                    1. **Strategic Commander identifies** 2-3 teams with overlapping or conflicting findings
                    2. **Each team presents** their hypothesis with evidence
                    3. **Teams critique** each other's positions constructively
                    4. **Teams respond** and revise their hypotheses based on feedback
                    5. **Commander facilitates** consensus among teams
                    
                    This collaborative dialogue helps reach more accurate root cause analysis by combining
                    expertise from multiple domains.
                    """)
    
    # Tab 2: Overview
    with tab2:
        col_left, col_right = st.columns([2, 1])
        
        with col_left:
            st.markdown("### 📝 Incident Details")
            st.write(f"**Description:** {incident['description']}")
            st.write(f"**Affected System:** {incident['affected_system']}")
            if incident.get('incident_commander'):
                st.write(f"**Commander:** {incident['incident_commander']}")
            
            st.markdown("### 💡 Current Hypothesis")
            if incident.get('hypothesis') and isinstance(incident['hypothesis'], dict):
                hyp = incident['hypothesis']
                st.success(f"**Root Cause:** {hyp.get('root_cause', 'Unknown')}")
                st.progress(hyp.get('confidence', 0))
                st.caption(f"Confidence: {hyp.get('confidence', 0):.0%} | Version: {hyp.get('version', 1)}")
                
                if hyp.get('supporting_evidence'):
                    st.markdown("**Evidence:**")
                    for evidence in hyp['supporting_evidence']:
                        st.write(f"- {evidence}")
            else:
                st.info("No hypothesis formed yet. Investigation in progress.")
        
        with col_right:
            st.markdown("### 📊 Impact")
            impact = incident.get('impact', {})
            if impact and isinstance(impact, dict):
                if impact.get('affected_users'):
                    st.metric("Affected Users", f"{impact['affected_users']:,}")
                if impact.get('affected_services'):
                    st.write("**Services:**")
                    for svc in impact['affected_services']:
                        st.write(f"- {svc}")
            else:
                st.info("No impact data available.")
            
            st.markdown("### 🎯 Quick Actions")
            
            if incident.get('status') != "resolved":
                if st.button("🔄 Trigger Commander Analysis", use_container_width=True):
                    with st.spinner("Analyzing..."):
                        result = api_post(f"/incidents/{incident_id}/analyze", {})
                        if result:
                            st.success("Analysis triggered!")
                            st.rerun()
                
                if st.button("📣 Generate Executive Summary", use_container_width=True):
                    summary_data = api_get(f"/incidents/{incident_id}/executive-summary")
                    if summary_data and isinstance(summary_data, dict):
                        st.success(summary_data.get('summary', 'No summary available'))
                
                if st.button("✅ Resolve Incident", use_container_width=True):
                    result = api_post(f"/incidents/{incident_id}/resolve", {})
                    if result:
                        st.success("Incident marked as resolved!")
                        st.rerun()
    
    # Tab 3: Actions
    with tab3:
        st.markdown("### 🎯 Assigned Actions")
        
        actions = api_get(f"/incidents/{incident_id}/actions") or []
        
        if not actions:
            st.info("No actions assigned yet.")
        else:
            # Filter controls
            col_filter, col_sort = st.columns(2)
            
            with col_filter:
                filter_status = st.multiselect(
                    "Filter by Status",
                    ["pending", "in_progress", "completed", "blocked"],
                    default=["pending", "in_progress", "blocked"]
                )
            
            with col_sort:
                filter_priority = st.multiselect(
                    "Filter by Priority",
                    ["critical", "high", "normal", "low"],
                    default=["critical", "high", "normal"]
                )
            
            # Filter actions
            filtered_actions = [
                a for a in actions
                if a.get('status') in filter_status and a.get('priority') in filter_priority
            ]
            
            st.caption(f"Showing {len(filtered_actions)} of {len(actions)} actions")
            
            for action in filtered_actions:
                status_class = f"action-{action.get('status', 'pending')}"
                
                with st.container():
                    st.markdown(f'<div class="{status_class}" style="padding:1rem;margin:0.5rem 0;border-radius:8px;">', unsafe_allow_html=True)
                    
                    cols = st.columns([3, 1, 1])
                    
                    with cols[0]:
                        priority_emoji = {
                            'critical': '🔴',
                            'high': '🟠',
                            'normal': '🟢',
                            'low': '⚪'
                        }.get(action.get('priority', 'normal'), '🟢')
                        
                        st.markdown(f"{priority_emoji} **{action.get('description', 'No description')}**")
                        st.caption(f"Assigned to: {action.get('assigned_to', 'Unknown').upper()}")
                    
                    with cols[1]:
                        st.markdown(get_status_badge(action.get('status', 'unknown')), unsafe_allow_html=True)
                    
                    with cols[2]:
                        if action.get('status') != "completed":
                            current_status = action.get('status', 'pending')
                            status_options = ["pending", "in_progress", "completed", "blocked"]
                            current_index = status_options.index(current_status) if current_status in status_options else 0
                            
                            new_status = st.selectbox(
                                "Update",
                                status_options,
                                key=f"action_status_{action.get('id', 'unknown')}",
                                index=current_index,
                                label_visibility="collapsed"
                            )
                            
                            if new_status != current_status and st.button("Update", key=f"update_{action.get('id', 'unknown')}"):
                                payload = {"action_id": action.get('id'), "status": new_status}
                                result = api_post(f"/incidents/{incident_id}/actions/{action.get('id')}", payload)
                                if result:
                                    st.rerun()
                    
                    st.markdown('</div>', unsafe_allow_html=True)
    
    # Tab 4: Timeline
    with tab4:
        st.markdown("### 📈 Incident Timeline")
        
        timeline = incident.get('timeline', [])
        
        if not timeline:
            st.info("No timeline events yet.")
        else:
            # Reverse to show newest first
            for event in reversed(timeline[-50:]):
                event_type = event.get('event_type', 'info')
                
                emoji = {
                    'detection': '🔍',
                    'escalation': '⬆️',
                    'finding': '💡',
                    'action': '🎯',
                    'action_assigned': '📝',
                    'action_update': '📋',
                    'hypothesis_formed': '💭',
                    'hypothesis_updated': '🔄',
                    'team_coordination': '🤝',
                    'strategic_analysis': '🧠',
                    'resolution': '✅'
                }.get(event_type, '📌')
                
                timestamp = format_timestamp(event.get('timestamp', ''))
                team = event.get('team', '')
                team_badge = f"[{team.upper()}]" if team else ""
                
                st.markdown(
                    f"**{timestamp}** {emoji} {team_badge} {event.get('description', 'No description')}"
                )
                st.markdown("---")
    
    # Tab 5: Teams
    with tab5:
        st.markdown("### 👥 Team Coordination")
        
        team_states = incident.get('team_states', {})
        
        if not team_states:
            st.info("No team data available.")
        else:
            # Show team cards
            cols = st.columns(3)
            
            for idx, (team_name, state) in enumerate(team_states.items()):
                with cols[idx % 3]:
                    if isinstance(state, dict):
                        status = state.get('status', 'standby')
                        status_class = f"team-{status}"
                        
                        st.markdown(f'<div class="team-card {status_class}">', unsafe_allow_html=True)
                        
                        st.markdown(f"### {team_name.upper()}")
                        st.markdown(get_status_badge(status), unsafe_allow_html=True)
                        
                        st.metric("Findings", state.get('findings_count', 0))
                        st.metric("Active Tasks", len(state.get('active_tasks', [])))
                        
                        if state.get('assigned_engineers'):
                            st.caption("Engineers: " + ", ".join(state['assigned_engineers']))
                        
                        if state.get('blocked_reason'):
                            st.error(f"⚠️ Blocked: {state['blocked_reason']}")
                        
                        if state.get('needs_help_from'):
                            st.warning(f"Needs help from: {', '.join(state['needs_help_from'])}")
                        
                        st.markdown('</div>', unsafe_allow_html=True)