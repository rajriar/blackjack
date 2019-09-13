"""Hitme_game - urls"""

from django.urls import path
from . import views
import django.contrib.auth.views as auth_views


urlpatterns = [
    path('lobby', views.lobby, name='lobby'),
    path('game/<game_url>', views.gameroom, name='gameroom'),
    path('rules', views.rules, name='rules'),
    path('', views.custom_login, name='mainpage'),
    path('logout', auth_views.logout_then_login, name='logout'),
    path('register', views.register, name='register'),
    path('create_game', views.create_game, name='create-game'),
    path('about', views.about, name="about"),
]
