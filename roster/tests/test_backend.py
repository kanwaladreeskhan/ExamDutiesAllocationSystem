from datetime import date, time

import pytest
from django.urls import reverse

from accounts.models import User
from roster.models import (
    Assignment, Availability, ExamSession, Room, Roster, SessionRoom, StaffProfile,
)
from roster.forms import AvailabilityForm, ExamSessionForm, RoomForm, StaffForm

pytestmark = pytest.mark.django_db


# ---------- helpers ----------

def make_user(username, role=User.Role.STAFF, password="Pass@12345"):
    return User.objects.create_user(username=username, password=password, role=role)


def make_staff(username, max_duties=5):
    user = make_user(username)
    return StaffProfile.objects.create(user=user, max_duties=max_duties)


@pytest.fixture
def coordinator(client):
    make_user("coord", role=User.Role.COORDINATOR)
    client.login(username="coord", password="Pass@12345")
    return client


@pytest.fixture
def staff_client(client):
    make_user("staffer")
    client.login(username="staffer", password="Pass@12345")
    return client


MANAGE_URLS = [
    "manage:room_list", "manage:session_list", "manage:staff_list",
    "manage:availability_list", "manage:assignment_list",
]


# ---------- permissions (FR-01) ----------

@pytest.mark.parametrize("name", MANAGE_URLS)
def test_staff_gets_403_on_manage_pages(staff_client, name):
    assert staff_client.get(reverse(name)).status_code == 403


@pytest.mark.parametrize("name", MANAGE_URLS)
def test_coordinator_can_open_manage_pages(coordinator, name):
    assert coordinator.get(reverse(name)).status_code == 200


@pytest.mark.parametrize("name", MANAGE_URLS)
def test_anonymous_is_redirected_to_login(client, name):
    response = client.get(reverse(name))
    assert response.status_code == 302
    assert "login" in response.url


def test_staff_cannot_open_coordinator_dashboard(staff_client):
    assert staff_client.get(reverse("coordinator")).status_code == 403


# ---------- password hashing ----------

def test_password_is_stored_hashed():
    user = make_user("hashme", password="Secret@123")
    assert user.password != "Secret@123"
    assert user.password.startswith("pbkdf2_")
    assert user.check_password("Secret@123")


def test_staff_form_hashes_password():
    form = StaffForm(data={
        "first_name": "New", "last_name": "Person", "username": "newperson",
        "password": "Plain@12345", "designation": "Lecturer", "max_duties": 3,
    })
    assert form.is_valid(), form.errors
    profile = form.save()
    assert profile.user.password != "Plain@12345"
    assert profile.user.check_password("Plain@12345")
    assert profile.user.role == User.Role.STAFF


# ---------- invalid inputs ----------

def test_room_capacity_zero_rejected():
    assert not RoomForm(data={"name": "X-1", "capacity": 0}).is_valid()


def test_duplicate_room_name_rejected():
    Room.objects.create(name="A-1", capacity=10)
    assert not RoomForm(data={"name": "A-1", "capacity": 10}).is_valid()


def test_session_end_before_start_rejected():
    form = ExamSessionForm(data={
        "course_code": "X", "course_name": "X", "date": "2026-12-15",
        "start_time": "12:00", "end_time": "09:00",
    })
    assert not form.is_valid()


def test_negative_duty_limit_rejected():
    form = StaffForm(data={
        "first_name": "A", "last_name": "B", "username": "ab",
        "password": "Pass@12345", "designation": "L", "max_duties": -1,
    })
    assert not form.is_valid()


def test_duplicate_username_rejected():
    make_user("taken")
    form = StaffForm(data={
        "first_name": "A", "last_name": "B", "username": "taken",
        "password": "Pass@12345", "designation": "L", "max_duties": 3,
    })
    assert not form.is_valid()
    assert "username" in form.errors


def test_availability_needs_both_times_or_none():
    staff = make_staff("avail")
    form = AvailabilityForm(data={
        "staff": staff.pk, "date": "2026-12-15", "start_time": "09:00",
        "end_time": "", "is_available": False,
    })
    assert not form.is_valid()


# ---------- replacement (FR-09, BR-01/02/03/05) ----------

@pytest.fixture
def setup_roster():
    room = Room.objects.create(name="A-101", capacity=40)
    s1 = ExamSession.objects.create(
        course_code="S1", course_name="One", date=date(2026, 12, 15),
        start_time=time(9, 0), end_time=time(12, 0))
    s2 = ExamSession.objects.create(
        course_code="S2", course_name="Two", date=date(2026, 12, 15),
        start_time=time(10, 0), end_time=time(13, 0))
    sr1 = SessionRoom.objects.create(session=s1, room=room, required_invigilators=1)
    sr2 = SessionRoom.objects.create(session=s2, room=room, required_invigilators=1)
    roster = Roster.objects.create(version=1)
    hina, zara = make_staff("hina"), make_staff("zara")
    a1 = Assignment.objects.create(roster=roster, session_room=sr1, staff=hina)
    Assignment.objects.create(roster=roster, session_room=sr2, staff=zara)
    return {"a1": a1, "hina": hina, "zara": zara}


def post_replace(client, assignment, staff):
    return client.post(
        reverse("manage:assignment_replace", args=[assignment.pk]), {"staff": staff.pk}
    )


def test_replacement_valid_is_saved(coordinator, setup_roster):
    bilal = make_staff("bilal")
    response = post_replace(coordinator, setup_roster["a1"], bilal)
    assert response.status_code == 302
    setup_roster["a1"].refresh_from_db()
    assert setup_roster["a1"].staff == bilal


def test_replacement_unavailable_rejected(coordinator, setup_roster):
    ali = make_staff("ali")
    Availability.objects.create(staff=ali, date=date(2026, 12, 15), is_available=False)
    response = post_replace(coordinator, setup_roster["a1"], ali)
    assert response.status_code == 200
    setup_roster["a1"].refresh_from_db()
    assert setup_roster["a1"].staff == setup_roster["hina"]


def test_replacement_overlap_rejected(coordinator, setup_roster):
    # zara already works 10:00-13:00, the target duty is 09:00-12:00
    response = post_replace(coordinator, setup_roster["a1"], setup_roster["zara"])
    assert response.status_code == 200
    setup_roster["a1"].refresh_from_db()
    assert setup_roster["a1"].staff == setup_roster["hina"]


def test_replacement_over_duty_limit_rejected(coordinator, setup_roster):
    limited = make_staff("limited", max_duties=0)
    response = post_replace(coordinator, setup_roster["a1"], limited)
    assert response.status_code == 200
    setup_roster["a1"].refresh_from_db()
    assert setup_roster["a1"].staff == setup_roster["hina"]


def test_staff_cannot_replace(staff_client, setup_roster):
    bilal = make_staff("bilal2")
    response = post_replace(staff_client, setup_roster["a1"], bilal)
    assert response.status_code == 403