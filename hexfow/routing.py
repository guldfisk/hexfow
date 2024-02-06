from django.urls import re_path

from hexfow import consumers

websocket_urlpatterns = [
    re_path(r"ws/chat/$", consumers.GameConsumer.as_asgi()),
]
