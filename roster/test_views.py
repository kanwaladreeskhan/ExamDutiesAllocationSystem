import pytest
from django.urls import reverse

from accounts.models import User


def login_as(client, username, role):
    User.objects.create_user(username=username, password="Pass@12345", role=role)
    client.login(username=username, password="Pass@12345")


@pytest.mark.django_db
def test_staff_dashboard_loads(client):
    login_as(client, "staffer", User.Role.STAFF)
    response = client.get(reverse("dashboard"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_staff_dashboard_room_filter(client):
    login_as(client, "staffer", User.Role.STAFF)
    response = client.get(reverse("dashboard"), {"room": "A-101"})
    assert response.status_code == 200


@pytest.mark.django_db
def test_coordinator_dashboard_loads(client):
    login_as(client, "coord", User.Role.COORDINATOR)
    response = client.get(reverse("coordinator"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_publish_roster_post_redirects(client):
    login_as(client, "coord", User.Role.COORDINATOR)
    response = client.post(reverse("publish_roster"))
    assert response.status_code == 302
    assert response.url == reverse("coordinator")


@pytest.mark.django_db
def test_export_csv_returns_csv_file(client):
    login_as(client, "staffer", User.Role.STAFF)
    response = client.get(reverse("export_csv"))
    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/csv")


@pytest.mark.django_db
def test_print_roster_loads(client):
    login_as(client, "staffer", User.Role.STAFF)
    response = client.get(reverse("print_roster"))
    assert response.status_code == 200