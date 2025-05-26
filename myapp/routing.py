from django.urls import re_path
from . import consumer # Changed from 'consumers' to 'consumer'

websocket_urlpatterns = [
    re_path(r'ws/chat/(?P<room_id>[^/]+)/$', consumer.ChatConsumer.as_asgi()), # Changed from 'consumers' to 'consumer'
]
