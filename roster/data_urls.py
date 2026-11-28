from django.urls import path
from . import data_views as v

app_name = "manage"

urlpatterns = [
    path("rooms/", v.RoomList.as_view(), name="room_list"),
    path("rooms/add/", v.RoomCreate.as_view(), name="room_add"),
    path("rooms/<int:pk>/edit/", v.RoomUpdate.as_view(), name="room_edit"),
    path("rooms/<int:pk>/delete/", v.RoomDelete.as_view(), name="room_delete"),
 path("sessions/", v.SessionList.as_view(), name="session_list"),
    path("sessions/add/", v.session_add, name="session_add"),
    path("sessions/<int:pk>/edit/", v.session_edit, name="session_edit"),
    path("sessions/<int:pk>/delete/", v.SessionDelete.as_view(), name="session_delete"),
]