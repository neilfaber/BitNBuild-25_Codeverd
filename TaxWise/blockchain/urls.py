from django.urls import path
from . import views

urlpatterns = [
    path("add/", views.add_record_form, name="add_record_form"),
    path("get/", views.get_record_form, name="get_record_form"),
]
