// Javascript implementation for Zeya client.

// Map from song key to library item. Each library item is an object with
// attributes .title, .artist, .album, and .key.
var library;
// Representation of the set of available playlists. Maps a playlist ID to a
// list of song keys representing that playlist.
var playlist_map = {};
// The sequence of songs displayed in the playlist (after selection of
// playlist, filtering and shuffling). This is represented as a list of song
// keys (which are also keys into library).
var displayed_content;
// Index (into displayed_content) of the currently playing song, or null if no
// song is playing.
var current_index = null;
// Audio object we'll use for playing songs.
var current_audio;
var preload_audio;
var preload_key; // `key' attribute of the song we've preloaded.
var preload_finished = false;
// Current application state ('grayed', 'play', 'pause')
var current_state = 'grayed';
// Playlist ID of the selected playlist.
var current_playlist;
// Value of the search box, or null if no search has been performed
var search_string = null;
// Whether or not the repeat feature is activated.
var is_repeating = false;
// Whether or not the shuffle feature is activated.
var is_shuffled = false;
// Information to display in the status area.
var status_info = {
  total_tracks: 0,
  displayed_tracks: 0,
};

// We need to buffer streams for Chrome.
var using_webkit = navigator.userAgent.indexOf("AppleWebKit") > -1;
// Firefox 3.5 doesn't issue the 'suspend' event, so we need to use a fallback
// implementation.
var using_gecko_1_9_1 = navigator.userAgent.indexOf("Gecko/") > -1
  && navigator.userAgent.indexOf("rv:1.9.1.") > -1;

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
  return index % 2 === 0 ? 'evenrow' : 'oddrow';
}

// Hide or show the spinner.
function set_spinner_visible(visible) {
  document.getElementById("spinner_icon").style.visibility =
    visible ? "visible" : "hidden";
}

// Check if the song with the given index is the last in the list.
function is_last_track(index) {
  var collection = document.getElementById('collection_table');
  var index_row = document.getElementById(get_row_id_from_index(index));
  return index_row == collection.lastChild;
}

function plural(number) {
  return number > 1 ? 's' : '';
}

// Returns an Audio object corresponding to the track with the given key.
function get_stream(key) {
  var buffer_param = using_webkit ? 'buffered=true&' : '';
  return new Audio('getcontent?' + buffer_param + 'key=' + escape(key));
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

// Return true if the item matches the given query string.
function item_match(item, match_string) {
  var s = match_string.toLowerCase();
  if (s.match('^artist:')) {
    return item.artist.toLowerCase().indexOf(s.substring(7)) != -1;
  } else if (s.match('^title:')) {
    return item.title.toLowerCase().indexOf(s.substring(6)) != -1;
  } else if (s.match('^album:')) {
    return item.album.toLowerCase().indexOf(s.substring(6)) != -1;
  } else {
    return !(item.title.toLowerCase().indexOf(s) == -1
             && item.artist.toLowerCase().indexOf(s) == -1
             && item.album.toLowerCase().indexOf(s) == -1);
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
    document.getElementById("next_img").className = '';
  }
  current_state = new_state;
}

// Evaluates the search query and shuffle mode (if selected) and set
// `displayed_content' appropriately to reflect the new display. Also update
// `current_index' so that it continues to point to the same song, if possible.
function compute_displayed_content(current_playlist, search_query, shuffle) {
  var content = [];

  // Extract the key corresponding to the current song so we can identify it
  // again later. The key is invariant, unlike current_index.
  var currently_playing_song_key = null;
  if (current_index !== null) {
    currently_playing_song_key = library[displayed_content[current_index]].key;
  }
  current_index = null;

  // Apply the search filter.
  for (var index = 0; index < current_playlist.length; index++) {
    var key = current_playlist[index];
    var item = library[key];
    if (search_query !== null) {
      if (!item_match(item, search_query)) {
        continue;
      }
    }
    content.push(key);
  }

  // Peform the library shuffle via Durstenfeld's shuffle.
  if (shuffle) {
    for (var temp, j, i = content.length; i > 0;) {
      j = parseInt(Math.random() * i);
      temp = content[--i];
      content[i] = content[j];
      content[j] = temp;
    }
  }

  // Fix current_index so it points to the currently playing song in the
  // new collection.
  for (var i = 0; i < content.length; i++) {
    var item = library[content[i]];
    if (item.key == currently_playing_song_key) {
      current_index = i;
    }
  }

  displayed_content = content;
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
  for (var index = 0; index < displayed_content.length; index++) {
    var item = library[displayed_content[index]];

    var link = document.createElement('a');
    link.setAttribute('href', '#');
    link.setAttribute('onclick', 'select_item(' + index + ', true); return false;');
    link.appendChild(document.createTextNode(item.title));

    var tr = document.createElement('tr');
    tr.id = get_row_id_from_index(index);
    if (current_index == index) {
      tr.className = 'selectedrow';
    } else {
      tr.className = get_row_class_from_index(index);
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

  // Ensure that the selected song is visible in the window.
  if (current_index !== null) {
    // If possible, show some songs before the selected song, so that it
    // doesn't appear at the top of the window.
    var top_displayed_index = Math.max(0, current_index - 3);
    document.getElementById(
      get_row_id_from_index(top_displayed_index)).scrollIntoView();
  }

  status_info.displayed_tracks = index;
  update_status_area();
}

// Request the collection from the server then render it.
function load_collection() {
  var req = new XMLHttpRequest();
  req.open('GET', 'getlibrary', true);
  req.onreadystatechange = function(e) {
    if (req.readyState == 4 && req.status == 200) {
      server_response = JSON.parse(req.responseText);
      var library_obj = server_response.library;
      status_info.total_tracks = library_obj.length;
      init_playlist_map(library_obj, server_response.playlists);
      compute_displayed_content(current_playlist, search_string, is_shuffled);
      render_collection();
    }
  };
  req.send(null);
}

// Initialize the playlist_map object, where 'library' and 'playlists' are the
// deserialized collection objects returned by the server.
function init_playlist_map(library_obj, playlists) {
  // Create the default playlist, which corresponds to the entire collection.
  default_playlist = [];
  for (var i = 0; i < library_obj.length; i++) {
    library[library_obj[i].key] = library_obj[i];
    default_playlist.push(library_obj[i].key);
  }
  playlist_map['all'] = default_playlist;

  // Show the playlist selector if the backend supports it.
  if (playlists !== null) {
    corpus_selector = document.getElementById("corpus-selector");

    new_playlist_item = document.createElement("option");
    new_playlist_item.value = "all";
    new_playlist_item.appendChild(document.createTextNode("All music"));
    corpus_selector.appendChild(new_playlist_item);

    for (var i = 0; i < playlists.length; i++) {
      var playlist_id = "playlist:" + i;
      new_playlist_item = document.createElement("option");
      new_playlist_item.value = playlist_id;
      new_playlist_item.appendChild(document.createTextNode(playlists[i].name));
      corpus_selector.appendChild(new_playlist_item);
      playlist_map[playlist_id] = playlists[i].items;
    }
    corpus_selector.style.display = "block";

    // TODO: add some placeholder items when there are no playlists. (e.g.
    // simply a disabled item labeled "(No playlists)")
  }

  // Attempt to load the previously selected playlist (the browser may persist
  // the value within shadow-corpus-selector across page reloads.
  old_playlist_id = window.document.getElementById('shadow-corpus-selector').value;
  if (playlist_map[old_playlist_id] === undefined) {
    old_playlist_id = 'all';
  } else {
    document.getElementById('corpus-selector').value = old_playlist_id;
  }
  current_playlist = playlist_map[old_playlist_id];
}

// Clear displayed collection.
function clear_collection() {
  clear_children(document.getElementById('collection'));
  document.getElementById('collection').style.display = 'none';
  document.getElementById('loading').style.display = 'block';
}

// Update the collection when the playlist is updated.
function update_playlist() {
  corpus_id = document.getElementById('corpus-selector').value;
  window.document.getElementById('shadow-corpus-selector').value = corpus_id;
  current_playlist = playlist_map[corpus_id];
  clear_collection();
  compute_displayed_content(current_playlist, search_string, is_shuffled);
  render_collection();
}

// Update current search string and reload collection.
function search() {
  var search_box = document.getElementById('search_box');
  search_string = search_box.value;
  search_box.blur();
  window.document.getElementById('content').focus();
  // Redisplay collection, filtering on the search string.
  clear_collection();
  // The setTimeout trick is to force the browser to display the loading
  // message before rendering the collection.
  compute_displayed_content(current_playlist, search_string, is_shuffled);
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

function clear_search() {
  document.getElementById('search_box').value = '';
  search();
}

// Toggle the 'repeat' mechanism.
function repeat() {
  is_repeating = !is_repeating;
  if (is_repeating) {
    document.getElementById("repeat_img").className = 'activated';
  } else {
    document.getElementById("repeat_img").className = '';
  }
}

// Toggle the 'shuffled' state of the playlist.
function shuffle() {
  clear_collection();
  is_shuffled = !is_shuffled;
  if (is_shuffled) {
    document.getElementById("shuffle_img").className = 'activated';
  } else {
    document.getElementById("shuffle_img").className = '';
  }
  compute_displayed_content(current_playlist, search_string, is_shuffled);
  window.setTimeout("render_collection()", 1);
}

// Pause the currently playing song.
function pause() {
  if (current_index !== null) {
    set_spinner_visible(false);
    current_audio.pause();
    set_ui_state('pause');
  }
}

// Start or resume playing the current song.
function play() {
  if (current_index !== null) {
    set_spinner_visible(true);
    current_audio.play();
    set_ui_state('play');
  }
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

// Return the index of the next song, with wraparound.
function next_index() {
  if (current_index === null) {
    // Display changed since we began playing.
    if (displayed_content.length > 0) {
      return 0;
    } else {
      return null;
    }
  }

  // If on the last row, go back to the first.
  if (current_index == displayed_content.length - 1) {
    return 0;
  } else {
    return current_index + 1;
  }
}

// Return the index of the next song, with wraparound.
function previous_index() {
  if (current_index === null) {
    // Display changed since we began playing.
    if (displayed_content.length > 0) {
      return 0;
    } else {
      return null;
    }
  }

  // If on the last row, go back to the first.
  if (current_index == 0) {
    return displayed_content.length - 1;
  } else {
    return current_index - 1;
  }
}

// Invokes callback after audio_elt has finished loading.
function add_load_finished_listener(audio_elt, callback) {
  // Firefox 3.6 (Gecko 1.9.2) and Chrome 4 support the 'suspend' event, which
  // makes this trivial.
  if (!using_gecko_1_9_1) {
    audio_elt.addEventListener('suspend', callback, false);
  } else {
    // This is a fallback implementation for Gecko 1.9.1. Just keep polling the
    // audio's networkState attribute periodically to determine when it's
    // finished loading.
    timer_callback = function() {
      if (audio_elt.networkState != 2) { // NETWORK_LOADING
        callback();
      } else {
        add_load_finished_listener(audio_elt, callback);
      }
    };
    setTimeout(timer_callback, 2000);
  }
}

// Start loading the next song in the list, but don't play it.
function preload_song() {
  // Disable preloading for Gecko 1.9.1. It doesn't seem to deal correctly with
  // preloading streams and then asking to start playing them at some later
  // time. Instead, all songs are loaded on demand.
  if (using_gecko_1_9_1) {
    // It's fine to return early here, because this just means preload_key
    // never gets set. When the next song is supposed to start, a real request
    // will get issued, as if there were no preloading mechanism.
    return;
  }

  preload_key = library[displayed_content[next_index()]].key;

  if (preload_key !== null) {
    preload_finished = false;
    preload_audio = get_stream(preload_key);
    add_load_finished_listener(preload_audio, function() { preload_finished = true; });
    preload_audio.load();
  }
}

// Select the song with the given index. If play_track is true, then the song
// will be loaded for playing too. (If play_track is false, the song is not
// loaded and the UI is set to a "pause" state.)
function select_item(index, play_track) {
  // Stop playing the current song.
  if (current_audio !== null) {
    current_audio.pause();
    set_ui_state('pause');
  }
  // Show the spinner if applicable.
  if (play_track) {
    set_spinner_visible(true);
  }
  // Highlight the selected row.
  if (current_index !== null) {
    var current_row = document.getElementById(get_row_id_from_index(current_index));
    if (current_row) {
      current_row.className = get_row_class_from_index(current_index);
    }
  }
  document.getElementById(get_row_id_from_index(index)).className = 'selectedrow';
  var entry = library[displayed_content[index]];
  var preloaded = entry.key == preload_key;
  if (preloaded) {
    current_audio = preload_audio;
  } else {
    current_audio = get_stream(entry.key);
  }
  if (play_track) {
    // Chrome doesn't seem to play the media if we set autoplay=true after the
    // media has finished loading. So we have to check for that case and play
    // manually ourselves.
    if (current_audio.readyState >= 3) { // HAVE_FUTURE_DATA or HAVE_ENOUGH_DATA
      current_audio.play();
    } else {
      current_audio.setAttribute('autoplay', 'true');
    }
  }
  current_index = index;
  // Hide the spinner when the song has loaded.
  current_audio.addEventListener(
    'play', function() {set_spinner_visible(false);}, false);
  // Update the time/progress element.
  current_audio.addEventListener(
    'timeupdate', function() {update_time();}, false);
  // If the song we're about to play has already finished, loading, kick off
  // the next preload. Otherwise, start it when the current song has finished
  // loading.
  if (preload_finished) {
    preload_song();
  } else {
    add_load_finished_listener(current_audio, preload_song);
  }
  // When this song is finished, advance to the next song (or stop playing if
  // this was the last song in the list).
  current_audio.addEventListener('ended', maybe_advance_to_next_song, false);
  if (!preloaded) {
    current_audio.load();
  }
  // Update the metadata in the UI.
  set_title(entry.title, entry.artist);
  // Set the state of the play controls.
  if (play_track) {
    set_ui_state('play');
  } else {
    set_ui_state('pause');
  }
}

// Load the next song in the list (with wraparound).
function select_next() {
  next_song_index = next_index();
  if (next_song_index !== null) {
    select_item(next_song_index, true);
  }
}

// Wait for a short interval if we're using Chrome, then select the next song.
function maybe_wait_and_select_next() {
  if (using_webkit) {
    // Chrome seems to fire the 'ended' event early. Wait for a short time so
    // the next song doesn't get started early. This is kind of hacky, as I
    // have no idea what the exact amount of the offset is, nor its true cause.
    setTimeout(select_next, 700);
  } else {
    select_next();
  }
}

// Advance to the next song, or stop if we're at the last song (unless repeat
// mode is active.).
function maybe_advance_to_next_song() {
  if (!is_repeating && (current_index === null || is_last_track(current_index))) {
    stop();
  } else {
    maybe_wait_and_select_next();
  }
}

// Load the previous song in the list (with wraparound).
function select_previous() {
  previous_song_index = previous_index();
  if (previous_song_index !== null) {
    select_item(previous_song_index, true);
  }
}

// Skip to the next song.
function next() {
  if (current_state != 'grayed') {
    select_next();
  }
}

// Skip to the beginning of the current song, or to the previous song.
function previous() {
  if (current_state != 'grayed') {
    if (current_index !== null && current_audio.currentTime > 5.00) {
      current_audio.currentTime = 0.0;
    } else {
      select_previous();
    }
  }
}

// Stop playback.
function stop() {
  current_audio.pause();
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
  library = {};
  current_audio = null;
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
  // Focus the scrollable area so that PgUp and PgDn keypresses are interpreted
  // properly.
  window.document.getElementById('content').focus();
}

function update_time() {
  var current_time = current_audio.currentTime;
  var minute = Math.floor(current_time / 60);
  var second = Math.floor(current_time - minute * 60);
  if (second < 10) {
    second = '0' + second;
  }
  document.getElementById('time-text-field').innerHTML = minute + ":" + second;
}

// Clean up after ourselves when the page is unloaded.
function cleanup() {
  // Firefox seems to maintain a huge audio buffer and playback doesn't always
  // stop immediately when the page is closed or refreshed. So pause the stream
  // manually here.
  if (current_audio !== null) {
    current_audio.pause();
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
      window.document.getElementById('content').focus();
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
