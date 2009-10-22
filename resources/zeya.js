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

// We need to buffer streams for Chrome.
var using_webkit = navigator.userAgent.indexOf("AppleWebKit") > -1;

// Clear all the children of c.
function clearChildren(c) {
  while (c.childNodes.length >= 1) {
    c.removeChild(c.firstChild);
  }
}

// Return the DOM id of the row (TR element) corresponding to the specified
// index.
function getRowIdFromIndex(index) {
  return 'row' + index;
}

// Return the library index corresponding to a given row id.
function getIndexFromRowId(id) {
  return id.substring(3);
}

// Return the class to use for the row corresponding to the given index. This
// determines the color of the row.
function getRowClassFromIndex(index) {
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
function load_collection()
{
  var req = new XMLHttpRequest();
  req.open('GET', '/getlibrary', true);
  req.onreadystatechange = function(e) {
    if (req.readyState == 4 && req.status == 200) {
      library = JSON.parse(req.responseText);
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
    tr.id = getRowIdFromIndex(index);
    if (current_index == index) {
      tr.className = 'selectedrow';
    } else {
      tr.className = getRowClassFromIndex(current_line);
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
}

// Clear displayed collection.
function clear_collection() {
  clearChildren(document.getElementById('collection'));
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
    current_row = document.getElementById(getRowIdFromIndex(current_index));
    if (current_row) {
      current_row.className =
        getRowClassFromIndex(get_line_number(current_row));
    }
  }
  document.getElementById(getRowIdFromIndex(index)).className = 'selectedrow';
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
  var index_row = document.getElementById(getRowIdFromIndex(index));
  return index_row == collection.lastChild
}

// Load the next song in the list (with wraparound).
function select_next() {
  var collection = document.getElementById('collection_table');
  var current_row = document.getElementById(getRowIdFromIndex(current_index));

  if (!current_row) {
    // Display changed since we began playing and the displayed
    // collection is empty.
    return;
  }

  // If on the last row, go back to the first.
  if (current_row == collection.lastChild) {
    // The table's firstChild is the heading.
    select_item(getIndexFromRowId(collection.firstChild.nextSibling.id));
  } else {
    var next_row = current_row.nextSibling;
    if (next_row) {
      select_item(getIndexFromRowId(next_row.id));
    }
  }
}

// Load the previous song in the list (with wraparound).
function select_previous() {
  var collection = document.getElementById('collection_table');
  var current_row = document.getElementById(getRowIdFromIndex(current_index));

  if (!current_row) {
    // Display changed since we began playing and the displayed
    // collection is empty.
    return;
  }

  // If on the first row, go to the last.
  if (current_row == collection.firstChild.nextSibling) {
    select_item(getIndexFromRowId(collection.lastChild.id));
  } else {
    var previous_row = current_row.previousSibling;
    if (previous_row) {
      select_item(getIndexFromRowId(previous_row.id));
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
  }
  return true;
}
