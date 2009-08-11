// Javascript implementation for Zeya client.

// Representation of library.
var library;
// Index (into library) of the currently playing song, or null if no song is
// playing.
var current_index;
// Audio object we'll use for playing songs.
var audio;
// Current application state ('grayed', 'play', 'pause')
var current_state = 'grayed';

// Clear all the children of c.
function clearChildren(c) {
    while (c.childNodes.length >= 1) {
        c.removeChild(c.firstChild);
    }
}

// Initialize the application.
function init() {
    current_index = null;
    library = null;
    audio = null;
    set_ui_state('grayed');
    load_collection();
}

function keypress_handler(e) {
    if(window.event) {
        keynum = e.keyCode; // IE
    } else if(e.which) {
        keynum = e.which; // Other browsers
    } else {
        return true;
    }
    if (String.fromCharCode(keynum) == ' ') {
        if (current_state == 'play') {
            pause();
        } else if (current_state == 'pause') {
            play();
        }
        return false;
    } else if (String.fromCharCode(keynum) == 'j') {
        next();
        return false;
    } else if (String.fromCharCode(keynum) == 'k') {
        previous();
        return false;
    }
    return true;
}

// Request the collection from the server and render a table to display it.
function load_collection() {
    var t = document.getElementById('collection_table');
    var req = new XMLHttpRequest();
    req.open('GET', '/getlibrary', true);
    req.onreadystatechange = function(e) {
        if (req.readyState == 4 && req.status == 200) {
            library = JSON.parse(req.responseText);
            // Each item will have one row in the table.
            for (var index = 0; index < library.length; index++) {
                var item = library[index];

                link = document.createElement('a');
                link.setAttribute('href', '#');
                link.setAttribute('onclick', 'select_item(' + index + '); return false;');
                link.appendChild(document.createTextNode(item.title));

                tr = document.createElement('tr');
                td1 = document.createElement('td');
                td2 = document.createElement('td');
                td3 = document.createElement('td');
                td1.appendChild(link);
                td2.appendChild(document.createTextNode(item.artist));
                td3.appendChild(document.createTextNode(item.album));
                tr.appendChild(td1);
                tr.appendChild(td2);
                tr.appendChild(td3);
                t.appendChild(tr);
            }
            document.getElementById('loading').style.display = 'none';
        }
    }
    req.send(null);
}

// Skip to the next song.
function next() {
    if (current_index != null) {
        select_next();
    }
}

// Pause the currently playing song.
function pause() {
    if (current_index != null) {
        audio.pause();
        set_ui_state('pause');
    }
}

// Start or resume playing the current song.
function play() {
    if (current_index != null) {
        audio.play();
        set_ui_state('play');
    }
}

// Skip to the beginning of the current song, or to the previous song.
function previous() {
    if (current_index != null) {
        if (audio.currentTime > 5.00) {
            audio.currentTime = 0.0;
        } else {
            select_previous();
        }
    }
}

// Load the song with the given index.
function select_item(index) {
    // Pause the currently playing song.
    if (audio != null) {
        audio.pause();
        set_ui_state('pause');
    }
    // Start streaming the new song.
    entry = library[index];
    audio = new Audio('/getcontent?' + escape(entry.key));
    audio.setAttribute('autoplay', 'true');
    current_index = index;
    // When this song is finished, advance to the next one.
    if (index < library.length - 1) {
        audio.addEventListener('ended', select_next, false);
    }
    audio.load();
    // Update the UI.
    clearChildren(document.getElementById('title_text'));
    clearChildren(document.getElementById('artist_text'));
    document.getElementById('title_text').appendChild(document.createTextNode(entry.title));
    document.getElementById('artist_text').appendChild(document.createTextNode(entry.artist));
    document.title = entry.title + ' (' + entry.artist + ') - Zeya';
    set_ui_state('play');
}

// Load the next song in the list (with wraparound).
function select_next() {
    if (current_index == library.length - 1) {
        select_item(0);
    } else {
        select_item(current_index + 1);
    }
}

// Load the previous song in the list (with wraparound).
function select_previous() {
    if (current_index == 0) {
        select_item(library.length - 1);
    } else {
        select_item(current_index - 1);
    }
}

// Set the state of the UI.
function set_ui_state(new_state) {
    if (new_state == 'grayed') {
        // All buttons grayed.
        document.getElementById("previous_img").className = 'grayed';
        document.getElementById("play_img").className = 'grayed';
        document.getElementById("pause_img").className = 'grayed';
        document.getElementById("next_img").className = 'grayed';
    } else if (new_state == 'play') {
        // 'Play' depressed
        document.getElementById("previous_img").className = '';
        document.getElementById("play_img").className = 'activated';
        document.getElementById("pause_img").className = '';
        document.getElementById("next_img").className = '';
    } else {
        // 'Pause' depressed
        document.getElementById("previous_img").className = '';
        document.getElementById("pause_img").className = 'activated';
        document.getElementById("play_img").className = '';
        document.getElementById("previous_img").className = '';
    }
    current_state = new_state;
}
