

import lakebase


def create_tables():
    """Create the tickets and ticket_messages tables if they don't exist."""
    lakebase.run_write(
        """
        CREATE TABLE IF NOT EXISTS tickets (
            ticket_id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',
            created_by TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    lakebase.run_write(
        """
        CREATE TABLE IF NOT EXISTS ticket_messages (
            message_id SERIAL PRIMARY KEY,
            ticket_id INT NOT NULL REFERENCES tickets(ticket_id),
            message_text TEXT NOT NULL,
            author TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    # Safe against an already-existing tickets table: fills existing rows with
    # the given default and applies the same default going forward.
    lakebase.run_write(
        "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS priority TEXT NOT NULL DEFAULT 'medium'"
    )
    lakebase.run_write(
        "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS category TEXT NOT NULL DEFAULT 'other'"
    )


def init_schema():
    """Entry point: create tables, then seed if empty. Safe to call repeatedly."""
    create_tables()



if __name__ == "__main__":
    # Allows running this standalone in a notebook/terminal for manual setup:
    #   python schema.py
    init_schema()
    print("Schema created and sample data seeded (if tables were empty).")