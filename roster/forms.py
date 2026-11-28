from django import forms
from django.forms import inlineformset_factory

from accounts.models import User

from .models import Availability, ExamSession, Room, SessionRoom, StaffProfile
from .services.adapters import check_replacement


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


class StaffForm(forms.ModelForm):
    """Creates/edits a staff User together with its StaffProfile."""
    first_name = forms.CharField(widget=forms.TextInput(attrs={"class": "form-control"}))
    last_name = forms.CharField(widget=forms.TextInput(attrs={"class": "form-control"}))
    username = forms.CharField(widget=forms.TextInput(attrs={"class": "form-control"}))
    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
        help_text="Leave blank to keep the current password.",
    )

    class Meta:
        model = StaffProfile
        fields = ["designation", "max_duties"]
        widgets = {
            "designation": forms.TextInput(attrs={"class": "form-control"}),
            "max_duties": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            u = self.instance.user
            self.fields["first_name"].initial = u.first_name
            self.fields["last_name"].initial = u.last_name
            self.fields["username"].initial = u.username

    def clean_username(self):
        username = self.cleaned_data["username"]
        qs = User.objects.filter(username=username)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.user_id)
        if qs.exists():
            raise forms.ValidationError("This username is already taken.")
        return username

    def clean(self):
        cleaned = super().clean()
        if not self.instance.pk and not cleaned.get("password"):
            self.add_error("password", "Password is required for a new staff member.")
        return cleaned

    def save(self, commit=True):
        profile = super().save(commit=False)
        data = self.cleaned_data
        user = profile.user if self.instance.pk else User(role=User.Role.STAFF)
        user.username = data["username"]
        user.first_name = data["first_name"]
        user.last_name = data["last_name"]
        if data.get("password"):
            user.set_password(data["password"])  # hashed
        user.save()
        profile.user = user
        if commit:
            profile.save()
        return profile


class AvailabilityForm(forms.ModelForm):
    class Meta:
        model = Availability
        fields = ["staff", "date", "start_time", "end_time", "is_available"]
        widgets = {
            "staff": forms.Select(attrs={"class": "form-select"}),
            "date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "start_time": forms.TimeInput(attrs={"class": "form-control", "type": "time"}),
            "end_time": forms.TimeInput(attrs={"class": "form-control", "type": "time"}),
            "is_available": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean(self):
        cleaned = super().clean()
        start, end = cleaned.get("start_time"), cleaned.get("end_time")
        if bool(start) != bool(end):
            raise forms.ValidationError(
                "Give both start and end time, or leave both empty for the whole day."
            )
        if start and end and end <= start:
            raise forms.ValidationError("End time must be after start time.")
        return cleaned


class ReplacementForm(forms.Form):
    staff = forms.ModelChoiceField(
        queryset=StaffProfile.objects.all(),
        label="Replacement staff member",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    def __init__(self, *args, assignment, **kwargs):
        super().__init__(*args, **kwargs)
        self.assignment = assignment
        self.fields["staff"].queryset = (
            StaffProfile.objects.select_related("user")
            .exclude(pk=assignment.staff_id)
            .order_by("user__first_name")
        )

    def clean_staff(self):
        staff = self.cleaned_data["staff"]
        issues = check_replacement(self.assignment, staff)
        if issues:
            raise forms.ValidationError(list(issues))
        return staff