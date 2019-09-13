"""HitMe Game Models"""

from django.conf import settings
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
import secrets
import string

AUTH_USER_MODEL = getattr(settings, 'AUTH_USER_MODEL', 'auth.User')
SESSION_URL_LENGTH = getattr(settings, 'SESSION_URL_LENGTH', 10)
MAX_PLAYERS_PER_GAME = getattr(settings, 'MAX_PLAYERS_PER_GAME', 3)


class GameSessionManager(models.Manager):

    def create_game_session(self, user):
        return self.create(url=self.generate_unique_url(), creator=user)

    def generate_unique_url(self):
        url = ''.join(secrets.choice(string.ascii_letters + string.digits)
                      for i in range(SESSION_URL_LENGTH))
        try:
            obj = self.get(url=url)
            return self.generate_unique_url()
        except GameSession.DoesNotExist:
            return url

    def get_active_games(self):
        return self.filter(num_players__gt=0,
                           num_players__lt=MAX_PLAYERS_PER_GAME)

    def get_game(self, url):
        try:
            return self.get(url=url)
        except GameSession.DoesNotExist:
            return None

    def update_num_players(self, url, num_players):
        self.filter(url=url).update(num_players=num_players)

    def delete_game_session(self, url):
        self.filter(url=url).delete()


@python_2_unicode_compatible
class GameSession(models.Model):
    """
    Model to store Game Session
    """
    url = models.CharField(max_length=25, unique=True)
    creator = models.ForeignKey(
        AUTH_USER_MODEL, related_name='creator', on_delete=models.CASCADE)
    num_players = models.IntegerField(default=0)

    objects = GameSessionManager()
