# hitme_game/consumers.py
from asgiref.sync import async_to_sync
from channels.generic.websocket import JsonWebsocketConsumer
from channels.layers import get_channel_layer
from django.conf import settings
import json
from .models import GameSession
from . import live_games
from time import sleep

MAX_PLAYERS_PER_GAME = getattr(settings, 'MAX_PLAYERS_PER_GAME', 3)


class LobbyConsumer(JsonWebsocketConsumer):
    LOBBY_CHANNEL_GROUP = "lobby_channels"

    @classmethod
    def update_game_broadcast(cls, data):
        channel_layer = get_channel_layer()
        data['type'] = 'update_game'
        # Send message to room group
        async_to_sync(channel_layer.group_send)(
            cls.LOBBY_CHANNEL_GROUP, data
        )

    @classmethod
    def remove_game_broadcast(cls, data):
        channel_layer = get_channel_layer()
        data['type'] = 'remove_game'
        # Send message to room group
        async_to_sync(channel_layer.group_send)(
            cls.LOBBY_CHANNEL_GROUP, data
        )

    @classmethod
    def chat_broadcast(cls, data):
        channel_layer = get_channel_layer()
        data['type'] = 'chat_message'
        # Send message to room group
        async_to_sync(channel_layer.group_send)(
            cls.LOBBY_CHANNEL_GROUP, data
        )

    def connect(self):
        if self.scope["user"].is_anonymous:
            self.close()

        # Join Lobby Group
        async_to_sync(self.channel_layer.group_add)(
            LobbyConsumer.LOBBY_CHANNEL_GROUP,
            self.channel_name
        )
        self.accept()

    def disconnect(self, close_code):
        # Leave room group
        async_to_sync(self.channel_layer.group_discard)(
            LobbyConsumer.LOBBY_CHANNEL_GROUP,
            self.channel_name
        )

    def receive_json(self, content):
        message_type = content.get('type', '')
        if message_type == "CHAT":
            LobbyConsumer.chat_broadcast({
                'chat_message': content['chat_message'],
                'player': self.scope["user"].username
            })

    def update_game(self, event):
        url = event["url"]
        creator = event["creator"]
        num_players = event["num_players"]

        content = {
            'type': 'UPDATE_GAME',
            'url': url,
            'creator': creator,
            'num_players': num_players,
        }
        self.send_json(content)

    def remove_game(self, event):
        url = event["url"]

        content = {
            'type': 'REMOVE_GAME',
            'url': url,
        }
        self.send_json(content)

    def chat_message(self, event):
        content = {
            'type': 'CHAT_MESSAGE',
            'chat_message': event["chat_message"],
            'player': event["player"]
        }
        self.send_json(content)


class GameRoomConsumer(JsonWebsocketConsumer):

    GROUP_NAME_PREFIX = "GAME-"

    def send_json(self, content):
        super().send_json(content)
        print("Sending Message: {}".format(content['type']))

    @classmethod
    def chat_broadcast(cls, data, url):
        channel_layer = get_channel_layer()
        data['type'] = 'chat_message'
        # Send message to room group
        async_to_sync(channel_layer.group_send)(
            cls.GROUP_NAME_PREFIX+url, data
        )

    @classmethod
    def add_player_broadcast(cls, data, url):
        channel_layer = get_channel_layer()
        data['type'] = 'player_added'
        # Send message to room group
        async_to_sync(channel_layer.group_send)(
            cls.GROUP_NAME_PREFIX+url, data
        )

    @classmethod
    def remove_player_broadcast(cls, data, url):
        channel_layer = get_channel_layer()
        data['type'] = 'player_removed'
        # Send message to room group
        async_to_sync(channel_layer.group_send)(
            cls.GROUP_NAME_PREFIX+url, data
        )

    @classmethod
    def start_game_broadcast(cls, data, url):
        channel_layer = get_channel_layer()
        data['type'] = 'game_started'
        # Send message to room group
        async_to_sync(channel_layer.group_send)(
            cls.GROUP_NAME_PREFIX+url, data
        )

    @classmethod
    def start_game_all_ready_broadcast(cls, data, url):
        channel_layer = get_channel_layer()
        data['type'] = 'game_started_all_ready'
        # Send message to room group
        async_to_sync(channel_layer.group_send)(
            cls.GROUP_NAME_PREFIX+url, data
        )

    @classmethod
    def turn_broadcast(cls, data, url):
        channel_layer = get_channel_layer()
        data['type'] = 'turn_changed'
        # Send message to room group
        async_to_sync(channel_layer.group_send)(
            cls.GROUP_NAME_PREFIX+url, data
        )

    @classmethod
    def player_hit_broadcast(cls, data, url):
        channel_layer = get_channel_layer()
        data['type'] = 'player_hit'
        # Send message to room group
        async_to_sync(channel_layer.group_send)(
            cls.GROUP_NAME_PREFIX+url, data
        )

    @classmethod
    def player_ready_broadcast(cls, data, url):
        channel_layer = get_channel_layer()
        data['type'] = 'player_ready'
        # Send message to room group
        async_to_sync(channel_layer.group_send)(
            cls.GROUP_NAME_PREFIX+url, data
        )

    @classmethod
    def dealer_turn_broadcast(cls, data, url):
        channel_layer = get_channel_layer()
        data['type'] = 'dealer_final_turn'
        # Send message to room group
        async_to_sync(channel_layer.group_send)(
            cls.GROUP_NAME_PREFIX+url, data
        )

    @classmethod
    def players_blackjack_broadcast(cls, data, url):
        channel_layer = get_channel_layer()
        data['type'] = 'players_blackjack'
        # Send message to room group
        async_to_sync(channel_layer.group_send)(
            cls.GROUP_NAME_PREFIX+url, data
        )

    def connect(self):
        if self.scope["user"].is_anonymous:
            self.close()
        game_url = self.scope["url_route"]["kwargs"]["game_url"]
        game = GameSession.objects.get_game(game_url)
        if game is None:
            self.close()
        self.game_url = game_url
        self.game_creator = game.creator.username
        # Join Game Group
        async_to_sync(self.channel_layer.group_add)(
            GameRoomConsumer.GROUP_NAME_PREFIX + self.game_url,
            self.channel_name
        )
        self.accept()
        self.add_player()

    def add_player(self):
        url = self.game_url
        creator_username = self.game_creator
        current_player = self.scope["user"].username

        num_players = live_games._redis_add_player(
            self, url, creator_username, current_player)

        # Send lobby Updates
        if num_players > 0 and num_players < MAX_PLAYERS_PER_GAME:
            LobbyConsumer.update_game_broadcast({
                'url': url,
                'creator': creator_username,
                'num_players': num_players
            })
        else:
            LobbyConsumer.remove_game_broadcast({
                'url': url
            })

    def disconnect(self, close_code):
        self.remove_player()
        # Leave game group
        async_to_sync(self.channel_layer.group_discard)(
            GameRoomConsumer.GROUP_NAME_PREFIX + self.game_url,
            self.channel_name
        )

    def remove_player(self):
        url = self.game_url
        creator_username = self.game_creator

        num_players, player_removed = live_games._redis_remove_player(
            self, url)

        if num_players > 0 and num_players < MAX_PLAYERS_PER_GAME:
            # Send lobby Updates
            LobbyConsumer.update_game_broadcast({
                'url': url,
                'creator': creator_username,
                'num_players': num_players
            })
        else:
            # Send lobby Updates
            LobbyConsumer.remove_game_broadcast({
                'url': url
            })

        # Inform other players in the game
        GameRoomConsumer.remove_player_broadcast({
            'idx': player_removed.index,
            'player': player_removed.get_json_obj()}, self.game_url)

        game_obj = live_games._get_redis_game_obj_json(self.game_url)
        if game_obj and self.check_if_all_ready(game_obj):
            # sleep for small duration
            sleep(0.1)
            self.start_game_all_ready()

    def receive_json(self, content):
        print("Received Message: {}".format(content))
        message_type = content.get('type', '')
        if message_type == "CHAT":
            GameRoomConsumer.chat_broadcast({
                'chat_message': content['chat_message'],
                'player': self.scope["user"].username
            }, self.game_url)
        elif message_type == "INIT_GAME":
            self.send_init_game()
        elif message_type == "START_GAME":
            self.start_game()
        elif message_type == "HIT":
            self.hit(content.get('idx', None))
        elif message_type == "DOUBLE":
            self.double(content.get('idx', None))
        elif message_type == "HOLD":
            self.hold(content.get('idx', None))
        elif message_type == "PLAYER_READY":
            self.ready_btn(content.get('idx', None), content.get('bet', 5))

    def send_init_game(self):
        game_obj = live_games._get_redis_game_obj_json(self.game_url)
        print(game_obj)
        idx = -1
        for key, val in game_obj['players'].items():
            if val['name'] == self.channel_name:
                idx = key
                break
        content = {
            'type': 'INIT_GAME',
            'my_idx': idx,
            'state': game_obj
        }
        self.send_json(content)
        sleep(0.05)
        # Also inform other players of the new player arrived
        GameRoomConsumer.add_player_broadcast({
            'idx': idx,
            'player': game_obj['players'][idx]
        }, self.game_url)

    def start_game(self):
        game_obj = live_games._get_redis_game_obj_json(self.game_url)
        
        if (game_obj['game_state'] == live_games.GameState.STARTED.value or
                game_obj['game_state'] == live_games.GameState.AWAITING_READY.value):
            return
        
        started_game_obj = live_games._redis_start_game(self.game_url)

        # Init game object correctly and inform clients to make bets
        GameRoomConsumer.start_game_broadcast({
            'state': started_game_obj
        }, self.game_url)

    def start_game_all_ready(self):
        game_obj, status = live_games._redis_start_game_all_ready(
            self.game_url)
        # Dealdeal all cards then inform clients
        GameRoomConsumer.start_game_all_ready_broadcast({
            'state': game_obj
        }, self.game_url)

        # Check blackjack
        game_obj = live_games._redis_check_initial_blackjack(self.game_url)

        # Check if players have any blackjack
        player_blackjacks = []
        for idx, player_obj in game_obj['players'].items():
            if player_obj["player_game_state"] == live_games.PlayerGameState.GAME_OVER_BLACKJACK.value:
                player_blackjacks.append(idx)
        # If players have blackjack, inform clients
        if len(player_blackjacks) > 0:
            # sleep for small duration
            sleep(0.05)
            GameRoomConsumer.players_blackjack_broadcast({
                'players': player_blackjacks
            }, self.game_url)

        # sleep for small duration
        sleep(0.1)

        # If dealer blackjack or all players blackjack
        if (game_obj['dealer_blackjack'] == True or
                game_obj['current_turn'] >= MAX_PLAYERS_PER_GAME):
            game_obj = live_games._redis_dealer_final_turn(self.game_url)
            GameRoomConsumer.dealer_turn_broadcast({
                'state': game_obj
            }, self.game_url)

        # Else send regular turn event
        else:
            GameRoomConsumer.turn_broadcast({
                'state': game_obj
            }, self.game_url)

    def hit(self, idx):
        if not self.is_valid_turn(idx):
            return
        game_obj, status = live_games._redis_player_hit(self.game_url, idx)

        # Inform clients of Player Hit
        if status:
            GameRoomConsumer.player_hit_broadcast({
                'idx': idx,
                'state': game_obj
            }, self.game_url)
        # sleep for small duration
        sleep(0.1)
        # Check is user turn is done, total above 21
        if game_obj['players'][idx]["current_hand_value"] >= 21:
            self.do_next_turn()

    def double(self, idx):
        if not self.is_valid_turn(idx):
            return
        game_obj, status = live_games._redis_player_hit(self.game_url,
                                                        idx, is_double=True)
        # Inform clients of Player Hit
        if status:
            GameRoomConsumer.player_hit_broadcast({
                'idx': idx,
                'state': game_obj
            }, self.game_url)
        # sleep for small duration
        sleep(0.1)
        # End turn after double
        self.do_next_turn()

    def hold(self, idx):
        if not self.is_valid_turn(idx):
            return
        self.do_next_turn()

    def ready_btn(self, idx, bet):
        if idx is None or idx < 0 or idx >= MAX_PLAYERS_PER_GAME:
            return

        game_obj, status = live_games._redis_player_ready(
            self.game_url, idx, bet)
        print("Player Ready Status :: {}".format(status))
        # Inform clients of Player Hit
        if status:
            GameRoomConsumer.player_ready_broadcast({
                'idx': idx,
                'state': game_obj
            }, self.game_url)

        if self.check_if_all_ready(game_obj):
            # sleep for small duration
            sleep(0.1)
            self.start_game_all_ready()

    def do_next_turn(self):
        game_obj, next_turn = live_games._redis_next_turn(self.game_url)
        if next_turn >= MAX_PLAYERS_PER_GAME:
            # Dealer Turn
            game_obj = live_games._redis_dealer_final_turn(self.game_url)
            GameRoomConsumer.dealer_turn_broadcast({
                'state': game_obj
            }, self.game_url)
        else:
            GameRoomConsumer.turn_broadcast({
                'state': game_obj
            }, self.game_url)

    def check_if_all_ready(self, game_obj):
        if game_obj['game_state'] != live_games.GameState.AWAITING_READY.value:
            return False
        for player_obj in game_obj['players'].values():
            if not player_obj['in_game']:
                continue
            elif (player_obj['player_game_state'] ==
                  live_games.PlayerGameState.AWAITING_READY.value):
                return False
        return True

    def is_valid_turn(self, idx):
        if idx is None:
            print("idx is None")
            return False

        game_obj = live_games._get_redis_game_obj_json(self.game_url)
        if game_obj["current_turn"] != idx:
            print("Not a valid turn! Current turn not same as idx")
            return False

        current_player = game_obj['players'].get(idx, None)
        if current_player:
            current_player_channel_name = current_player['name']
        else:
            current_player_channel_name = None
        if current_player_channel_name != self.channel_name:
            print(
                "Not a valid turn! "
                "Current turn channel name does not match current consumer")
            return False

        return True

    def chat_message(self, event):
        content = {
            'type': 'CHAT_MESSAGE',
            'chat_message': event["chat_message"],
            'player': event["player"]
        }
        self.send_json(content)

    def player_added(self, event):
        content = {
            'type': 'PLAYER_ADDED',
            'idx': event["idx"],
            'player_added': event["player"]
        }
        self.send_json(content)

    def player_removed(self, event):
        content = {
            'type': 'PLAYER_REMOVED',
            'idx': event["idx"],
            'player_removed': event["player"]
        }
        self.send_json(content)

    def game_started(self, event):
        content = {
            'type': 'GAME_STARTED',
            'state': event["state"]
        }
        self.send_json(content)

    def game_started_all_ready(self, event):
        content = {
            'type': 'GAME_STARTED_ALL_READY',
            'state': event["state"]
        }
        self.send_json(content)

    def turn_changed(self, event):
        content = {
            'type': 'NEXT_TURN',
            'state': event["state"]
        }
        self.send_json(content)

    def player_hit(self, event):
        content = {
            'type': 'PLAYER_HIT',
            'state': event["state"],
            'idx': event['idx']
        }
        self.send_json(content)

    def player_ready(self, event):
        content = {
            'type': 'PLAYER_READY',
            'state': event["state"],
            'idx': event['idx']
        }
        self.send_json(content)

    def dealer_final_turn(self, event):
        content = {
            'type': 'DEALER_FINAL_TURN',
            'state': event["state"],
        }
        self.send_json(content)

    def players_blackjack(self, event):
        content = {
            'type': 'PLAYERS_BLACKJACK',
            'players': event["players"],
        }
        self.send_json(content)
