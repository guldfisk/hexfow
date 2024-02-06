from django.urls import path

from game import views


urlpatterns = [
    path("map/", views.GenerateMap.as_view()),
]
