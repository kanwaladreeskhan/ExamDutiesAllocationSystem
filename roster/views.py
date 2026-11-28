from datetime import date, time, datetime
from accounts.decorators import coordinator_required
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

# Imports for CSV Export (FR-11)
import csv
from django.http import HttpResponse


# Dummy data for testing the UI
SAMPLE_DUTIES = [
    {
        "date": date(2026, 12, 15),
        "start_time": time(9, 0),
        "end_time": time(12, 0),
        "room": "A-101",
        "course_code": "SEN-311",
        "role": "Invigilator",
        "status": "Confirmed",
    },
    {
        "date": date(2026, 12, 17),
        "start_time": time(14, 0),
        "end_time": time(17, 0),
        "room": "B-204",
        "course_code": "CSE-102",
        "role": "Invigilator",
        "status": "Confirmed",
    },
]


# Staff dashboard view (FR-10) - with Filters
@login_required
def staff_dashboard(request):
    duties = SAMPLE_DUTIES.copy()

    room = request.GET.get("room")
    date_str = request.GET.get("date")

    if room:
        duties = [d for d in duties if room.lower() in d["room"].lower()]

    if date_str:
        try:
            filter_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            duties = [d for d in duties if d["date"] == filter_date]
        except ValueError:
            pass

    return render(request, "staff/dashboard.html", {"duties": duties})


# Coordinator dashboard view
@coordinator_required
def coordinator_dashboard(request):
    return render(request, "coordinator/dashboard.html")


# Print roster view (FR-11)
@login_required
def print_roster(request):
    return render(
        request,
        "staff/print_roster.html",
        {
            "duties": SAMPLE_DUTIES,
            "staff": request.user,
            "exam_period": "December 2026",
            "designation": "Invigilator",
        },
    )


# Placeholder for allocation algorithm (Future implementation)
@coordinator_required
@require_POST
def generate_roster(request):
    messages.info(request, "Roster generation is a placeholder until allocation logic is added.")
    return redirect("coordinator")


# Placeholder for saving draft
@coordinator_required
@require_POST
def save_draft(request):
    messages.success(request, "Draft action received. Database saving is not implemented yet.")
    return redirect("coordinator")


# Publish roster and send real-time notification via WebSockets
@coordinator_required
@require_POST
def publish_roster(request):
    channel_layer = get_channel_layer()

    async_to_sync(channel_layer.group_send)(
        "notifications",
        {
            "type": "duty_update",
            "message": "New exam duty roster has been published! Please check your duties.",
        }
    )

    messages.success(request, "Roster published and staff have been notified in real-time.")
    return redirect("coordinator")


# FR-11: CSV Export functionality
@login_required
def export_roster_csv(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="my_exam_duties.csv"'

    writer = csv.writer(response)
    writer.writerow(["Date", "Start Time", "End Time", "Room", "Course Code", "Role", "Status"])

    for duty in SAMPLE_DUTIES:
        writer.writerow([
            duty["date"],
            duty["start_time"],
            duty["end_time"],
            duty["room"],
            duty["course_code"],
            duty["role"],
            duty["status"],
        ])

    return response


# Logout and redirect to login page
def logout_view(request):
    logout(request)
    return redirect("login")