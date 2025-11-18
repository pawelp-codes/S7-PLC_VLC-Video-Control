import socket
import vlc
import threading
import time

# HOST = '127.0.0.1'  # IP localhost - for tests with Hercules app
HOST = '192.168.0.101'  # IP PC
PORT = 2000              # Port - set in PLC configuration

# ================== Global variables ==================
vlc_instance = vlc.Instance(
    "--no-video-title-show",
    "--no-video-deco",
    "--fullscreen",
    "--video-on-top",
    "--vout=direct3d9",
    "--avcodec-hw=none",
)
player = None
conn = None
player_lock = threading.Lock()  # thread sync

# ================== VLC ==================
def start_vlc():
    global player
    with player_lock:
        if player is None:
            media = vlc_instance.media_new(r"C:\Users\Pawel\Desktop\filmik.mp4") ## movie film path
            player = vlc_instance.media_player_new()
            player.set_media(media)
            player.play()
            return "START"
        elif not player.is_playing():
            player.play()
            return "START"
    return "ALREADY_RUNNING"

def stop_vlc():
    global player
    with player_lock:
        if player is not None:
            try:
                player.stop()
            except Exception as e:
                print("Błąd zatrzymania VLC:", e)
            player = None
            return "STOP"
    return "NOT_RUNNING"

def reset_vlc():
    stop_vlc()
    return start_vlc()

def pause_vlc():
    with player_lock:
        if player is not None:
            if player.is_playing():
                player.pause()  # PAUSE
                return "PAUSE"
            else:
                return "ALREADY_PAUSED"
    return "NOT_RUNNING"

def resume_vlc():
    with player_lock:
        if player is not None:
            if not player.is_playing():
                player.play()  # RESUME
                return "START"
            else:
                return "ALREADY_RUNNING"
    return "NOT_RUNNING"

def rewind_0_vlc():
    with player_lock:
        if player is not None:
            player.set_time(0)
            return "REWIND"
    return "NOT_RUNNING"

def rewind_x_vlc():
    with player_lock:
        if player is not None:
            player.set_time(5000)  # REWIND to 5s
            return "REWIND"
    return "NOT_RUNNING"

# ================== Parser ==================
def extract_command_bytes(data: bytes) -> str:
    """Wyciąga pierwszą cyfrę ASCII (0-9) z surowych bajtów odebranych od PLC."""
    for b in data:
        if 48 <= b <= 57:
            return chr(b)
    return ""

# ================== Time monitoring to stop before end of file ==================
def monitor_player():
    global player, conn
    while True:
        with player_lock:
            if player is not None:
                try:
                    current_time = player.get_time()
                    total_length = player.get_length()
                    if total_length > 0 and current_time >= total_length - 200:
                        # rewind to begin before player reach end of file
                        player.set_time(0)
                        player.pause()  # pause – PLC command decide when start

                        # send END_OF_FILE message to PLC
                        if conn:
                            try:
                                reply = "END_OF_FILE".ljust(21)
                                conn.sendall(reply.encode("ascii"))
                                print("WYSŁANO (END_OF_FILE):", repr(reply))
                            except Exception as e:
                                print("Błąd wysyłania END_OF_FILE:", e)
                except Exception as e:
                    print("Błąd w monitor_player:", e)
        time.sleep(0.01)  # each 10ms check time

# ================== Livebit (heartbeat) ==================
def livebit_sender():
    global conn
    i = 0
    while True:
        if conn:
            try:
                if i == 0:
                    msg = "HB0".ljust(21)  # fixed length 21 bytes
                    conn.sendall(msg.encode("ascii"))
                    i = i + 1
                elif i == 1:
                    msg = "HB1".ljust(21)  # fixed length 21 bytes
                    conn.sendall(msg.encode("ascii"))
                    i = i + 1
                else: 
                    i = 0
                print("WYSŁANO (HEARTBEAT):", repr(msg))  # debug

            except Exception as e:
                print("Błąd wysyłania HEARTBEAT:", e)
                conn = None  # PLC connection down
        time.sleep(1.0)  # each 1 sec send heartbeat

# run thread in the background - monitor player
threading.Thread(target=monitor_player, daemon=True).start()

# ================== Command map ==================
command_map = {
    "1": start_vlc,
    "2": stop_vlc,
    "3": reset_vlc,
    "4": pause_vlc,
    "5": resume_vlc,
    "6": rewind_0_vlc,
    "7": rewind_x_vlc,
}

# ================== TCP Server ==================
while True:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((HOST, PORT))
            s.listen()
            print(f"Serwer TCP działa na {HOST}:{PORT}, czeka na PLC...")

            conn, addr = s.accept()
            print(f"Połączono z: {addr}")
            
            try:
                welcome = "CONNECTED".ljust(21)
                conn.sendall(welcome.encode("ascii"))
                print(f"WYSŁANO: {repr(welcome)}")

                time.sleep(2.0)
                # after establish connection we run thread heartbeat
                threading.Thread(target=livebit_sender, daemon=True).start()

                while True:
                    data = conn.recv(1024)
                    if not data:
                        print("Rozłączenie klienta, wracam do nasłuchu...")
                        break

                    msg = extract_command_bytes(data)
                    print("MSG PARSED:", repr(msg))
                    if not msg:
                        continue

                    # choose command from dictionary
                    func = command_map.get(msg)
                    if func:
                        response = func()
                    else:
                        response = "UNKNOWN_COMMAND"

                    try:
                        reply = response.ljust(21)
                        conn.sendall(reply.encode("ascii"))
                        print(f"WYSŁANO: {repr(reply)}")
                    except Exception as e:
                        print("Błąd wysyłania odpowiedzi:", e)

                    time.sleep(0.01)

            except Exception as e:
                print(f"Błąd połączenia: {e}, wracam do nasłuchu...")
            finally:
                if conn:
                    try:
                        conn.close()
                    except:
                        pass
                    conn = None

    except socket.error as e:
        print(f"Błąd przy próbie nasłuchu na {HOST}:{PORT}: {e}")
        time.sleep(5)  # reconnect after 5s