import csv
import json
from collections import defaultdict
from datetime import datetime

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.decorators import coordinator_required
from .models import Assignment, Roster, RosterChangeLog, SessionRoom, StaffProfile
from .services.adapters import build_duty, build_staff_member
from .services.allocation import allocate_duties


def _duty_hours(session):
    start_dt = datetime.combine(session.date, session.start_time)
    end_dt = datetime.combine(session.date, session.end_time)
    return round((end_dt - start_dt).total_seconds() / 3600, 2)


def _get_published_duties(user, room=None, date_str=None):
    """Fetch published assignments for a staff user (or all if coordinator)."""
    latest_published = (
        Roster.objects.filter(status=Roster.Status.PUBLISHED)
        .order_by("-version", "-published_at")
        .first()
    )
    if not latest_published:
        return []

    qs = (
        Assignment.objects.filter(roster=latest_published)
        .select_related("staff__user", "session_room__session", "session_room__room")
        .order_by("session_room__session__date", "session_room__session__start_time")
    )

    if getattr(user, "role", None) != "COORDINATOR":
        qs = qs.filter(staff__user=user)

    if room:
        qs = qs.filter(session_room__room__name__icontains=room.strip())

    if date_str:
        try:
            filter_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            qs = qs.filter(session_room__session__date=filter_date)
        except ValueError:
            pass

    duties = []
    for item in qs:
        session = item.session_room.session
        duties.append({
            "date": session.date,
            "start_time": session.start_time,
            "end_time": session.end_time,
            "room": item.session_room.room.name,
            "course_code": session.course_code,
            "course_name": session.course_name,
            "staff_name": item.staff.user.get_full_name() or item.staff.user.username,
            "role": item.staff.designation or "Invigilator",
            "hours": _duty_hours(session),
            "status": f"Published (v{latest_published.version})",
        })
    return duties


# Staff dashboard view (FR-10) - with Filters, Duty Count & Total Hours
@login_required
def staff_dashboard(request):
    room = request.GET.get("room", "")
    date_str = request.GET.get("date", "")
    duties = _get_published_duties(request.user, room=room, date_str=date_str)
    total_hours = round(sum(d["hours"] for d in duties), 2)

    return render(
        request,
        "staff/dashboard.html",
        {
            "duties": duties,
            "duty_count": len(duties),
            "total_hours": total_hours,
        },
    )


# Coordinator dashboard view with Workload Charts & Change Log
@coordinator_required
def coordinator_dashboard(request):
    latest_roster = Roster.objects.order_by("-version", "-created_at").first()
    staff_profiles = StaffProfile.objects.select_related("user").order_by("user__first_name", "user__username")

    duty_counts = defaultdict(int)
    duty_hours = defaultdict(float)

    if latest_roster:
        assignments = Assignment.objects.filter(roster=latest_roster).select_related(
            "staff", "session_room__session"
        )
        for a in assignments:
            duty_counts[a.staff_id] += 1
            duty_hours[a.staff_id] += _duty_hours(a.session_room.session)

    chart_labels = []
    chart_counts = []
    chart_hours = []
    for sp in staff_profiles:
        chart_labels.append(sp.user.get_full_name() or sp.user.username)
        chart_counts.append(duty_counts[sp.id])
        chart_hours.append(round(duty_hours[sp.id], 2))

    total_required = sum(sr.required_invigilators for sr in SessionRoom.objects.all())
    total_assigned = sum(chart_counts)
    unfilled_count = max(total_required - total_assigned, 0)
    unfilled_details = request.session.pop("unfilled_details", [])

    change_logs = RosterChangeLog.objects.select_related("roster", "changed_by")[:10]

    return render(
        request,
        "coordinator/dashboard.html",
        {
            "latest_roster": latest_roster,
            "total_assigned": total_assigned,
            "total_required": total_required,
            "unfilled_count": unfilled_count,
            "unfilled_details": unfilled_details,
            "change_logs": change_logs,
            "chart_labels_json": json.dumps(chart_labels),
            "chart_counts_json": json.dumps(chart_counts),
            "chart_hours_json": json.dumps(chart_hours),
        },
    )


# Print roster view (FR-11)
@login_required
def print_roster(request):
    duties = _get_published_duties(request.user)
    profile = getattr(request.user, "staff_profile", None)
    return render(
        request,
        "staff/print_roster.html",
        {
            "duties": duties,
            "staff": request.user,
            "exam_period": "Fall 2026",
            "designation": profile.designation if profile and profile.designation else "Invigilator",
        },
    )


# Run automatic allocation algorithm and create a new Draft roster (FR-06, FR-07, FR-08)
@coordinator_required
@require_POST
def generate_roster(request):
    session_rooms = list(
        SessionRoom.objects.select_related("session", "room").order_by(
            "session__date", "session__start_time"
        )
    )
    staff_profiles = list(StaffProfile.objects.select_related("user").prefetch_related("availabilities"))

    if not session_rooms or not staff_profiles:
        messages.warning(request, "Please add staff members and exam session rooms before generating a roster.")
        return redirect("coordinator")

    dates = {sr.session.date for sr in session_rooms}
    duties = [build_duty(sr) for sr in session_rooms]
    staff_members = [build_staff_member(sp, dates) for sp in staff_profiles]

    result = allocate_duties(staff_members, duties)

    latest = Roster.objects.order_by("-version").first()
    next_version = (latest.version + 1) if latest else 1

    with transaction.atomic():
        roster = Roster.objects.create(
            version=next_version,
            status=Roster.Status.DRAFT,
            created_by=request.user,
        )
        Assignment.objects.bulk_create([
            Assignment(
                roster=roster,
                session_room_id=a.duty.id,
                staff_id=a.staff_id,
            )
            for a in result.assignments
        ])
        RosterChangeLog.objects.create(
            roster=roster,
            changed_by=request.user,
            action=f"Generated Draft Roster v{roster.version} ({len(result.assignments)} assigned, {len(result.unfilled)} unfilled).",
        )

    if result.unfilled:
        request.session["unfilled_details"] = [
            f"{u.duty.room} ({u.duty.start:%Y-%m-%d %H:%M}) Slot #{u.slot_number}: {u.reasons[0]}"
            for u in result.unfilled
        ]
        messages.warning(
            request,
            f"Draft Roster v{roster.version} generated with {len(result.assignments)} assignments and {len(result.unfilled)} unfilled slots.",
        )
    else:
        messages.success(
            request,
            f"Draft Roster v{roster.version} generated successfully with all {len(result.assignments)} slots filled!",
        )
    return redirect("coordinator")


# Save current roster as Draft (FR-11)
@coordinator_required
@require_POST
def save_draft(request):
    latest = Roster.objects.order_by("-version").first()
    if not latest:
        messages.warning(request, "No roster exists yet. Click Generate Roster first.")
        return redirect("coordinator")

    if latest.status == Roster.Status.PUBLISHED:
        with transaction.atomic():
            new_draft = Roster.objects.create(
                version=latest.version + 1,
                status=Roster.Status.DRAFT,
                created_by=request.user,
            )
            Assignment.objects.bulk_create([
                Assignment(
                    roster=new_draft,
                    session_room=a.session_room,
                    staff=a.staff,
                )
                for a in latest.assignments.all()
            ])
            RosterChangeLog.objects.create(
                roster=new_draft,
                changed_by=request.user,
                action=f"Cloned Published v{latest.version} into editable Draft v{new_draft.version}.",
            )
        messages.success(request, f"Created editable Draft Roster v{new_draft.version}.")
    else:
        RosterChangeLog.objects.create(
            roster=latest,
            changed_by=request.user,
            action=f"Saved Draft Roster v{latest.version}.",
        )
        messages.success(request, f"Draft Roster v{latest.version} saved.")
    return redirect("coordinator")


# Publish roster snapshot and send real-time notification via WebSockets (FR-11, FR-12)
@coordinator_required
@require_POST
def publish_roster(request):
    latest = Roster.objects.order_by("-version").first()
    if not latest:
        messages.warning(request, "No roster available to publish. Generate a roster first.")
        return redirect("coordinator")

    with transaction.atomic():
        latest.status = Roster.Status.PUBLISHED
        latest.published_at = timezone.now()
        latest.save(update_fields=["status", "published_at"])
        RosterChangeLog.objects.create(
            roster=latest,
            changed_by=request.user,
            action=f"Published Roster v{latest.version}.",
        )

    channel_layer = get_channel_layer()
    if channel_layer:
        async_to_sync(channel_layer.group_send)(
            "notifications",
            {
                "type": "duty_update",
                "message": f"Exam duty roster v{latest.version} has been published! Please check your duties.",
            },
        )

    messages.success(request, f"Roster v{latest.version} published and staff notified in real-time.")
    return redirect("coordinator")


# FR-11: CSV Export functionality
@login_required
def export_roster_csv(request):
    duties = _get_published_duties(request.user)
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="my_exam_duties.csv"'

    writer = csv.writer(response)
    writer.writerow(["Date", "Start Time", "End Time", "Room", "Course Code", "Role", "Hours", "Status"])

    for duty in duties:
        writer.writerow([
            duty["date"],
            duty["start_time"],
            duty["end_time"],
            duty["room"],
            duty["course_code"],
            duty["role"],
            duty["hours"],
            duty["status"],
        ])

    return response


# Logout and redirect to login page
def logout_view(request):
    logout(request)
    return redirect("login")