import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_staff_dashboard_loads(client):
    response = client.get(reverse("dashboard"))
    assert response.status_code == 200
    assert b"My Exam Duties" in response.content


@pytest.mark.django_db
def test_staff_dashboard_room_filter(client):
    response = client.get(reverse("dashboard"), {"room": "A-101"})
    assert response.status_code == 200
    assert b"A-101" in response.content


@pytest.mark.django_db
def test_coordinator_dashboard_loads(client):
    response = client.get(reverse("coordinator"))
    assert response.status_code == 200
    assert b"Coordinator Dashboard" in response.content


@pytest.mark.django_db
def test_publish_roster_post_redirects(client):
    response = client.post(reverse("publish_roster"))
    assert response.status_code == 302
    assert response.url == reverse("coordinator")


@pytest.mark.django_db
def test_export_csv_returns_csv_file(client):
    response = client.get(reverse("export_csv"))
    assert response.status_code == 200
    assert response["Content-Type"] == "text/csv"


@pytest.mark.django_db
def test_print_roster_loads(client):
    response = client.get(reverse("print_roster"))
    assert response.status_code == 200
    assert b"Examination Invigilation Duty Sheet" in response.content