from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from accounts.decorators import coordinator_required
from accounts.mixins import CoordinatorRequiredMixin

from .forms import ExamSessionForm, RoomForm, SessionRoomFormSet
from .models import ExamSession, Room


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