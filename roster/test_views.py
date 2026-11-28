from datetime import date, time
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from roster.models import (
    Assignment,
    ExamSession,
    Room,
    Roster,
    RosterChangeLog,
    SessionRoom,
    StaffProfile,
)

User = get_user_model()


@pytest.fixture
def setup_roster_data(db):
    coord_user = User.objects.create_user(
        username="coord1", password="Password123!", role="COORDINATOR"
    )
    staff_user = User.objects.create_user(
        username="staff1", first_name="Ali", last_name="Khan", password="Password123!", role="STAFF"
    )
    staff_profile = StaffProfile.objects.create(
        user=staff_user, designation="Lecturer", max_duties=4
    )
    room = Room.objects.create(name="A-101", capacity=40)
    session = ExamSession.objects.create(
        course_code="SEN-311",
        course_name="Software Construction",
        date=date(2026, 12, 15),
        start_time=time(9, 0),
        end_time=time(12, 0),
    )
    session_room = SessionRoom.objects.create(
        session=session, room=room, required_invigilators=1
    )
    return {
        "coord_user": coord_user,
        "staff_user": staff_user,
        "staff_profile": staff_profile,
        "room": room,
        "session": session,
        "session_room": session_room,
    }


@pytest.mark.django_db
def test_staff_cannot_access_coordinator_dashboard(client, setup_roster_data):
    client.force_login(setup_roster_data["staff_user"])
    response = client.get(reverse("coordinator"))
    assert response.status_code == 403


@pytest.mark.django_db
def test_generate_save_draft_and_publish_roster_flow(client, setup_roster_data):
    client.force_login(setup_roster_data["coord_user"])

    # Generate Draft Roster
    resp_gen = client.post(reverse("generate_roster"))
    assert resp_gen.status_code == 302
    roster = Roster.objects.first()
    assert roster is not None
    assert roster.status == Roster.Status.DRAFT
    assert Assignment.objects.filter(roster=roster).count() == 1

    # Save Draft
    resp_draft = client.post(reverse("save_draft"))
    assert resp_draft.status_code == 302

    # Publish Roster
    resp_pub = client.post(reverse("publish_roster"))
    assert resp_pub.status_code == 302
    roster.refresh_from_db()
    assert roster.status == Roster.Status.PUBLISHED
    assert RosterChangeLog.objects.filter(roster=roster).count() >= 2


@pytest.mark.django_db
def test_staff_dashboard_filters_csv_and_print(client, setup_roster_data):
    coord = setup_roster_data["coord_user"]
    staff = setup_roster_data["staff_user"]
    profile = setup_roster_data["staff_profile"]
    sr = setup_roster_data["session_room"]

    roster = Roster.objects.create(version=1, status=Roster.Status.PUBLISHED, created_by=coord)
    Assignment.objects.create(roster=roster, session_room=sr, staff=profile)

    client.force_login(staff)

    # Staff dashboard with matching filter
    resp = client.get(reverse("dashboard"), {"room": "A-101", "date": "2026-12-15"})
    assert resp.status_code == 200
    assert b"SEN-311" in resp.content
    assert b"Total Duties: 1" in resp.content

    # Non-matching room filter
    resp_empty = client.get(reverse("dashboard"), {"room": "Z-999"})
    assert resp_empty.status_code == 200
    assert b"No published exam duties found." in resp_empty.content

    # CSV export
    resp_csv = client.get(reverse("export_roster_csv"))
    assert resp_csv.status_code == 200
    assert "text/csv" in resp_csv["Content-Type"]
    assert b"SEN-311" in resp_csv.content

    # Print view
    resp_print = client.get(reverse("print_roster"))
    assert resp_print.status_code == 200
    assert b"SEN-311" in resp_print.content