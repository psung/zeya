// Javascript implementation for Zeya client.

// Representation of library.
var library;
// Index (into library) of the currently playing song, or null if no song is
// playing.
var current_index = null;
// Audio object we'll use for playing songs.
var audio;
// Current application state ('grayed', 'play', 'pause')
var current_state = 'grayed';

// We need to buffer streams for Chrome.
var using_webkit = navigator.userAgent.indexOf("AppleWebKit") > -1;

// Clear all the children of c.
function clearChildren(c) {
  while (c.childNodes.length >= 1) {
    c.removeChild(c.firstChild);
  }
}

// Request the collection from the server and render a table to display it.
function load_collection() {
  var t = document.createElement('table');

  t.id = "collection_table";
  var t_head = document.createElement("thead");
  var header_td1 = document.createElement("td");
  header_td1.style.width = "42%";
  header_td1.appendChild(document.createTextNode("Title"));
  var header_td2 = document.createElement("td");
  header_td2.style.width = "29%";
  header_td2.appendChild(document.createTextNode("Artist"));
  var header_td3 = document.createElement("td");
  header_td3.style.width = "29%";
  header_td3.appendChild(document.createTextNode("Album"));
  t_head.appendChild(header_td1);
  t_head.appendChild(header_td2);
  t_head.appendChild(header_td3);
  t.appendChild(t_head);

  var req = new XMLHttpRequest();
  req.open('GET', '/getlibrary', true);
  req.onreadystatechange = function(e) {
    if (req.readyState == 4 && req.status == 200) {
      library = JSON.parse(req.responseText);
      // Each item will have one row in the table.
      for (var index = 0; index < library.length; index++) {
        var item = library[index];

        var link = document.createElement('a');
        link.setAttribute('href', '#');
        link.setAttribute('onclick', 'select_item(' + index + '); return false;');
        link.appendChild(document.createTextNode(item.title));

        var tr = document.createElement('tr');
        tr.id = 'row' + index;
        tr.setAttribute('class', index % 2 == 0 ? 'evenrow' : 'oddrow');
        var td1 = document.createElement('td');
        var td2 = document.createElement('td');
        var td3 = document.createElement('td');
        td1.appendChild(link);
        td2.appendChild(document.createTextNode(item.artist));
        td3.appendChild(document.createTextNode(item.album));
        tr.appendChild(td1);
        tr.appendChild(td2);
        tr.appendChild(td3);
        t.appendChild(tr);
      }
      document.getElementById('collection').appendChild(t);
      document.getElementById('collection').style.display = 'block';
      document.getElementById('loading').style.display = 'none';
    }
  };

  req.send(null);
}

// Pause the currently playing song.
function pause() {
  if (current_index !== null) {
    audio.pause();
    set_ui_state('pause');
  }
}

// Start or resume playing the current song.
function play() {
  if (current_index !== null) {
    audio.play();
    set_ui_state('play');
  }
}

// Hide or show the spinner.
function set_spinner_visible(visible) {
  document.getElementById("spinner_icon").style.visibility =
    visible ? "visible" : "hidden";
}

// Sets the title/artist fields that are displayed in the header, and the page
// title.
function set_title(title, artist) {
  clearChildren(document.getElementById('title_text'));
  clearChildren(document.getElementById('artist_text'));
  if (title != '') {
    document.getElementById('title_text').appendChild(document.createTextNode(title));
  }
  if (artist != '') {
    document.getElementById('artist_text').appendChild(document.createTextNode(artist));
  }
  if (title == '' && artist == '') {
    document.title = 'Zeya';
  } else {
    document.title = title + ' (' + artist + ') - Zeya';
  }
}

// Load the song with the given index.
function select_item(index) {
  // Pause the currently playing song.
  if (audio !== null) {
    audio.pause();
    set_ui_state('pause');
  }
  // Update the UI.
  set_spinner_visible(true);
  if (current_index !== null) {
    document.getElementById('row' + current_index).className =
      current_index % 2 == 0 ? 'evenrow' : 'oddrow';
  }
  document.getElementById('row' + index).className = 'selectedrow';
  // Start streaming the new song.
  var entry = library[index];
  // Get a buffered stream of the desired file.
  var bufferParam = using_webkit ? 'buffered=true&' : '';
  audio = new Audio('/getcontent?' + bufferParam + 'key=' + escape(entry.key));
  audio.setAttribute('autoplay', 'true');
  current_index = index;
  // Hide the spinner when the song has loaded.
  audio.addEventListener(
    'play', function() {set_spinner_visible(false);}, false);
  if (index == library.length - 1) {
    // When this song is finished, stop playing (if this was the last song
    // in the list).
    audio.addEventListener('ended', stop, false);
  } else {
    // Otherwise, advance to the next song.
    audio.addEventListener('ended', select_next, false);
  }
  audio.load();
  // Update the UI.
  set_title(entry.title, entry.artist);
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
  if (current_index === 0) {
    select_item(library.length - 1);
  } else {
    select_item(current_index - 1);
  }
}

// Skip to the next song.
function next() {
  if (current_index !== null) {
    select_next();
  }
}

// Skip to the beginning of the current song, or to the previous song.
function previous() {
  if (current_index !== null) {
    if (audio.currentTime > 5.00) {
      audio.currentTime = 0.0;
    } else {
      select_previous();
    }
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

// Stop playback.
function stop() {
  audio.pause();
  set_ui_state('grayed');
  set_title('', '');
}

// EVENT HANDLERS

// Initialize the application.
function init() {
  current_index = null;
  library = null;
  audio = null;
  set_ui_state('grayed');
  load_collection();
}

function keypress_handler(e) {
  var keynum;
  if(window.event) {
    keynum = e.keyCode; // IE
  } else if(e.which) {
    keynum = e.which; // Other browsers
  } else {
    return true;
  }
  if (String.fromCharCode(keynum) === ' ') {
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
