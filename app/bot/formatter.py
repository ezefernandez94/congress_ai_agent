import re


def escape_markdown(text: str) -> str:
    """Escape special Markdown v2 characters."""
    special_chars = r"\_*[]()~`>#+-=|{}.!"
    return re.sub(f"([{re.escape(special_chars)}])", r"\\\1", text)


def format_task_list(tasks: list[dict]) -> str:
    if not tasks:
        return "No pending tasks. You're all caught up! ✅"

    priority_order = {"urgent": 0, "high": 1, "medium": 2, "low": 3}
    sorted_tasks = sorted(tasks, key=lambda t: priority_order.get(t.get("priority", "low"), 3))

    lines = []
    shown = 0
    for task in sorted_tasks[:7]:
        priority = task.get("priority", "medium")
        emoji = {"urgent": "⚠️", "high": "🔴", "medium": "🟡", "low": "🟢"}.get(priority, "•")
        due = f" _{task['due_date']}_" if task.get("due_date") else ""
        lines.append(f"{emoji} {task['title']}{due}")
        shown += 1

    if len(tasks) > 7:
        lines.append(f"_...and {len(tasks) - 7} more_")

    return "\n".join(lines)


def format_contact_saved(name: str, company: str | None, role: str | None, tasks: list[str]) -> str:
    details = []
    if company:
        details.append(company)
    if role:
        details.append(role)
    detail_str = ", ".join(details) if details else "no company info"

    lines = [f"{name} saved ✅ — {detail_str}."]
    if tasks:
        lines.append(f"{len(tasks)} task(s) created: {', '.join(tasks)}.")
    lines.append("Anything to add?")
    return "\n".join(lines)
