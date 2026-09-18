from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # WebSocket route for the omnichannel inbox (per tenant)
    re_path(r'ws/inbox/(?P<tenant_slug>[\w-]+)/$', consumers.InboxConsumer.as_asgi()),
]
