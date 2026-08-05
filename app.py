import logging
from pathlib import Path

import streamlit as st

import lakebase
import schema

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(page_title="Support Tickets", layout="wide")

STATUSES = ["open", "in_progress", "resolved"]
PRIORITIES = ["low", "medium", "high", "urgent"]
CATEGORIES = ["hardware", "software", "network", "access", "other"]

TITLE_MAX_LEN = 200
NAME_MAX_LEN = 100
MESSAGE_MAX_LEN = 5000

STATUS_BADGE_CLASS = {
    "open": "badge-tangerine",
    "in_progress": "badge-pine",
    "resolved": "badge-gold",
}
PRIORITY_BADGE_CLASS = {
    "urgent": "badge-urgent",
    "high": "badge-high",
    "medium": "badge-pine",
    "low": "badge-neutral",
}


def load_css():
    css_path = Path(__file__).parent / "styles.css"
    st.markdown(f"<style>{css_path.read_text()}</style>", unsafe_allow_html=True)


def safe_run_query(sql, params=None, error_message="Couldn't load data — please try again."):
    try:
        return lakebase.run_query(sql, params)
    except Exception:
        logger.exception("Query failed: %s", sql)
        st.error(error_message)
        return []


def safe_run_write(sql, params=None, error_message="Couldn't save your changes — please try again."):
    try:
        lakebase.run_write(sql, params)
        return True
    except Exception:
        logger.exception("Write failed: %s", sql)
        st.error(error_message)
        return False


def validate_text(value, field_label, max_len, required=True):
    value = (value or "").strip()
    if required and not value:
        return None, f"{field_label} is required."
    if len(value) > max_len:
        return None, f"{field_label} must be {max_len} characters or fewer (currently {len(value)})."
    return value, None


def badge_html(label, css_class):
    return f'<span class="badge {css_class}">{label.replace("_", " ").title()}</span>'


def ticket_badges_html(t):
    return (
        badge_html(t["status"], STATUS_BADGE_CLASS.get(t["status"], "badge-neutral"))
        + badge_html(t["priority"], PRIORITY_BADGE_CLASS.get(t["priority"], "badge-neutral"))
        + badge_html(t["category"], "badge-neutral")
    )


def fetch_tickets(statuses, priorities, categories):
    # An empty selection on a filter dimension means "don't filter on this" —
    # so no filters selected at all shows every ticket, and picking just one
    # value in one dimension (e.g. status=open) doesn't also require picking
    # something in the others.
    clauses, params = [], []
    if statuses:
        clauses.append("status = ANY(%s)")
        params.append(statuses)
    if priorities:
        clauses.append("priority = ANY(%s)")
        params.append(priorities)
    if categories:
        clauses.append("category = ANY(%s)")
        params.append(categories)
    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = (
        "SELECT ticket_id, title, status, priority, category, created_by, created_at "
        f"FROM tickets {where_sql} ORDER BY created_at DESC"
    )
    return safe_run_query(sql, tuple(params) if params else None)


load_css()

try:
    schema.create_tables()
except Exception:
    logger.exception("Failed to initialize schema")
    st.error("Couldn't connect to the database — please try again shortly.")
    st.stop()

st.title("Internal Support Tickets")

# --- Stats ---
st.markdown("### Overview")
total_row = safe_run_query("SELECT COUNT(*) AS count FROM tickets")
total_count = total_row[0]["count"] if total_row else 0
status_counts = {r["status"]: r["count"] for r in safe_run_query("SELECT status, COUNT(*) AS count FROM tickets GROUP BY status")}
priority_counts = {r["priority"]: r["count"] for r in safe_run_query("SELECT priority, COUNT(*) AS count FROM tickets GROUP BY priority")}

stat_cols = st.columns(1 + len(STATUSES))
stat_cols[0].metric("Total tickets", total_count)
for col, status in zip(stat_cols[1:], STATUSES):
    col.metric(status.replace("_", " ").title(), status_counts.get(status, 0))

priority_cols = st.columns(len(PRIORITIES))
for col, priority in zip(priority_cols, PRIORITIES):
    col.metric(f"{priority.title()} priority", priority_counts.get(priority, 0))

st.divider()

# --- Create new ticket ---
with st.expander("➕ Create new ticket"):
    with st.form("new_ticket_form", clear_on_submit=True):
        title = st.text_input("Title")
        created_by = st.text_input("Your name")
        col_a, col_b = st.columns(2)
        with col_a:
            priority = st.selectbox("Priority", PRIORITIES, index=PRIORITIES.index("medium"))
        with col_b:
            category = st.selectbox("Category", CATEGORIES, index=CATEGORIES.index("other"))
        submitted = st.form_submit_button("Create ticket", type="primary")

        if submitted:
            clean_title, title_err = validate_text(title, "Title", TITLE_MAX_LEN)
            clean_name, name_err = validate_text(created_by, "Your name", NAME_MAX_LEN)
            errors = [e for e in (title_err, name_err) if e]

            if errors:
                for e in errors:
                    st.error(e)
            else:
                ok = safe_run_write(
                    "INSERT INTO tickets (title, status, created_by, priority, category) "
                    "VALUES (%s, %s, %s, %s, %s)",
                    (clean_title, "open", clean_name, priority, category),
                    error_message="Couldn't save your ticket — please try again.",
                )
                if ok:
                    st.success("Ticket created!")
                    st.rerun()

st.divider()

# --- Filters ---
st.markdown("### Filters")
st.caption("Leave a filter empty to include every value for it.")
filter_cols = st.columns(3)
with filter_cols[0]:
    selected_statuses = st.multiselect("Status", STATUSES, default=[], key="filter_status")
with filter_cols[1]:
    selected_priorities = st.multiselect("Priority", PRIORITIES, default=[], key="filter_priority")
with filter_cols[2]:
    selected_categories = st.multiselect("Category", CATEGORIES, default=[], key="filter_category")

st.divider()

# --- List tickets ---
tickets = fetch_tickets(selected_statuses, selected_priorities, selected_categories)

if not tickets:
    any_filter_set = selected_statuses or selected_priorities or selected_categories
    if any_filter_set:
        st.info("No tickets match the current filters.")
    else:
        st.info("No tickets yet.")
else:
    ticket_ids = [t["ticket_id"] for t in tickets]
    if st.session_state.get("selected_ticket_id") not in ticket_ids:
        st.session_state.selected_ticket_id = ticket_ids[0]

    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("All tickets")
        st.caption(f"{len(tickets)} ticket(s)")
        for t in tickets:
            with st.container(border=True):
                # Invisible marker so styles.css can target *this specific*
                # bordered container via a `:has()` selector — st.container
                # has no `key=` support on every Streamlit version, so this
                # is the version-safe way to scope the card CSS precisely.
                st.markdown('<span class="ticket-card-marker"></span>', unsafe_allow_html=True)
                st.markdown(f"**#{t['ticket_id']} — {t['title']}**")
                st.caption(f"by {t['created_by']}")
                st.markdown(ticket_badges_html(t), unsafe_allow_html=True)
                is_selected = t["ticket_id"] == st.session_state.selected_ticket_id
                if st.button(
                    "Selected" if is_selected else "View",
                    key=f"select_{t['ticket_id']}",
                    type="primary" if is_selected else "secondary",
                    disabled=is_selected,
                    use_container_width=True,
                ):
                    st.session_state.selected_ticket_id = t["ticket_id"]
                    st.rerun()

    with col2:
        selected_id = st.session_state.selected_ticket_id
        selected_ticket = next(t for t in tickets if t["ticket_id"] == selected_id)

        st.subheader(selected_ticket["title"])
        st.caption(f"Created by {selected_ticket['created_by']} on {selected_ticket['created_at']}")
        st.markdown(ticket_badges_html(selected_ticket), unsafe_allow_html=True)

        # --- Update status ---
        new_status = st.selectbox(
            "Status",
            STATUSES,
            index=STATUSES.index(selected_ticket["status"]) if selected_ticket["status"] in STATUSES else 0,
            key=f"status_select_{selected_id}",
        )
        if new_status != selected_ticket["status"]:
            if st.button("Update status", type="primary"):
                ok = safe_run_write(
                    "UPDATE tickets SET status = %s WHERE ticket_id = %s",
                    (new_status, selected_id),
                    error_message="Couldn't update the status — please try again.",
                )
                if ok:
                    st.success("Status updated!")
                    st.rerun()

        st.markdown("### Messages")
        messages = safe_run_query(
            "SELECT message_text, author, created_at FROM ticket_messages "
            "WHERE ticket_id = %s ORDER BY created_at ASC",
            (selected_id,),
        )
        for m in messages:
            st.markdown(f"**{m['author']}** _{m['created_at']}_")
            st.write(m["message_text"])
            st.divider()

        # --- Add message ---
        with st.form(f"new_message_form_{selected_id}", clear_on_submit=True):
            author = st.text_input("Your name", key="msg_author")
            message_text = st.text_area("Message")
            msg_submitted = st.form_submit_button("Add message", type="primary")
            if msg_submitted:
                clean_author, author_err = validate_text(author, "Name", NAME_MAX_LEN)
                clean_message, message_err = validate_text(message_text, "Message", MESSAGE_MAX_LEN)
                errors = [e for e in (author_err, message_err) if e]

                if errors:
                    for e in errors:
                        st.error(e)
                else:
                    ok = safe_run_write(
                        "INSERT INTO ticket_messages (ticket_id, message_text, author) VALUES (%s, %s, %s)",
                        (selected_id, clean_message, clean_author),
                        error_message="Couldn't add your message — please try again.",
                    )
                    if ok:
                        st.success("Message added!")
                        st.rerun()

        # --- Delete ticket ---
        st.markdown('<div class="danger-zone">', unsafe_allow_html=True)
        with st.expander("⚠️ Delete this ticket"):
            st.caption("This permanently deletes the ticket and all of its messages. This cannot be undone.")
            confirm_delete = st.checkbox(
                "I understand this is permanent", key=f"confirm_delete_{selected_id}"
            )
            if st.button(
                "Delete ticket",
                key=f"delete_btn_{selected_id}",
                type="primary",
                disabled=not confirm_delete,
            ):
                # Single statement (CTE) so the message + ticket delete commit atomically.
                ok = safe_run_write(
                    "WITH deleted_messages AS ("
                    "  DELETE FROM ticket_messages WHERE ticket_id = %s"
                    ") DELETE FROM tickets WHERE ticket_id = %s",
                    (selected_id, selected_id),
                    error_message="Couldn't delete the ticket — please try again.",
                )
                if ok:
                    st.session_state.selected_ticket_id = None
                    st.success("Ticket deleted.")
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
