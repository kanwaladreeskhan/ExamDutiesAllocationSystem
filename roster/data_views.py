from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from accounts.decorators import coordinator_required
from accounts.mixins import CoordinatorRequiredMixin

from .forms import (
    AvailabilityForm,
    ExamSessionForm,
    ReplacementForm,
    RoomForm,
    SessionRoomFormSet,
    StaffForm,
)
from .models import (
    Assignment,
    Availability,
    ExamSession,
    Room,
    Roster,
    RosterChangeLog,
    StaffProfile,
)


# ---------- Rooms ----------

class RoomList(CoordinatorRequiredMixin, ListView):
    model = Room
    template_name = "coordinator/room_list.html"


class RoomCreate(CoordinatorRequiredMixin, CreateView):
    model = Room
    form_class = RoomForm
    template_name = "coordinator/room_form.html"
    success_url = reverse_lazy("manage:room_list")


class RoomUpdate(CoordinatorRequiredMixin, UpdateView):
    model = Room
    form_class = RoomForm
    template_name = "coordinator/room_form.html"
    success_url = reverse_lazy("manage:room_list")


class RoomDelete(CoordinatorRequiredMixin, DeleteView):
    model = Room
    template_name = "coordinator/room_confirm_delete.html"
    success_url = reverse_lazy("manage:room_list")


# ---------- Exam sessions ----------

class SessionList(CoordinatorRequiredMixin, ListView):
    model = ExamSession
    template_name = "coordinator/session_list.html"


class SessionDelete(CoordinatorRequiredMixin, DeleteView):
    model = ExamSession
    template_name = "coordinator/session_confirm_delete.html"
    success_url = reverse_lazy("manage:session_list")


def _save_session(request, session=None):
    if request.method == "POST":
        form = ExamSessionForm(request.POST, instance=session)
        formset = SessionRoomFormSet(request.POST, instance=session)
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                saved = form.save()
                formset.instance = saved
                formset.save()
            messages.success(request, "Exam session saved.")
            return redirect("manage:session_list")
    else:
        form = ExamSessionForm(instance=session)
        formset = SessionRoomFormSet(instance=session)
    return render(
        request,
        "coordinator/session_form.html",
        {"form": form, "formset": formset, "object": session},
    )


@coordinator_required
def session_add(request):
    return _save_session(request)


@coordinator_required
def session_edit(request, pk):
    return _save_session(request, get_object_or_404(ExamSession, pk=pk))


# ---------- Staff ----------

class StaffList(CoordinatorRequiredMixin, ListView):
    model = StaffProfile
    template_name = "coordinator/staff_list.html"
    queryset = StaffProfile.objects.select_related("user").order_by("user__first_name")


class StaffCreate(CoordinatorRequiredMixin, CreateView):
    model = StaffProfile
    form_class = StaffForm
    template_name = "coordinator/staff_form.html"
    success_url = reverse_lazy("manage:staff_list")


class StaffUpdate(CoordinatorRequiredMixin, UpdateView):
    model = StaffProfile
    form_class = StaffForm
    template_name = "coordinator/staff_form.html"
    success_url = reverse_lazy("manage:staff_list")


class StaffDelete(CoordinatorRequiredMixin, DeleteView):
    model = StaffProfile
    template_name = "coordinator/staff_confirm_delete.html"
    success_url = reverse_lazy("manage:staff_list")


# ---------- Availability ----------

class AvailabilityList(CoordinatorRequiredMixin, ListView):
    model = Availability
    template_name = "coordinator/availability_list.html"
    queryset = Availability.objects.select_related("staff__user").order_by(
        "date", "staff__user__first_name"
    )


class AvailabilityCreate(CoordinatorRequiredMixin, CreateView):
    model = Availability
    form_class = AvailabilityForm
    template_name = "coordinator/availability_form.html"
    success_url = reverse_lazy("manage:availability_list")


class AvailabilityUpdate(CoordinatorRequiredMixin, UpdateView):
    model = Availability
    form_class = AvailabilityForm
    template_name = "coordinator/availability_form.html"
    success_url = reverse_lazy("manage:availability_list")


class AvailabilityDelete(CoordinatorRequiredMixin, DeleteView):
    model = Availability
    template_name = "coordinator/availability_confirm_delete.html"
    success_url = reverse_lazy("manage:availability_list")


# ---------- Replacement (FR-09 & FR-12) ----------

class AssignmentList(CoordinatorRequiredMixin, ListView):
    model = Assignment
    template_name = "coordinator/assignment_list.html"
    queryset = Assignment.objects.select_related(
        "roster", "staff__user", "session_room__session", "session_room__room"
    ).order_by(
        "roster_id", "session_room__session__date", "session_room__session__start_time"
    )


@coordinator_required
def assignment_replace(request, pk):
    assignment = get_object_or_404(
        Assignment.objects.select_related(
            "roster", "staff__user", "session_room__session", "session_room__room"
        ),
        pk=pk,
    )
    if request.method == "POST":
        form = ReplacementForm(request.POST, assignment=assignment)
        if form.is_valid():
            old_staff_name = assignment.staff.user.get_full_name() or assignment.staff.user.username
            new_staff = form.cleaned_data["staff"]
            new_staff_name = new_staff.user.get_full_name() or new_staff.user.username

            assignment.staff = new_staff
            assignment.save()

            session = assignment.session_room.session
            room_name = assignment.session_room.room.name
            RosterChangeLog.objects.create(
                roster=assignment.roster,
                changed_by=request.user,
                action=(
                    f"Replaced {old_staff_name} with {new_staff_name} for "
                    f"{session.course_code} in {room_name} ({session.date})."
                ),
            )

            if assignment.roster.status == Roster.Status.PUBLISHED:
                channel_layer = get_channel_layer()
                if channel_layer:
                    async_to_sync(channel_layer.group_send)(
                        "notifications",
                        {
                            "type": "duty_update",
                            "message": (
                                f"Duty update ({session.date}, {room_name}): "
                                f"{new_staff_name} assigned in place of {old_staff_name}."
                            ),
                        },
                    )

            messages.success(request, "Replacement saved and logged.")
            return redirect("manage:assignment_list")
    else:
        form = ReplacementForm(assignment=assignment)
    return render(
        request,
        "coordinator/assignment_replace.html",
        {"form": form, "assignment": assignment},
    )