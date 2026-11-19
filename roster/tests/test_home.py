"""Smoke test: the home page loads."""
from django.test import Client


def test_home_page_loads():
    response = Client().get("/")
    assert response.status_code == 200
