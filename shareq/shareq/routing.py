import queues.routing
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.sessions import SessionMiddlewareStack

channel_routing = {}

application = ProtocolTypeRouter({
    'websocket': SessionMiddlewareStack(
        URLRouter(
            queues.routing.websocket_urlpatterns
        )
    ),
})