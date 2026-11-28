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
        path("staff/", v.StaffList.as_view(), name="staff_list"),
    path("staff/add/", v.StaffCreate.as_view(), name="staff_add"),
    path("staff/<int:pk>/edit/", v.StaffUpdate.as_view(), name="staff_edit"),
    path("staff/<int:pk>/delete/", v.StaffDelete.as_view(), name="staff_delete"),
        path("availability/", v.AvailabilityList.as_view(), name="availability_list"),
    path("availability/add/", v.AvailabilityCreate.as_view(), name="availability_add"),
    path("availability/<int:pk>/edit/", v.AvailabilityUpdate.as_view(), name="availability_edit"),
    path("availability/<int:pk>/delete/", v.AvailabilityDelete.as_view(), name="availability_delete"),
           path("assignments/", v.AssignmentList.as_view(), name="assignment_list"),
    path("assignments/<int:pk>/replace/", v.assignment_replace, name="assignment_replace"),
]
