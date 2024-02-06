from django.urls import path

from frontend import views


urlpatterns = [
    path('', TemplateView.as_view(template_name='index.html')),
]