"""Convert Django models into the plain objects used by rules.py."""
from collections import defaultdict
from datetime import datetime, time, timedelta

from ..models import Assignment as DbAssignment
from .rules import Assignment as RuleAssignment
from .rules import Duty, StaffMember, TimeWindow, validate_replacement


def _dt(day, at):
    return datetime.combine(day, at)


def build_duty(session_room):
    session = session_room.session
    return Duty(
        id=session_room.pk,
        start=_dt(session.date, session.start_time),
        end=_dt(session.date, session.end_time),
        required_invigilators=session_room.required_invigilators,
        room=session_room.room.name,
    )


def _free_windows(profile, dates):
    """Whole day minus the staff member's unavailable entries, per date."""
    blocked = defaultdict(list)
    for entry in profile.availabilities.filter(date__in=dates, is_available=False):
        start = _dt(entry.date, entry.start_time or time.min)
        if entry.end_time:
            end = _dt(entry.date, entry.end_time)
        else:
            end = _dt(entry.date, time.min) + timedelta(days=1)
        blocked[entry.date].append((start, end))

    windows = []
    for day in dates:
        cursor = _dt(day, time.min)
        day_end = cursor + timedelta(days=1)
        for start, end in sorted(blocked.get(day, [])):
            if start > cursor:
                windows.append(TimeWindow(cursor, start))
            cursor = max(cursor, end)
        if cursor < day_end:
            windows.append(TimeWindow(cursor, day_end))
    return windows


def build_staff_member(profile, dates):
    return StaffMember(
        id=profile.pk,
        max_duties=profile.max_duties,
        availability=_free_windows(profile, dates),
    )


def check_replacement(db_assignment, new_staff):
    """Return a tuple of rule violations (empty tuple means allowed)."""
    roster_assignments = (
        DbAssignment.objects.filter(roster=db_assignment.roster)
        .select_related("session_room__session", "session_room__room")
        .order_by("pk")
    )
    slot_counter = defaultdict(int)
    rule_assignments = []
    target = None
    for item in roster_assignments:
        slot_counter[item.session_room_id] += 1
        converted = RuleAssignment(
            item.staff_id,
            build_duty(item.session_room),
            slot_counter[item.session_room_id],
        )
        rule_assignments.append(converted)
        if item.pk == db_assignment.pk:
            target = converted

    dates = {target.duty.start.date()}
    staff = build_staff_member(new_staff, dates)
    return validate_replacement(staff, target, rule_assignments)