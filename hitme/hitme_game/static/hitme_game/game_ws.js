/**
 * Game channels 
 */
$(function() {
    var script_tag = document.getElementById('websocket_js');
    var url = script_tag.getAttribute("data-game");

    var gameSocket = new WebSocket(
        'ws://' + window.location.host +
        '/ws/game/' + url + '/');

    window.onbeforeunload = function() {
        gameSocket.onclose = function() {}; // disable onclose handler first
        gameSocket.close();
    };

    gameSocket.onmessage = function(e) {
        var data = JSON.parse(e.data);
        var type = data['type'];

        if (type == "CHAT_MESSAGE") {
            add_chat_message(data['player'], data['chat_message']);
        } else if (type == "INIT_GAME") {
            init_game(data['state'], data['my_idx']);
        } else if (type == "PLAYER_ADDED") {
            player_added(data['idx'], data['player_added']);
        } else if (type == "PLAYER_REMOVED") {
            player_removed(data['idx'], data['player_removed']);
        } else if (type == "GAME_STARTED") {
            game_started(data['state']);
        } else if (type == "GAME_STARTED_ALL_READY") {
            game_started_all_ready(data['state']);
        } else if (type == "NEXT_TURN") {
            next_turn(data['state']);
        } else if (type == "PLAYER_HIT") {
            player_hit(data['idx'], data['state']);
        } else if (type == "PLAYER_READY") {
            player_ready(data['idx'], data['state']);
        } else if (type == "DEALER_FINAL_TURN") {
            dealer_final_turn(data['state']);
        } else if (type == "PLAYERS_BLACKJACK") {
            players_blackjack(data['players']);
        }
    };

    gameSocket.onopen = function(e) {
        gameSocket.send(JSON.stringify({
            'type': "INIT_GAME"
        }));
    };

    // Game chat
    document.querySelector('#game-chat-input').onkeyup = function(e) {
        if (e.keyCode === 13) { // enter, return
            document.querySelector('#game-chat-submit').click();
        }
    };

    document.querySelector('#game-chat-submit').onclick = function(e) {
        var inputDom = document.querySelector('#game-chat-input');
        var input = inputDom.value;
        if (input != '' && input != '\n') {
            gameSocket.send(JSON.stringify({
                'type': "CHAT",
                'chat_message': input
            }));
        }

        inputDom.value = '';
    };

    // Game play
    document.querySelector('#btnstart').onclick = function(e) {
        gameSocket.send(JSON.stringify({
            'type': "START_GAME"
        }));
    };

    $('[id="maxbet"]').click(function() {
        var total = $("div.player1#player-" + window.my_idx + " span#dollars").html();
        $("div.player1#player-" + window.my_idx + " input#mybet").val(total);
    });

    $('[id="btnhold"]').click(function() {
        gameSocket.send(JSON.stringify({
            'type': "HOLD",
            'idx': window.my_idx
        }));
    });

    $('[id="btnhit"]').click(function() {
        gameSocket.send(JSON.stringify({
            'type': "HIT",
            'idx': window.my_idx
        }));
    });

    $('[id="btndouble"]').click(function() {
        gameSocket.send(JSON.stringify({
            'type': "DOUBLE",
            'idx': window.my_idx
        }));
    });

    $('[id="btndeal"]').click(function() {
        var bet = parseInt($("div.player1#player-" + window.my_idx + " input#mybet").val()) || 5;
        gameSocket.send(JSON.stringify({
            'type': "PLAYER_READY",
            'idx': window.my_idx,
            'bet': bet
        }));
    });    
    
});

/**
 * Chat logic
 */
function add_chat_message(player, chat) {
    document.querySelector('#game-chat-log').value += (player + ': ' + chat + '\n');
    document.getElementById("game-chat-log").scrollTop = document.getElementById("game-chat-log").scrollHeight
}

function init_game(state, my_idx) {
    window.my_idx = my_idx;
    window.my_username = state['players'][my_idx]['username'];
    window.my_channel = state['players'][my_idx]['name']
    var dollars = state['players'][my_idx]['dollars'];
    disable_other_controls();
    activate_my_game(dollars);
    add_other_players(state);

}

function activate_my_game(dollars) {
    var heading_message = "This is your game, " + window.my_username;
    // Set Heading
    $("div.player1#player-" + window.my_idx + " div#player-heading").addClass('bold-heading');
    $("div.player1#player-" + window.my_idx + " div#player-heading").html(heading_message);
    // Disable Button
    $("div.player1#player-" + window.my_idx + " button#maxbet").hide();
    $("div.player1#player-" + window.my_idx + " div#myactions").hide();
    $("div.player1#player-" + window.my_idx + " button#btndeal").hide();

    // Fill dollars
    $("div.player1#player-" + window.my_idx + " span#dollars").html(dollars);

    // Init my bet input
    $("div.player1#player-" + window.my_idx + " input#mybet").val("");
    $("div.player1#player-" + window.my_idx + " input#mybet").prop("disabled", true);
}

function disable_other_controls() {
    player_ids = [0, 1, 2];
    for (let idx of player_ids) {
        if (idx != window.my_idx)
            disable_controls(idx);
    }
}

function disable_controls(idx) {
    // Hide all buttons
    $("div.player1#player-" + idx + " button#maxbet").hide();
    $("div.player1#player-" + idx + " div#myactions").hide();
    $("div.player1#player-" + idx + " button#btndeal").hide();

    // Disbale my bet
    $("div.player1#player-" + idx + " input#mybet").val("");
    $("div.player1#player-" + idx + " input#mybet").prop("disabled", true);
}

function add_other_players(state) {
    player_ids = [0, 1, 2];
    for (let idx of player_ids) {
        if (idx != window.my_idx)
            if (idx in state['players']) {
                init_other_player(idx, state['players'][idx]);
            } else {
                hide_player_box(idx);
            }
    }
}

function init_other_player(idx, player_obj) {
    var heading_message = "Player: " + player_obj['username'];
    var dollars = player_obj['dollars'];
    $("div.player1#player-" + idx.toString() + " div#player-heading").html(heading_message);
    $("div.player1#player-" + idx.toString() + " span#dollars").html(dollars);
}

function hide_player_box(idx) {
    $("div.player1#player-" + idx + " div.game-box").hide();
}

function player_added(idx, player_obj) {
    if (window.my_channel == player_obj["name"])
        return;
    init_other_player(idx, player_obj);
    $("div.player1#player-" + idx + " div.game-box").show();
    disable_controls(idx);
}

function player_removed(idx, player_obj) {
    if (window.my_channel == player_obj["name"])
        return;
    $("div.player1#player-" + idx.toString() + " div#player-heading").html("No Player Joined!");
    hide_player_box(idx);
}

function game_started(game_state) {
    $("div#start button#btnstart").hide();
    clear_dealer_hand();

    // Add Waiting message for all and clear all player hands
    for (let idx in game_state['players']) {
        set_waiting_message(idx);
        clear_hand(idx);
    }
    // Show my ready button
    $("div.player1#player-" + window.my_idx + " button#btndeal").show();

    // Enable my Bet controls
    $("div.player1#player-" + window.my_idx + " input#mybet").val("5");
    $("div.player1#player-" + window.my_idx + " input#mybet").prop("disabled", false);
    $("div.player1#player-" + window.my_idx + " button#maxbet").show();

    // Set Message
    $("div.player1#player-" + window.my_idx + " div#message").html("Select your Bet and Press Ready!");

}

function clear_hand(idx) {
    $("div.player1#player-" + idx + " span#pValue").html("");
    $("div.player1#player-" + idx + " div#playerHolder").html("");
}

function clear_dealer_hand() {
    var dealerHolder = document.getElementById('dealerHolder');
    dealerHolder.innerHTML = "";
    $("span#dValue").html("");
}

function game_started_all_ready(game_state) {
    show_dealer_intial_cards(game_state);
    // Set player Message and show player card
    for (let idx in game_state['players']) {
        show_players_intial_cards(idx, game_state['players'][idx]);
        set_waiting_message(idx);
    }
}

function set_waiting_message(idx) {
    $("div.player1#player-" + idx + " div#message").html("Waiting...");
}

function show_dealer_intial_cards(game_state) {
    if (game_state["dealer_hand"].length != 2) {
        alert("Error! Dealer did not get 2 cards.");
        return;
    }
    var dealerHolder = document.getElementById('dealerHolder');
    dealerHolder.innerHTML += cardOutput(game_state["dealer_hand"][0], 0);
    // Cover Dealer's first card
    dealerHolder.innerHTML += '<div id="cover" style="left:100px;"></div>';
    dealerHolder.innerHTML += cardOutput(game_state["dealer_hand"][1], 1);
}

function show_players_intial_cards(idx, player_obj) {
    if (player_obj["current_hand"].length != 2) {
        alert("Error! Player " + idx + " did not get 2 cards.");
        return;
    }
    // Add Player cards
    for (let i = 0; i < player_obj["current_hand"].length; i++)
        $("div.player1#player-" + idx + " div#playerHolder").append(cardOutput(player_obj["current_hand"][i], i));
    // Update Player hand total
    $("div.player1#player-" + idx + " span#pValue").html(player_obj["current_hand_value"])

}


function cardOutput(card, card_position) {

    /* where the card is being displayed */
    /* changing this line from ... to*/
    /* var hpos = (x > 0) ? x * 60 + 100 : 100; */
    var hpos = (card_position > 0) ? card_position * 30 + 100 : 100;
    return '<div class="icard ' + card["suit"] + '" style="left:' + hpos + 'px;">  <div class="top-card suit">' + card["num"] + '<br></div>  <div class="content-card suit"></div>  <div class="bottom-card suit">' + card["num"] +
        '<br></div> </div>';
}

function next_turn(game_state) {
    // Set Waiting message for everybody
    for (let idx in game_state['players']) {
        set_waiting_message(idx);
    }
    // Hide my actions if they are displayed
    hide_my_actions();
    //If my turn then enable controls and set message
    if (game_state["current_turn"] == window.my_idx)
        my_turn(game_state["current_turn"]);
    else
        other_player_turn(game_state["current_turn"]);

}

function my_turn(my_idx) {
    var message = "<center><b>Your Turn</b><br>Get up to 21 and beat the dealer to win.</center>"
    $("div.player1#player-" + my_idx + " div#message").html(message);
    show_my_actions();
}

function other_player_turn(idx) {
    var message = "<center><b>Currently Playing Turn...</b></center>"
    $("div.player1#player-" + idx + " div#message").html(message);
}

function hide_my_actions() {
    $("div.player1#player-" + window.my_idx + " div#myactions").hide();
}

function show_my_actions() {
    $("div.player1#player-" + window.my_idx + " div#myactions").show();
}

function player_hit(idx, game_state) {
    var player = game_state['players'][idx];
    var hand = player['current_hand'];
    var last_card = hand[hand.length - 1];
    $("div.player1#player-" + idx + " div#playerHolder").append(cardOutput(last_card, hand.length - 1));
    // Update Player hand total
    $("div.player1#player-" + idx + " span#pValue").html(player["current_hand_value"])
    // Update Player bet and dollars (used for double)

    // Set total and bet amounts
    var bet = player['current_bet'];
    var total = player['dollars'];
    $("div.player1#player-" + idx + " span#dollars").html(total);
    $("div.player1#player-" + idx + " input#mybet").val(bet);
    $("div.player1#player-" + idx + " input#mybet").prop("disabled", true);

}

function player_ready(idx, game_state) {
    var player = game_state['players'][idx];
    var bet = player['current_bet'];
    var total = player['dollars'];

    // Set total and bet amounts
    $("div.player1#player-" + idx + " span#dollars").html(total);
    $("div.player1#player-" + idx + " input#mybet").val(bet);
    $("div.player1#player-" + idx + " input#mybet").prop("disabled", true);
    
    // Hide ready and bet buttons
    $("div.player1#player-" + idx + " button#btndeal").hide();
    $("div.player1#player-" + idx + " button#maxbet").hide();

    // Set Message
    $("div.player1#player-" + idx + " div#message").html("Player Ready!");
}

function dealer_final_turn(game_state) {
    // Hide my actions if they are displayed
    hide_my_actions();

    // Set Waiting message for everybody
    for (let idx in game_state['players']) {
        set_waiting_message(idx);
    }

    var dealerHolder = document.getElementById('dealerHolder');
    dealerHolder.innerHTML = "";
    for (let i=0; i<game_state['dealer_hand'].length; i++) {
        dealerHolder.innerHTML += cardOutput(game_state["dealer_hand"][i], i);    
    }
    
    // Update dealer total
    if (game_state['dealer_blackjack'] == true)
        $("span#dValue").html("<b>Blackjack!</b>");
    else 
        $("span#dValue").html(game_state["dealer_hand_value"]);

    // Update player messages
    for (let idx in game_state['players']) {
        var win_loss = game_state['players'][idx]['win_loss'];
        var total = game_state['players'][idx]['dollars'];
        var outcome = game_state['players'][idx]['player_game_outcome'];
        if (outcome == 'win') {
            set_win_message(idx, win_loss);
        } else if (outcome == 'loss') {
            set_loss_message(idx, win_loss);
        } else if (outcome == 'push') {
            set_push_message(idx);
        }
        // clear current input and update total
        $("div.player1#player-" + idx + " span#dollars").html(total);
        $("div.player1#player-" + idx + " input#mybet").val("");
    }

    // Show start button to begin game again
    $("div#start button#btnstart").show();
}

function set_win_message(idx, win_loss) {
    if (idx == window.my_idx)
        $("div.player1#player-" + idx + " div#message").html('<span style="color:green;">You Win! You won $' + win_loss + '</span>');
    else
        $("div.player1#player-" + idx + " div#message").html('<span style="color:green;">Player Wins!</span>');
}

function set_loss_message(idx, win_loss) {
    if (idx == window.my_idx)
        $("div.player1#player-" + idx + " div#message").html('<span style="color:red;">Dealer Wins! You lost $' + win_loss + '</span>');
    else
        $("div.player1#player-" + idx + " div#message").html('<span style="color:red;">Dealer Wins!</span>');
}

function set_push_message(idx) {
    if (idx == window.my_idx)
        $("div.player1#player-" + idx + " div#message").html('<span style="color:blue;">It\'s a Draw! You neither win nor lose.</span>');
    else
        $("div.player1#player-" + idx + " div#message").html('<span style="color:blue;">It\'s a Draw!</span>');
}

function players_blackjack(players) {
    console.log(players);
    for (let idx of players) {
        // Update Player hand total
        $("div.player1#player-" + idx + " span#pValue").html("<b>Blackjack!</b>")
    }
}
