# hitme_game/routing.py
from django.conf.urls import url
from django.urls import path

from . import consumers

websocket_urlpatterns = [
    url(r'^ws/lobby/$', consumers.LobbyConsumer),
    path('ws/game/<game_url>/', consumers.GameRoomConsumer),
]
