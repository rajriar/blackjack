"""Hitme_game views"""

from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.views.decorators.http import require_POST
from .models import GameSession

MAX_PLAYERS_PER_GAME = getattr(settings, 'MAX_PLAYERS_PER_GAME', 3)

@login_required
def lobby(request):
    active_games = GameSession.objects.get_active_games()
    return render(request, 'hitme_game/lobby.html', {'active_games': active_games})


@login_required
def gameroom(request, game_url=None):
    if not game_url:
        return redirect(lobby)

    game = GameSession.objects.get_game(game_url)
    if not game or game.num_players >= MAX_PLAYERS_PER_GAME:
        return redirect(lobby)
    else:
        return render(request, 'hitme_game/gameroom.html', {'game': game})


def rules(request):
    return render(request, 'hitme_game/rules.html')


def custom_login(request):
    if request.user.is_authenticated:
        return redirect(lobby)
    else:
        return LoginView.as_view(
            template_name='hitme_game/index.html')(request)


def register(request):
    if request.method == "POST":
        username = request.POST.get('username', None)
        password = request.POST.get('password', None)
        password2 = request.POST.get('password2', None)
        # make sure all inputs are not null
        if username and password and password2:
            # make sure confirmation password is correct
            if password != password2:
                messages.add_message(request, messages.INFO,
                                     'The passwords are not consistent!')
                return redirect('/hitme#register')
            else:
                cur_users = User.objects.filter(username=username)
                if cur_users:  # if the username is already used, return
                    messages.add_message(
                        request, messages.INFO,
                        'The username is already taken!')
                    return redirect('/hitme#register')

                user = User.objects.create_user(
                    username=username, password=password)
                user.save()
                login(request, user)
                return redirect('/hitme/lobby')
    messages.add_message(request, messages.INFO,
                         'Please enter both user name and password')
    return redirect('/hitme#register')


@require_POST
@login_required
def create_game(request):
    game = GameSession.objects.create_game_session(request.user)
    return redirect('gameroom', game_url=game.url)

def about(request):
    return render(request, "hitme_game/about.html")
