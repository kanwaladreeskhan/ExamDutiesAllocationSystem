from django.contrib.auth import views as auth_views
from django.urls import path
from . import views

urlpatterns = [
    path("", views.staff_dashboard, name="dashboard"),
    path("coordinator/", views.coordinator_dashboard, name="coordinator"),
    path("print/", views.print_roster, name="print_roster"),
    path("generate-roster/", views.generate_roster, name="generate_roster"),
    path("save-draft/", views.save_draft, name="save_draft"),
    path("publish-roster/", views.publish_roster, name="publish_roster"),
    path("logout/", views.logout_view, name="logout"),

    # Password Change URLs
    path(
        "password-change/",
        auth_views.PasswordChangeView.as_view(
            template_name="registration/password_change_form.html"
        ),
        name="password_change",
    ),
    path(
        "password-change/done/",
        auth_views.PasswordChangeDoneView.as_view(
            template_name="registration/password_change_done.html"
        ),
        name="password_change_done",
    ),

    # CSV Export URL
    path("export-csv/", views.export_roster_csv, name="export_roster_csv"),
]