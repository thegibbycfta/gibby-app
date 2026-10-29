"""Auditable timing rules for the class manager's background work."""
from dataclasses import dataclass


CALENDAR_SYNC_INTERVAL_SECONDS = 300
LIFECYCLE_INTERVAL_SECONDS = 3600


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

MANUAL_ONLY_TASKS = ("treasurer_sheet",)

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

CONTRACT_REMINDER_DAYS = 3
INVITE_LINK_DAYS = 7
AFTER_CLASS_NOTE_REMINDER_HOUR = 17
ADMIN_DIGEST_WEEKDAY = 0
ADMIN_DIGEST_HOUR = 7
FACEBOOK_TOKEN_WARNING_DAYS = (14, 2)


def class_event_due(rule, days_until_event):
    """Whether a class-relative rule is due; positive means before the event."""
    first, last = CLASS_DAY_OFFSETS[rule]
    return first <= days_until_event <= last


def deadline_campaign_due(today, start, deadline, every_days):
    """Configured reminder cadence plus a reminder on the deadline itself."""
    return (today == deadline or
            (start <= today <= deadline and (today - start).days % every_days == 0))