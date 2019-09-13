from .models import GameSession
from math import ceil
from django.conf import settings
from enum import Enum
import functools
from typing import Dict, List, Optional
from random import choice
from redis import StrictRedis
import pickle


KEY_FORMAT = "GAME:{}:GAME"
LOCK_FORMAT = "LOCK:{}:LOCK"
MAX_PLAYERS_PER_GAME = getattr(settings, 'MAX_PLAYERS_PER_GAME', 3)

SUITS = ["spades", "hearts", "clubs", "diams"]
NUMBERS = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
# BGCOLORS = {'D': 'red', 'C': 'black', 'H': 'red', 'S': 'black'}


class Player(object):
    def __init__(self, name, username):
        self.name = name
        self.index = -1
        self.dollars = 100
        self.current_bet = 0
        self.win_loss = 0
        self.username = username
        self.in_game = False
        self.current_hand = []
        self.player_game_state = PlayerGameState.GAME_NOT_STARTED
        self.player_game_outcome = PlayerGameOutcome.NA

    def get_json_obj(self):
        return {
            "name": self.name,
            "username": self.username,
            "index": self.index,
            "dollars": self.dollars,
            "current_bet": self.current_bet,
            "in_game": self.in_game,
            "current_hand": self.current_hand,
            "player_game_state": self.player_game_state.value,
            "player_game_outcome": self.player_game_outcome.value,
            "win_loss": self.win_loss,
            "current_hand_value": functools.reduce(lambda x, y: x+y['value'],
                                                   self.current_hand, 0)
        }


class GameObj(object):
    def __init__(self, url, creator_username):
        self.url = url
        self.creator = creator_username
        self.players_map: Dict[str, int] = {}
        self.players_list: List[Optional[Player]] = [None]*MAX_PLAYERS_PER_GAME
        self.game_state = GameState.NOT_STARTED
        self.current_turn = -1
        self.dealer_hand = []
        self.dealer_blackjack = False

    def get_json_obj(self):
        obj = {}
        obj['url'] = self.url
        obj['players'] = {}
        for idx in range(len(self.players_list)):
            if self.players_list[idx] is not None:
                obj['players'][idx] = self.players_list[idx].get_json_obj()
        obj['game_state'] = self.game_state.value
        obj['current_turn'] = self.current_turn
        obj['dealer_hand'] = self.dealer_hand
        obj['dealer_blackjack'] = self.dealer_blackjack
        obj['dealer_hand_value'] = functools.reduce(lambda x, y: x+y['value'],
                                                    self.dealer_hand, 0)
        return obj

    def start_game(self):
        # update game state
        self.game_state = GameState.AWAITING_READY
        self.current_turn = -1

        # Update Dealer hand
        self.dealer_hand.clear()
        self.dealer_blackjack = False

        # Update all player objects
        for p in self.players_list:
            if p:
                p.in_game = True
                p.current_hand.clear()
                p.player_game_state = PlayerGameState.AWAITING_READY
                p.player_game_outcome = PlayerGameOutcome.NA
                p.win_loss = 0
                p.current_bet = 0

    def start_game_all_ready(self):
        if self.game_state == GameState.STARTED:
            return False

        self.game_state = GameState.STARTED
        
        # Deal initial cards to everyone
        self.deal_initial_cards()

        # #### To Delete #####
        # c = choice([0,1,3, 4, 5, 6, 7 , 8 ,9, 10, 11, 12])
        # if c == 0:
        #     print("Making dealer blackjack")
        #     self.dealer_hand[0]['value'] = 11
        #     self.dealer_hand[0]['num'] = 'A'
        #     self.dealer_hand[1]['value'] = 10
        #     self.dealer_hand[1]['num'] = 'K'

        # for p in self.players_list:
        #     if p: 
        #         c = choice([0])
        #         if c == 0 and p.index == 0:
        #             print("Making Blackjack")
        #             p.current_hand[0]['value'] = 11
        #             p.current_hand[0]['num'] = 'A'
        #             p.current_hand[1]['value'] = 10
        #             p.current_hand[1]['num'] = 'K'
        # ####################

        return True

    def deal_initial_cards(self):
        # Deal dealer cards
        self.dealer_hand.append(deal_card())
        self.dealer_hand.append(deal_card())

        # Iterate over players and deal cards
        for p in self.players_list:
            if p and p.in_game:
                p.player_game_state = PlayerGameState.GAME_STARTED
                p.current_hand.append(deal_card())
                p.current_hand.append(deal_card())

    def do_next_turn(self):
        self.current_turn = self.get_next_turn(self.current_turn)
        return self.current_turn

    def get_next_turn(self, prev_turn):
        start = prev_turn + 1
        while (start < len(self.players_list)):
            if (self.players_list[start] and 
                self.players_list[start].in_game and
                self.players_list[start].player_game_state == PlayerGameState.GAME_STARTED):
                return start
            else:
                start += 1
        return start + 1000

    def player_hit(self, idx, is_double=False):
        player_obj = self.players_list[idx]
        if player_obj is None:
            print("player_hit:: player_obj is None")
            return False
        player_obj.current_hand.append(deal_card())
        if is_double:
            player_obj.dollars -= player_obj.current_bet
            player_obj.current_bet *= 2
        return True

    def dealer_final_turn(self):
        dealer_total = functools.reduce(lambda x, y: x+y['value'],
                                        self.dealer_hand, 0)
        while (dealer_total < 17):
            card = deal_card()
            dealer_total += card['value']
            self.dealer_hand.append(card)
        self.calculate_score()
        self.game_state = GameState.NOT_STARTED

    def player_ready(self, idx, bet):
        player_obj = self.players_list[idx]
        if player_obj is None:
            print("player_ready:: player_obj is None")
            return False
        if player_obj.player_game_state == PlayerGameState.AWAITING_READY:
            player_obj.current_bet = bet
            player_obj.dollars -= bet
            player_obj.player_game_state = PlayerGameState.READY
            return True
        return False

    def check_initial_blackjack(self):
        dealer_total = functools.reduce(lambda x, y: x+y['value'],
                                        self.dealer_hand, 0)
        if dealer_total == 21:
            self.dealer_blackjack = True

        # Iterate over players and check for blackjack
        for p in self.players_list:
            if p and p.player_game_state == PlayerGameState.GAME_STARTED:
                player_total = functools.reduce(lambda x, y: x+y['value'],
                                                p.current_hand, 0)
                if player_total == 21:
                    p.player_game_state = PlayerGameState.GAME_OVER_BLACKJACK

        # Update next turn based on player blackjack
        self.do_next_turn()

        # if self.dealer_blackjack:
        #     self.calculate_score()
        #     self.game_state = GameState.NOT_STARTED

    def calculate_score(self):
        dealer_total = functools.reduce(lambda x, y: x+y['value'],
                                        self.dealer_hand, 0)
        # Iterate over players and calculate winnings/losings
        for p in self.players_list:
            if not p or p.in_game == False:
                continue
            player_total = functools.reduce(lambda x, y: x+y['value'],
                                                p.current_hand, 0)
            # player busted , so player lose
            if player_total > 21:
                p.player_game_outcome = PlayerGameOutcome.LOSS
                p.win_loss = p.current_bet

            # Player Blackjack
            elif p.player_game_state == PlayerGameState.GAME_OVER_BLACKJACK:
                if self.dealer_blackjack == True:
                    p.player_game_outcome = PlayerGameOutcome.PUSH
                    p.win_loss = 0
                else:
                    p.player_game_outcome = PlayerGameOutcome.WIN
                    p.win_loss = ceil(1.5 * p.current_bet)

            # Player Stay
            else:
                if self.dealer_blackjack == True:
                    p.player_game_outcome = PlayerGameOutcome.LOSS
                    p.win_loss = p.current_bet
                elif dealer_total > 21:
                    p.player_game_outcome = PlayerGameOutcome.WIN
                    p.win_loss = p.current_bet
                elif player_total > dealer_total:
                    p.player_game_outcome = PlayerGameOutcome.WIN
                    p.win_loss = p.current_bet
                elif player_total < dealer_total:
                    p.player_game_outcome = PlayerGameOutcome.LOSS
                    p.win_loss = p.current_bet
                else:
                    p.player_game_outcome = PlayerGameOutcome.PUSH
                    p.win_loss = 0

            p.dollars += p.current_bet
            p.current_bet = 0
            if p.player_game_outcome == PlayerGameOutcome.WIN:
                p.dollars += p.win_loss
            elif p.player_game_outcome == PlayerGameOutcome.LOSS:
                p.dollars -= p.win_loss


def deal_card():
    card = {}
    card['suit'] = choice(SUITS)
    card['num'] = choice(NUMBERS)
    #card['bg'] = BGCOLORS[card['suit']]

    def get_value(num):
        try:
            val = int(num)
            return val
        except ValueError:
            if num == 'A':
                return 11
            else:
                return 10

    card['value'] = get_value(card['num'])
    return card


class GameState(Enum):
    NOT_STARTED = "not-started"
    AWAITING_READY = "awaiting-ready"
    STARTED = "started"


class PlayerGameState(Enum):
    GAME_NOT_STARTED = "game-not-started"
    AWAITING_READY = "awaiting-ready"
    READY = "ready"
    GAME_STARTED = "game-started"
    GAME_OVER_BLACKJACK = "game-over-blackjack"
    
class PlayerGameOutcome(Enum):
    NA = "na"
    WIN = "win"
    LOSS = "loss"
    PUSH = "push"


def _get_redis_conn():
    redis_configs = getattr(settings, 'LIVE_GAMES_REDIS_CONFIG', {})
    return StrictRedis(host=redis_configs.get('host', 'localhost'),
                       port=redis_configs.get('port', 6379),
                       db=redis_configs.get('db', 0))


def _get_redis_game_obj_json(url):
    r = _get_redis_conn()
    key = KEY_FORMAT.format(url)
    lock_key = LOCK_FORMAT.format(url)

    with r.lock(lock_key):
        if r.exists(key):
            ret_obj = pickle.loads(r.get(key)).get_json_obj()
        else:
            ret_obj = None
    return ret_obj


def _redis_add_player(player_consumer, url, creator_username, current_player):
    r = _get_redis_conn()
    key = KEY_FORMAT.format(url)
    lock_key = LOCK_FORMAT.format(url)

    with r.lock(lock_key):
        if r.exists(key):
            game_obj = pickle.loads(r.get(key))
        else:
            game_obj = GameObj(url=url, creator_username=creator_username)

        player = _add_to_game_obj(
            player_consumer.channel_name, game_obj, current_player)
        r.set(key, pickle.dumps(game_obj))

    num_players = len(game_obj.players_map)

    # Update Database
    GameSession.objects.update_num_players(url, num_players)
    return num_players


def _redis_remove_player(player_consumer, url):
    r = _get_redis_conn()
    key = KEY_FORMAT.format(url)
    lock_key = LOCK_FORMAT.format(url)

    with r.lock(lock_key):
        game_obj = pickle.loads(r.get(key))
        player = _remove_from_game_obj(player_consumer.channel_name, game_obj)
        num_players = len(game_obj.players_map)
        if num_players == 0:
            r.delete(key)
        else:
            r.set(key, pickle.dumps(game_obj))

    if num_players == 0:
        GameSession.objects.delete_game_session(url)
    else:
        GameSession.objects.update_num_players(url, num_players)
    return num_players, player


def _redis_start_game(url):
    r = _get_redis_conn()
    key = KEY_FORMAT.format(url)
    lock_key = LOCK_FORMAT.format(url)
    with r.lock(lock_key):
        game_obj = pickle.loads(r.get(key))
        game_obj.start_game()
        r.set(key, pickle.dumps(game_obj))
    return _get_redis_game_obj_json(url)


def _redis_start_game_all_ready(url):
    r = _get_redis_conn()
    key = KEY_FORMAT.format(url)
    lock_key = LOCK_FORMAT.format(url)
    with r.lock(lock_key):
        game_obj = pickle.loads(r.get(key))
        status = game_obj.start_game_all_ready()
        r.set(key, pickle.dumps(game_obj))
    return _get_redis_game_obj_json(url), status


def _redis_player_hit(url, idx, is_double=False):
    r = _get_redis_conn()
    key = KEY_FORMAT.format(url)
    lock_key = LOCK_FORMAT.format(url)
    with r.lock(lock_key):
        game_obj = pickle.loads(r.get(key))
        status = game_obj.player_hit(idx, is_double)
        r.set(key, pickle.dumps(game_obj))
    return _get_redis_game_obj_json(url), status


def _redis_next_turn(url):
    r = _get_redis_conn()
    key = KEY_FORMAT.format(url)
    lock_key = LOCK_FORMAT.format(url)
    with r.lock(lock_key):
        game_obj = pickle.loads(r.get(key))
        next_turn = game_obj.do_next_turn()
        r.set(key, pickle.dumps(game_obj))
    return _get_redis_game_obj_json(url), next_turn


def _redis_dealer_final_turn(url):
    r = _get_redis_conn()
    key = KEY_FORMAT.format(url)
    lock_key = LOCK_FORMAT.format(url)
    with r.lock(lock_key):
        game_obj = pickle.loads(r.get(key))
        game_obj.dealer_final_turn()
        r.set(key, pickle.dumps(game_obj))
    return _get_redis_game_obj_json(url)


def _redis_player_ready(url, idx, bet):
    r = _get_redis_conn()
    key = KEY_FORMAT.format(url)
    lock_key = LOCK_FORMAT.format(url)
    with r.lock(lock_key):
        game_obj = pickle.loads(r.get(key))
        status = game_obj.player_ready(idx, bet)
        r.set(key, pickle.dumps(game_obj))
    return _get_redis_game_obj_json(url), status


def _redis_check_initial_blackjack(url,):
    r = _get_redis_conn()
    key = KEY_FORMAT.format(url)
    lock_key = LOCK_FORMAT.format(url)
    with r.lock(lock_key):
        game_obj = pickle.loads(r.get(key))
        game_obj.check_initial_blackjack()
        r.set(key, pickle.dumps(game_obj))
    return _get_redis_game_obj_json(url)


def _add_to_game_obj(player_name, game_obj, current_player):
    if None in game_obj.players_list:
        idx = game_obj.players_list.index(None)
        player = Player(player_name, current_player)
        player.index = idx
        game_obj.players_list[idx] = player
        game_obj.players_map[player_name] = idx
        return player
    return None


def _remove_from_game_obj(player_name, game_obj):
    if player_name in game_obj.players_map:
        idx = game_obj.players_map[player_name]
        player = game_obj.players_list[idx]
        game_obj.players_list[idx] = None
        game_obj.players_map.pop(player_name, None)
        return player
    return None
