from django import forms
from django.forms import inlineformset_factory

from .models import ExamSession, Room, SessionRoom


class RoomForm(forms.ModelForm):
    class Meta:
        model = Room
        fields = ["name", "capacity"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "capacity": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
        }

    def clean_capacity(self):
        capacity = self.cleaned_data["capacity"]
        if capacity < 1:
            raise forms.ValidationError("Capacity must be at least 1.")
        return capacity


class ExamSessionForm(forms.ModelForm):
    class Meta:
        model = ExamSession
        fields = ["course_code", "course_name", "date", "start_time", "end_time"]
        widgets = {
            "course_code": forms.TextInput(attrs={"class": "form-control"}),
            "course_name": forms.TextInput(attrs={"class": "form-control"}),
            "date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "start_time": forms.TimeInput(attrs={"class": "form-control", "type": "time"}),
            "end_time": forms.TimeInput(attrs={"class": "form-control", "type": "time"}),
        }

    def clean(self):
        cleaned = super().clean()
        start, end = cleaned.get("start_time"), cleaned.get("end_time")
        if start and end and end <= start:
            raise forms.ValidationError("End time must be after start time.")
        return cleaned


SessionRoomFormSet = inlineformset_factory(
    ExamSession,
    SessionRoom,
    fields=["room", "required_invigilators"],
    extra=1,
    can_delete=True,
    widgets={
        "room": forms.Select(attrs={"class": "form-select"}),
        "required_invigilators": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
    },
)