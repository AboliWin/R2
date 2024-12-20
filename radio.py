import curses
import vlc
import sys
import threading
import time
import requests


APP_NAME = "9Craft Radio"
INSTRUCTIONS = 'Space or "P" for play/pause, UP & DOWN keys for volume, "Esc" to exit'
INITIAL_STATUS = "Waiting for channel selection..."
KEYS = list("1234567890qwertyuiop")


urls = []
is_playing = False
playing_now = -1
volume = ""
status = ""


instance = vlc.Instance("--quiet")
player = instance.media_player_new()


session = requests.Session()

def load_data():
    """Fetches the radio channel data from the API."""
    global urls
    try:
        response = session.get("https://radio.9craft.ir/v1/api/genre/all")
        response.raise_for_status()
        data = response.json()
        urls = data.get("data", [])
    except requests.RequestException as e:
        print(f"Error loading data: {e}")
        urls = []

def init_curses():
    """Initializes the curses window."""
    stdscr = curses.initscr()
    curses.start_color()
    curses.noecho()
    curses.cbreak()
    stdscr.keypad(True)

    
    try:
        colors = [44, 181, 223, 47, 45, 206, 195, 242, 171, 111]
        for i, color in enumerate(colors):
            curses.init_pair(i + 1, color, curses.COLOR_BLACK)
    except curses.error:
        
        for i, color in enumerate([curses.COLOR_CYAN, curses.COLOR_YELLOW, curses.COLOR_GREEN,
                                    curses.COLOR_RED, curses.COLOR_WHITE, curses.COLOR_MAGENTA]):
            curses.init_pair(i + 1, color, curses.COLOR_BLACK)

    return stdscr

def end_curses(stdscr):
    """Restores the terminal to its original state."""
    stdscr.keypad(False)
    curses.nocbreak()
    curses.echo()
    curses.endwin()

def update_display(stdscr, status, volume):
    """Updates the curses window display with the latest information."""
    try:
        stdscr.clear()
        stdscr.addstr(0, 0, f"{APP_NAME}\n\n", curses.color_pair(4) | curses.A_BOLD)
        stdscr.addstr(f"Status: {status}\n\n", curses.color_pair(9))

        if playing_now == -1:
            genre_name, music_title = "", ""
        else:
            genre_name = urls[playing_now]["server_name"]
            music_title = urls[playing_now]["title"]
            stdscr.addstr(f"Genre: {genre_name}\n", curses.color_pair(2))
            stdscr.addstr(f"Music: {music_title}\n", curses.color_pair(3))

        
        for i, url in enumerate(urls):
            server_name = url["server_name"]
            title = url["title"]
            color = curses.color_pair(4) if i == playing_now else curses.color_pair(1)
            stdscr.addstr(f"\n{KEYS[i]}. ", color)
            stdscr.addstr(f"{server_name}: ", curses.color_pair(5))
            stdscr.addstr(f"{title}", curses.color_pair(7))

        stdscr.addstr(f'\n\n{INSTRUCTIONS}\n', curses.color_pair(8) | curses.A_ITALIC)
        if volume:
            stdscr.addstr(f"\nVolume: {volume}%", curses.color_pair(6) | curses.A_ITALIC)

        stdscr.refresh()
    except curses.error:
        pass  

def handle_volume_change(change):
    """Handles volume change based on user input."""
    global volume
    current_volume = player.audio_get_volume()
    new_volume = max(0, min(100, current_volume + change))
    player.audio_set_volume(new_volume)
    volume = f"{new_volume}"
    return volume

def play_station(index):
    """Plays the selected station."""
    global playing_now, status, is_playing
    if index < len(urls):
        media = instance.media_new(urls[index]["http_server_url"])
        player.stop()
        player.set_media(media)
        player.play()
        playing_now = index
        is_playing = True
        status = "Playing..."
    else:
        status = "Invalid selection"

def toggle_play_pause():
    """Toggles the play/pause state of the player."""
    global is_playing, status
    if playing_now != -1:
        if is_playing:
            player.stop()
            status = "Paused"
        else:
            player.play()
            status = "Playing..."
        is_playing = not is_playing

def refresh_data():
    """Periodically refreshes the radio channel data."""
    while True:
        time.sleep(10)
        load_data()  

def start_refresh_thread():
    """Starts the background thread to refresh station data."""
    refresh_thread = threading.Thread(target=refresh_data)
    refresh_thread.daemon = True
    refresh_thread.start()

def main(stdscr):
    """Main function to handle user input and control the player."""
    global volume, status
    status = INITIAL_STATUS
    update_display(stdscr, status, volume)

    while True:
        key = stdscr.getch()
        if key == 27:  
            break
        elif key == curses.KEY_UP:
            volume = handle_volume_change(5)
        elif key == curses.KEY_DOWN:
            volume = handle_volume_change(-5)
        elif key in (ord("p"), ord("P"), ord(" ")):
            toggle_play_pause()
        elif chr(key) in KEYS:
            index = KEYS.index(chr(key))
            play_station(index)

        update_display(stdscr, status, volume)

if __name__ == "__main__":
    try:
        print("Loading stations...")
        load_data()
        stdscr = init_curses()
        start_refresh_thread()
        main(stdscr)
    except requests.ConnectionError:
        print("Connection Error")
        sys.exit(1)
    except KeyboardInterrupt:
        end_curses(stdscr)
        sys.exit(0)
    except Exception as e:
        print(f"ERROR: {e}")
        end_curses(stdscr)
        sys.exit(1)
