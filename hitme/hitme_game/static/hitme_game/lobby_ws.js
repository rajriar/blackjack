$(function() {
    var lobbySocket = new WebSocket('ws://' + window.location.host + '/ws/lobby/');

    lobbySocket.onmessage = function(e) {
        var data = JSON.parse(e.data);
        var type = data['type'];

        if (type == "UPDATE_GAME")
            update_game(data['url'], data['num_players'], data['creator']);

        else if (type == "REMOVE_GAME")
            remove_game(data['url']);

        else if (type == "CHAT_MESSAGE")
            add_chat_message(data['player'], data['chat_message']);

    };

    lobbySocket.onclose = function(e) {
        console.error('Lobby socket closed unexpectedly');
    };

    document.querySelector('#chat-message-input').onkeyup = function(e) {
        if (e.keyCode === 13) { // enter, return
            document.querySelector('#chat-message-submit').click();
        }
    };

    document.querySelector('#chat-message-submit').onclick = function(e) {
        var messageInputDom = document.querySelector('#chat-message-input');
        var message = messageInputDom.value;

        if (message != '' && message != '\n') {
            lobbySocket.send(JSON.stringify({
                'type': 'CHAT',
                'chat_message': message
            }));
        }

        messageInputDom.value = '';
    };

});

function update_game(url, num_players, creator) {
    if ($('div.row#' + url).length > 0)
        $('div.row#' + url).find($('span#player_count')).html(num_players.toString());
    else
        $('div#active-games-list').append(create_game_div(url, num_players, creator));
}

function remove_game(url) {
    if ($('div.row#' + url).length > 0)
        $('div.row#' + url).remove();
}

function add_chat_message(player, message) {
    document.querySelector('#chat-log').value += (player + ': ' + message + '\n');
    document.getElementById("chat-log").scrollTop = document.getElementById("chat-log").scrollHeight
}

function create_game_div(url, num_players, creator) {
    var $row_div = $("<div></div>", {
        id: url,
        "class": "row"
    });
    var $col_div = $("<div></div>", {
        "class": "col"
    });
    $col_div.append($("<p></p>").html(creator + "'s game, <span id='player_count'>" + num_players + "</span> players"));

    $form_tag = $("<form></form>", {
        "action": "/hitme/game/" + url,
        "target": "_blank"
    });
    $form_tag.append($("<button></button>", {
        "type": "submit",
        "class": "btn btn-danger"
    }).html("Join Game"));
    $col_div.append($form_tag);

    $col_div.append($("<hr>"));

    $row_div.append($col_div);
    return $row_div;
}