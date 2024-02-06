# urlpatterns = [
#     path("api", views.status, name="status"),
#     path("", views.index,),
#     # path("", TemplateView.as_view(template_name="frontend/index.html")),
# ]
# # if settings.DEBUG:
# #     import debug_toolbar
# #
# #     urlpatterns = [
# #         path('__debug__/', include(debug_toolbar.urls)),
# #     ] + urlpatterns
#
# from django.conf import settings
from django.urls import path, include

from hexfow import views

urlpatterns = [
    path('api/game/', include('game.urls')),
    path("", views.index, ),
]

