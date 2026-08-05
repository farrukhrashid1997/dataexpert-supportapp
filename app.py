import streamlit as st

import lakebase

st.set_page_config(page_title="Support Tickets", layout="wide")

# Run once per session start — safe to call every time, it's idempotent
lakebase.init_schema()

st.title("🎫 Internal Support Tickets")

STATUSES = ["open", "in_progress", "resolved"]

# --- Create new ticket ---
with st.expander("➕ Create new ticket"):
    with st.form("new_ticket_form", clear_on_submit=True):
        title = st.text_input("Title")
        created_by = st.text_input("Your name")
        submitted = st.form_submit_button("Create ticket")
        if submitted:
            if title and created_by:
                lakebase.run_write(
                    "INSERT INTO tickets (title, status, created_by) VALUES (%s, %s, %s)",
                    (title, "open", created_by),
                )
                st.success("Ticket created!")
                st.rerun()
            else:
                st.error("Title and name are required.")

st.divider()

# --- List tickets ---
tickets = lakebase.run_query(
    "SELECT ticket_id, title, status, created_by, created_at FROM tickets ORDER BY created_at DESC"
)

if not tickets:
    st.info("No tickets yet.")
else:
    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("All tickets")
        ticket_labels = {
            t["ticket_id"]: f"#{t['ticket_id']} [{t['status']}] {t['title']}"
            for t in tickets
        }
        selected_id = st.radio(
            "Select a ticket",
            options=list(ticket_labels.keys()),
            format_func=lambda tid: ticket_labels[tid],
        )

    with col2:
        selected_ticket = next(t for t in tickets if t["ticket_id"] == selected_id)
        st.subheader(selected_ticket["title"])
        st.caption(f"Created by {selected_ticket['created_by']} on {selected_ticket['created_at']}")

        # --- Update status ---
        new_status = st.selectbox(
            "Status",
            STATUSES,
            index=STATUSES.index(selected_ticket["status"]) if selected_ticket["status"] in STATUSES else 0,
        )
        if new_status != selected_ticket["status"]:
            if st.button("Update status"):
                lakebase.run_write(
                    "UPDATE tickets SET status = %s WHERE ticket_id = %s",
                    (new_status, selected_id),
                )
                st.success("Status updated!")
                st.rerun()

        st.markdown("### Messages")
        messages = lakebase.run_query(
            "SELECT message_text, author, created_at FROM ticket_messages "
            "WHERE ticket_id = %s ORDER BY created_at ASC",
            (selected_id,),
        )
        for m in messages:
            st.markdown(f"**{m['author']}** _{m['created_at']}_")
            st.write(m["message_text"])
            st.divider()

        # --- Add message ---
        with st.form("new_message_form", clear_on_submit=True):
            author = st.text_input("Your name", key="msg_author")
            message_text = st.text_area("Message")
            msg_submitted = st.form_submit_button("Add message")
            if msg_submitted:
                if author and message_text:
                    lakebase.run_write(
                        "INSERT INTO ticket_messages (ticket_id, message_text, author) VALUES (%s, %s, %s)",
                        (selected_id, message_text, author),
                    )
                    st.success("Message added!")
                    st.rerun()
                else:
                    st.error("Name and message are required.")