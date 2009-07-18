var current_index;
var library;
var audio;

function clearChildren(c) {
    while (c.childNodes.length >= 1) {
        c.removeChild(c.firstChild);
    }
}

function init() {
    current_index = null;
    library = null;
    audio = null;
    set_ui_state('grayed');
    load_collection();
}

function load_collection() {
    var c = document.getElementById('collection');
    var req = new XMLHttpRequest();
    req.open('GET', '/getlibrary', true);
    req.onreadystatechange = function(e) {
        if (req.readyState == 4 && req.status == 200) {
            library = JSON.parse(req.responseText);
            for (var index = 0; index < library.length; index++) {
                var item = library[index];
                link = document.createElement("a")
                link.setAttribute('href', '#');
                link.setAttribute('onclick', 'select_item(' + index + '); return false;');
                link.appendChild(document.createTextNode(item.title));
                c.appendChild(link);
                c.appendChild(document.createTextNode(" " + item.artist));
                c.appendChild(document.createElement('br'));
            }
            document.getElementById('loading').style.display = 'none';
        }
    }
    req.send(null);
}

function pause() {
    if (current_index != null) {
        audio.pause();
        set_ui_state('pause');
    }
}

function play() {
    if (current_index != null) {
        audio.play();
        set_ui_state('play');
    }
}

function select_item(index) {
    current_index = index;
    if (audio != null) {
        audio.pause();
        set_ui_state('pause');
    }
    entry = library[index];
    audio = new Audio('/getcontent?' + escape(entry.location));
    audio.setAttribute('autoplay', 'true');
    if (current_index < library.length - 1) {
        audio.addEventListener('ended',
                               select_item_fn(current_index + 1),
                               false);
    }
    audio.load();
    clearChildren(document.getElementById('title_text'));
    clearChildren(document.getElementById('artist_text'));
    document.getElementById('title_text').appendChild(document.createTextNode(entry.title));
    document.getElementById('artist_text').appendChild(document.createTextNode(entry.artist));
    document.title = entry.title + ' (' + entry.artist + ') - Zeya';
    set_ui_state('play');
}

function select_item_fn(index) {
    var current_index = index;
    return function() {
        select_item(current_index);
    }
}

function set_ui_state(new_state) {
    if (new_state == 'grayed') {
        document.getElementById("play_img").className = 'grayed';
        document.getElementById("pause_img").className = 'grayed';
    } else if (new_state == 'play') {
        document.getElementById("play_img").className = 'activated';
        document.getElementById("pause_img").className = '';
    } else {
        document.getElementById("pause_img").className = 'activated';
        document.getElementById("play_img").className = '';
    }
}
