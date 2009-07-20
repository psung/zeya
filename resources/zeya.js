// Javascript implementation for Zeya client.

// Representation of library.
var library;
// Index (into library) of the currently playing song, or null if no song is
// playing.
var current_index;
// Audio object we'll use for playing songs.
var audio;

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
        audio.addEventListener('ended', select_item_fn(index + 1), false);
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

// Wrapper around select_item.
function select_item_fn(index) {
    var current_index = index;
    return function() {
        select_item(current_index);
    }
}

// Set the state of the UI.
function set_ui_state(new_state) {
    if (new_state == 'grayed') {
        // Both buttons grayed.
        document.getElementById("play_img").className = 'grayed';
        document.getElementById("pause_img").className = 'grayed';
    } else if (new_state == 'play') {
        // 'Play' depressed
        document.getElementById("play_img").className = 'activated';
        document.getElementById("pause_img").className = '';
    } else {
        // 'Pause' depressed
        document.getElementById("pause_img").className = 'activated';
        document.getElementById("play_img").className = '';
    }
}
