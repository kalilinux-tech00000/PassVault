"""
logger.py — View and export login audit logs
"""

from database import get_connection


def get_all_logs(limit: int = 50) -> list:
    """Return the most recent login log entries."""
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT id, username, status, ip_address, timestamp, reason
        FROM login_logs
        ORDER BY timestamp DESC
        LIMIT ?
        """,
        (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_failed_logs() -> list:
    """Return only failed login attempts."""
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT id, username, status, ip_address, timestamp, reason
        FROM login_logs
        WHERE status = 'FAILED'
        ORDER BY timestamp DESC
        """
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def print_logs(logs: list):
    """Pretty-print a list of log entries to console."""
    if not logs:
        print("[LOG] No entries found.")
        return
    header = f"{'ID':<5} {'USERNAME':<15} {'STATUS':<10} {'IP':<15} {'TIMESTAMP':<20} {'REASON'}"
    print(header)
    print("-" * len(header))
    for log in logs:
        reason = log.get("reason") or ""
        print(
            f"{log['id']:<5} {log['username']:<15} {log['status']:<10} "
            f"{log['ip_address']:<15} {log['timestamp']:<20} {reason}"
        )


def export_logs_csv(filepath: str = "login_logs.csv"):
    """Export all login logs to a CSV file."""
    import csv
    logs = get_all_logs(limit=10_000)
    if not logs:
        print("[LOG] No logs to export.")
        return
    with open(filepath, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=logs[0].keys())
        writer.writeheader()
        writer.writerows(logs)
    print(f"[LOG] Exported {len(logs)} entries to '{filepath}'.")
