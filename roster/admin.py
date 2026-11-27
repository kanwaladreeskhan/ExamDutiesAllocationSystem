from django.contrib import admin
from .models import StaffProfile, Availability, Room, ExamSession, SessionRoom, Roster, Assignment

for model in (StaffProfile, Availability, Room, ExamSession, SessionRoom, Roster, Assignment):
    admin.site.register(model)