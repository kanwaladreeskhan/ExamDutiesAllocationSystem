from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from accounts.mixins import CoordinatorRequiredMixin

from .forms import RoomForm
from .models import Room


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