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
// Value of the search box, or null if no search has been performed
var search_string = null;
// Information to display in the status area.
var status_info = {
  total_tracks: 0,
  displayed_tracks: 0,
};

// We need to buffer streams for Chrome.
var using_webkit = navigator.userAgent.indexOf("AppleWebKit") > -1;

// Return true if the client supports the <audio> tag.
function can_play_native_audio() {
  if (!document.createElement('audio').canPlayType) {
    return false;
  }
  // Supported browsers will return 'probably' or 'maybe' here
  var can_play = document.createElement('audio').canPlayType(
    'audio/ogg; codecs="vorbis"');
  return can_play != '';
}

// Clear all the children of c.
function clear_children(c) {
  while (c.childNodes.length >= 1) {
    c.removeChild(c.firstChild);
  }
}

// Return the DOM id of the row (TR element) corresponding to the specified
// index.
function get_row_id_from_index(index) {
  return 'row' + index;
}

// Return the library index corresponding to a given row id.
function get_index_from_row_id(id) {
  return id.substring(3);
}

// Return the class to use for the row corresponding to the given index. This
// determines the color of the row.
function get_row_class_from_index(index) {
  return index % 2 == 0 ? 'evenrow' : 'oddrow';
}

function item_match(item, match_string) {
  var s = match_string.toLowerCase();
  if (item.title.toLowerCase().indexOf(s) == -1
      && item.artist.toLowerCase().indexOf(s) == -1
      && item.album.toLowerCase().indexOf(s) == -1) {
      return false;
  }
  return true;
}

// Request the collection from the server then render it.
function load_collection() {
  var req = new XMLHttpRequest();
  req.open('GET', '/getlibrary', true);
  req.onreadystatechange = function(e) {
    if (req.readyState == 4 && req.status == 200) {
      library = JSON.parse(req.responseText);
      status_info.total_tracks = library.length;
      render_collection();
    }
  };
  req.send(null);
}

// Render a table to display it the collection.
function render_collection() {
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

  // Each item will have one row in the table.
  for (var index = 0, current_line = 0; index < library.length; index++) {
    var item = library[index];

    if (search_string !== null) {
      if (!item_match(item, search_string)) {
        continue;
      }
    }

    current_line++;
    var link = document.createElement('a');
    link.setAttribute('href', '#');
    link.setAttribute('onclick', 'select_item(' + index + '); return false;');
    link.appendChild(document.createTextNode(item.title));

    var tr = document.createElement('tr');
    tr.id = get_row_id_from_index(index);
    if (current_index == index) {
      tr.className = 'selectedrow';
    } else {
      tr.className = get_row_class_from_index(current_line);
    }
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

  status_info.displayed_tracks = current_line;
  update_status_area();
}

// Clear displayed collection.
function clear_collection() {
  clear_children(document.getElementById('collection'));
  document.getElementById('collection').style.display = 'none';
  document.getElementById('loading').style.display = 'block';
}

// Update current search string and reload collection.
function search() {
  var search_box = document.getElementById('search_box');
  search_string = search_box.value;
  search_box.blur();
  // Redisplay collection, filtering on the search string.
  clear_collection();
  // The setTimeout trick is to force the browser to display the loading
  // message before rendering the collection.
  window.setTimeout("render_collection()", 1);
  // Return false to prevent an actual form submit.
  return false;
}

function focus_search_box() {
  var search_box = document.getElementById('search_box');
  search_box.focus();
  // Select the text (if any)
  search_box.select();
}

// Pause the currently playing song.
function pause() {
  if (current_index !== null) {
    set_spinner_visible(false);
    audio.pause();
    set_ui_state('pause');
  }
}

// Start or resume playing the current song.
function play() {
  if (current_index !== null) {
    set_spinner_visible(true);
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
  clear_children(document.getElementById('title_text'));
  clear_children(document.getElementById('artist_text'));
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

function plural(number) {
  return number > 1 ? 's' : '';
}

function update_status_area() {
  var status_area = document.getElementById('status_area');
  var status_text = status_info.displayed_tracks + ' track'
       + plural(status_info.displayed_tracks);

  if (status_info.displayed_tracks < status_info.total_tracks) {
    status_text += ' (' + status_info.total_tracks + ' total)';
  }

  clear_children(status_area);
  status_area.appendChild(document.createTextNode(status_text));
}

// Return the line number corresponding to this row.
// Note that this is not the same as the index if a search filter has
// been applied.
function get_line_number(element) {
  var collection = document.getElementById('collection_table');
  var ret = 0;
  var e = collection.firstChild;
  while (e != element) {
    e = e.nextSibling;
    ret++;
  }
  return ret;
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
    current_row = document.getElementById(get_row_id_from_index(current_index));
    if (current_row) {
      current_row.className =
        get_row_class_from_index(get_line_number(current_row));
    }
  }
  document.getElementById(get_row_id_from_index(index)).className = 'selectedrow';
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
  if (is_last_track(index)) {
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

// Check if the song with the given index is the last in the list.
function is_last_track(index) {
  var collection = document.getElementById('collection_table');
  var index_row = document.getElementById(get_row_id_from_index(index));
  return index_row == collection.lastChild
}

// Load the next song in the list (with wraparound).
function select_next() {
  var collection = document.getElementById('collection_table');
  var current_row = document.getElementById(get_row_id_from_index(current_index));

  if (!current_row) {
    // Display changed since we began playing and the displayed
    // collection is empty.
    return;
  }

  // If on the last row, go back to the first.
  if (current_row == collection.lastChild) {
    // The table's firstChild is the heading.
    select_item(get_index_from_row_id(collection.firstChild.nextSibling.id));
  } else {
    var next_row = current_row.nextSibling;
    if (next_row) {
      select_item(get_index_from_row_id(next_row.id));
    }
  }
}

// Load the previous song in the list (with wraparound).
function select_previous() {
  var collection = document.getElementById('collection_table');
  var current_row = document.getElementById(get_row_id_from_index(current_index));

  if (!current_row) {
    // Display changed since we began playing and the displayed
    // collection is empty.
    return;
  }

  // If on the first row, go to the last.
  if (current_row == collection.firstChild.nextSibling) {
    select_item(get_index_from_row_id(collection.lastChild.id));
  } else {
    var previous_row = current_row.previousSibling;
    if (previous_row) {
      select_item(get_index_from_row_id(previous_row.id));
    }
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

function show_help() {
  document.getElementById('helpcontainer').style.display = 'block';
}

function hide_help() {
  document.getElementById('helpcontainer').style.display = 'none';
}

// EVENT HANDLERS

// Initialize the application.
function init() {
  current_index = null;
  library = null;
  audio = null;
  set_ui_state('grayed');
  // If the client doesn't support HTML5 audio, just disable everything and
  // display an error.
  if (!can_play_native_audio()) {
    window.document.getElementById('loading').style.display = 'none';
    window.document.getElementById('unsupported').style.display = 'block';
    window.document.getElementById('search_box').disabled = true;
    return;
  }
  // The browser may have filled in the search box with the user's previously
  // entered value. Load that into search_string here so that the search filter
  // is applied to the collection when it's first displayed to the user again.
  search_string = window.document.getElementById('search_box').value;
  load_collection();
}

// Clean up after ourselves when the page is unloaded.
function cleanup() {
  // Firefox seems to maintain a huge audio buffer and playback doesn't always
  // stop immediately when the page is closed or refreshed. So pause the stream
  // manually here.
  if (audio !== null) {
    audio.pause();
  }
}

function keydown_handler(e) {
  var keynum;
  if (e.which) {
    keynum = e.which;
  } else {
    return true;
  }

  if (keynum == 27) { // ESC
    // Blur the search box.
    if (window.document.activeElement
        == window.document.getElementById('search_box')) {
      window.document.getElementById('search_box').blur();
    } else {
      hide_help();
    }
    return false;
  } else {
    return true;
  }
}

function keypress_handler(e) {
  var keynum;
  if(e.which) {
    keynum = e.which;
  } else {
    return true;
  }

  // If editing the search box, don't intercept keypresses.
  // Note, document.activeElement is an HTML5 feature.
  if (window.document.activeElement
      == window.document.getElementById('search_box')) {
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
  } else if (String.fromCharCode(keynum) == '/') {
    focus_search_box();
    return false;
  } else if (String.fromCharCode(keynum) == '?') {
    show_help();
    return false;
  }
  return true;
}
