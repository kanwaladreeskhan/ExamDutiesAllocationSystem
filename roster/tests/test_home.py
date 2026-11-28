import pytest
from django.test import Client


@pytest.mark.django_db
def test_home_redirects_anonymous_to_login():
    response = Client().get("/")
    assert response.status_code == 302
    assert "/accounts/login/" in response.url