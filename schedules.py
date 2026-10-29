"""Auditable timing rules for the class manager's background work."""
from dataclasses import dataclass


CALENDAR_SYNC_INTERVAL_SECONDS = 300
LIFECYCLE_INTERVAL_SECONDS = 3600
CONTRACT_REMINDER_DAYS = 3
INVITE_LINK_DAYS = 7
AFTER_CLASS_NOTE_REMINDER_HOUR = 17
ADMIN_DIGEST_WEEKDAY = 0
ADMIN_DIGEST_HOUR = 7
WEEKDAY_NAMES = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
FACEBOOK_TOKEN_WARNING_DAYS = (14, 2)


@dataclass(frozen=True)
class PeriodicJob:
    name: str
    handler: str
    interval_seconds: int
    log_prefix: str
    error_suffix: str


PERIODIC_JOBS = (
    PeriodicJob("class_lifecycle", "run_scheduler", LIFECYCLE_INTERVAL_SECONDS, "scheduler", "error"),
    PeriodicJob("signed_contract_filing", "sweep_contracts_to_drive", LIFECYCLE_INTERVAL_SECONDS, "contract", "sweep error"),
    PeriodicJob("contract_reminders", "sweep_contract_reminders", LIFECYCLE_INTERVAL_SECONDS, "contract", "reminder error"),
    PeriodicJob("paperwork_reminders", "sweep_paperwork_reminders", LIFECYCLE_INTERVAL_SECONDS, "paperwork", "reminder error"),
    PeriodicJob("scheduled_instructor_emails", "send_due_instructor_emails", LIFECYCLE_INTERVAL_SECONDS, "instructor-email", "error"),
    PeriodicJob("admin_digest", "send_admin_digest", LIFECYCLE_INTERVAL_SECONDS, "digest", "error"),
    PeriodicJob("materials_sheet", "sweep_materials_sheet", LIFECYCLE_INTERVAL_SECONDS, "materials", "sweep error"),
    PeriodicJob("master_sheet", "sweep_master_sheet", LIFECYCLE_INTERVAL_SECONDS, "sheet", "sweep error"),
    PeriodicJob("daily_backup", "daily_backup_if_due", LIFECYCLE_INTERVAL_SECONDS, "backup", "error"),
    PeriodicJob("session_pruning", "prune_sessions", LIFECYCLE_INTERVAL_SECONDS, "session", "prune error"),
    PeriodicJob("registration_money_sync", "sync_approved_class_money", LIFECYCLE_INTERVAL_SECONDS, "registrations", "hourly sync error"),
)

PERIODIC_JOB_DETAILS = {
    "class_lifecycle": {
        "label": "Class lifecycle",
        "cadence": "Hourly; class-specific rules use the date windows below",
    },
    "signed_contract_filing": {
        "label": "File signed contracts to Drive",
        "cadence": "Hourly check; files signed contracts that are not yet on Drive",
    },
    "contract_reminders": {
        "label": "Unsigned contract reminders",
        "cadence": f"Hourly check; one reminder after {CONTRACT_REMINDER_DAYS} days unsigned",
    },
    "paperwork_reminders": {
        "label": "Paperwork reminders",
        "cadence": f"Hourly check; remind after {CONTRACT_REMINDER_DAYS} days, once per request",
    },
    "scheduled_instructor_emails": {
        "label": "Scheduled instructor emails",
        "cadence": "Hourly check; sends emails at or past their configured send time",
    },
    "admin_digest": {
        "label": "Admin weekly digest",
        "cadence": f"Hourly check; sends {WEEKDAY_NAMES[ADMIN_DIGEST_WEEKDAY]} at or after {ADMIN_DIGEST_HOUR:02d}:00, once that day",
    },
    "materials_sheet": {
        "label": "Materials spreadsheet refresh",
        "cadence": "Hourly rebuild, and after a class submission; also manually refreshable",
    },
    "master_sheet": {
        "label": "Master classes spreadsheet refresh",
        "cadence": "Hourly rebuild",
    },
    "daily_backup": {
        "label": "Database backup",
        "cadence": "Hourly check; creates at most one backup per day",
    },
    "session_pruning": {
        "label": "Expired session cleanup",
        "cadence": "Hourly",
    },
    "registration_money_sync": {
        "label": "Eventbrite registration and money sync",
        "cadence": "Hourly for approved classes",
    },
}

MANUAL_ONLY_TASKS = ({
    "name": "treasurer_sheet",
    "label": "Treasurer spreadsheet refresh",
    "handler": "sweep_treasurer_sheet",
    "cadence": "Manual only from the admin action",
},)

CLASS_DAY_OFFSETS = {
    "low_enrollment_alert": (8, 14),
    "under_minimum_decision": (7, 7),
    "staff_reminder_nudge": (2, 2),
    "instructor_roster": (1, 1),
    "after_class_note_request": (-1, -1),
    "after_class_note_reminder": (-1, -1),
    "student_thank_you": (-4, -2),
    "marketing_request": (-6, -3),
}

CLASS_DAY_RULE_DETAILS = {
    "low_enrollment_alert": {"label": "Low-enrollment alert", "description": "To admins when enrollment is below minimum.", "relative_to": "first_session"},
    "under_minimum_decision": {"label": "Under-minimum decision", "description": "To admins; a person decides whether to keep or cancel the class.", "relative_to": "first_session"},
    "staff_reminder_nudge": {"label": "48-hour staff reminder nudge", "description": "Asks staff to review and send the student reminder manually.", "relative_to": "first_session"},
    "instructor_roster": {"label": "Instructor roster", "description": "Sends the current roster to the instructor.", "relative_to": "first_session"},
    "after_class_note_request": {"label": "After-class note request", "description": "Asks the instructor for a note the day after the last session.", "relative_to": "last_session"},
    "after_class_note_reminder": {"label": "After-class note reminder", "description": f"One reminder at or after {AFTER_CLASS_NOTE_REMINDER_HOUR:02d}:00 if the note is unwritten.", "relative_to": "last_session"},
    "student_thank_you": {"label": "Student thank-you", "description": "Sends after class, unless the class is exempt.", "relative_to": "last_session"},
    "marketing_request": {"label": "Marketing photo request", "description": "Asks the instructor for marketing photos after the thank-you.", "relative_to": "last_session"},
}

ADDITIONAL_RULES = (
    {"name": "Expired invite links", "cadence": f"Hourly check; renews expired links, each valid for {INVITE_LINK_DAYS} days"},
    {"name": "Facebook token warnings", "cadence": f"Warns admins {', '.join(map(str, FACEBOOK_TOKEN_WARNING_DAYS))} days before expiry"},
)

def class_event_due(rule, days_until_event):
    """Whether a class-relative rule is due; positive means before the event."""
    first, last = CLASS_DAY_OFFSETS[rule]
    return first <= days_until_event <= last


def class_event_window(rule):
    first, last = CLASS_DAY_OFFSETS[rule]
    relative = CLASS_DAY_RULE_DETAILS[rule]["relative_to"].replace("_", " ")
    if first == last:
        distance = abs(first)
        unit = "day" if distance == 1 else "days"
        direction = "before" if first > 0 else "after"
        return f"{distance} {unit} {direction} the {relative}"
    if first > 0:
        return f"{first}-{last} days before the {relative}"
    return f"{abs(last)}-{abs(first)} days after the {relative}"


def admin_schedule(deadline):
    periodic = []
    for job in PERIODIC_JOBS:
        periodic.append({
            "name": job.name,
            "handler": job.handler,
            "interval_seconds": job.interval_seconds,
            **PERIODIC_JOB_DETAILS[job.name],
        })
    class_events = []
    for name, offsets in CLASS_DAY_OFFSETS.items():
        class_events.append({
            "name": name,
            "label": CLASS_DAY_RULE_DETAILS[name]["label"],
            "description": CLASS_DAY_RULE_DETAILS[name]["description"],
            "days": offsets,
            "window": class_event_window(name),
        })
    return {
        "calendar_sync_interval_seconds": CALENDAR_SYNC_INTERVAL_SECONDS,
        "periodic": periodic,
        "manual_only": list(MANUAL_ONLY_TASKS),
        "class_events": class_events,
        "other_rules": list(ADDITIONAL_RULES),
        "deadline_campaign": {
            key: (deadline or {}).get(key, "")
            for key in ("what", "start", "date", "every")
        },
    }


def deadline_campaign_due(today, start, deadline, every_days):
    """Configured reminder cadence plus a reminder on the deadline itself."""
    return (today == deadline or
            (start <= today <= deadline and (today - start).days % every_days == 0))