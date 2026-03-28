

import subprocess, time, os, sys, json, urllib.request, urllib.parse, shutil, re, threading, random

CACHE_DIR      = os.path.expanduser("~/.cache/lyrics")
PLAYERCTL_RATE = 0.3
OFFSET         = 0.0
ESC            = "\x1b"
CLEAR          = ESC + "[2J" + ESC + "[H"
DIM            = ESC + "[2m"
RESET          = ESC + "[0m"
BLINK          = ESC + "[5m"

MAX_HISTORY = 9  # how many past lines to show above current

def redraw(history, current_text, revealed=None, cursor=False):
    cols, rows_t = shutil.get_terminal_size((80, 24))
    max_past = min(MAX_HISTORY, rows_t - 3)
    past = history[-max_past:] if len(history) > max_past else history[:]
    total_lines = len(past) + (1 if current_text else 0)
    top_pad = max(0, (rows_t - total_lines) // 2)
    buf = [CLEAR]
    buf.append("\n" * top_pad)
    for line in past:
        if len(line) > cols:
            words = line.split()
            sub, subs = "", []
            for w in words:
                if len(sub) + len(w) + 1 > cols:
                    subs.append(sub.strip())
                    sub = w + " "
                else:
                    sub += w + " "
            if sub: subs.append(sub.strip())
            for s in subs:
                left = max(0, (cols - len(s)) // 2)
                buf.append(DIM + " " * left + s + RESET + "\n")
        else:
            left = max(0, (cols - len(line)) // 2)
            buf.append(DIM + " " * left + line + RESET + "\n")
    if current_text:
        shown = current_text[:revealed] if revealed is not None else current_text
        cur_str = shown + (BLINK + "|" + RESET if cursor else "")
        left = max(0, (cols - len(current_text)) // 2)
        buf.append(" " * left + cur_str + "\n")
    sys.stdout.write("".join(buf))
    sys.stdout.flush()

def display_status(msg):
    cols, rows_t = shutil.get_terminal_size((80, 24))
    sys.stdout.write(CLEAR)
    sys.stdout.write("\n" * (rows_t // 2))
    sys.stdout.write(msg.center(cols) + "\n")
    sys.stdout.flush()

def animate_line(history, text, start_mono, end_mono):
    n = len(text)
    if n == 0: return
    duration = end_mono - start_mono
    if duration <= 0:
        redraw(history, text); return
    per_char = duration / n
    for step in range(n):
        scheduled = start_mono + step * per_char
        now = time.monotonic()
        if scheduled > now: time.sleep(scheduled - now)
        if time.monotonic() > end_mono + 0.05: break
        redraw(history, text, revealed=step + 1, cursor=(step < n - 1))

def idle_animation(stop_event):
    random.seed(42)
    cols, rows_t = shutil.get_terminal_size((80, 24))
    stars = []
    for _ in range(150):
        x = random.uniform(0, cols)
        y = random.randint(0, rows_t - 1)
        speed = random.uniform(0.1, 2.5)
        ch = random.choice(["·", "·", "·", "∙", "✦", "★", "*", "•"])
        trail_char = random.choice(["─", "─", "─", "−", "‐"])
        brightness = random.choice([DIM, RESET, DIM, DIM])
        stars.append([x, y, speed, ch, trail_char, brightness])

    frame = 0
    while not stop_event.is_set():
        cols, rows_t = shutil.get_terminal_size((80, 24))
        screen = [[" "] * cols for _ in range(rows_t)]
        color_screen = [[RESET] * cols for _ in range(rows_t)]

        for s in stars:
            s[0] -= s[2]
            if s[0] < 0:
                s[0] = cols
                s[1] = random.randint(0, rows_t - 1)
                s[2] = random.uniform(0.1, 2.5)
                s[3] = random.choice(["·", "·", "·", "∙", "✦", "★", "*", "•"])
                s[5] = random.choice([DIM, RESET, DIM, DIM])

            sx, sy = int(s[0]), s[1]
            trail_len = max(1, int(s[2] * 2))

            # draw trail
            for tx in range(trail_len):
                c = sx + tx
                if 0 <= sy < rows_t and 0 <= c < cols:
                    screen[sy][c] = s[4]
                    color_screen[sy][c] = DIM

            # draw star head with occasional twinkle
            if 0 <= sy < rows_t and 0 <= sx < cols:
                twinkle = (frame % 20 == int(s[2] * 7) % 20)
                screen[sy][sx] = "✦" if twinkle else s[3]
                color_screen[sy][sx] = RESET if twinkle else s[5]

        buf = [CLEAR]
        for r in range(rows_t):
            for c in range(cols):
                buf.append(color_screen[r][c] + screen[r][c] + RESET)
            buf.append("\n")

        sys.stdout.write("".join(buf))
        sys.stdout.flush()
        frame += 1
        time.sleep(0.05)

def playerctl_meta():
    try:
        r = subprocess.run(["playerctl", "-p", "spotify", "metadata",
             "--format", "{{artist}}|||{{title}}|||{{position}}|||{{status}}"],
            capture_output=True, text=True, timeout=1.0)
        if r.returncode != 0: return None
        parts = r.stdout.strip().split("|||")
        if len(parts) != 4: return None
        artist, title, pos_us, status = parts
        return artist.strip(), title.strip(), float(pos_us) / 1_000_000, status.strip()
    except: return None

class Tracker:
    def __init__(self):
        self.lock = threading.Lock()
        self._pos = 0.0; self._pos_time = time.monotonic()
        self._playing = False; self._artist = ""; self._title = ""
        self._running = True
        threading.Thread(target=self._loop, daemon=True).start()
    def _loop(self):
        while self._running:
            meta = playerctl_meta()
            now = time.monotonic()
            if meta:
                artist, title, pos, status = meta
                with self.lock:
                    self._pos = pos; self._pos_time = now
                    self._playing = (status == "Playing")
                    self._artist = artist; self._title = title
            time.sleep(PLAYERCTL_RATE)
    def get(self):
        with self.lock:
            elapsed = (time.monotonic() - self._pos_time) if self._playing else 0
            return self._artist, self._title, self._pos + elapsed + OFFSET, self._playing
    def mono_for(self, song_pos):
        with self.lock:
            elapsed = (time.monotonic() - self._pos_time) if self._playing else 0
            return time.monotonic() + (song_pos - (self._pos + elapsed + OFFSET))
    def stop(self): self._running = False

os.makedirs(CACHE_DIR, exist_ok=True)
def cache_path(artist, title):
    safe = re.sub(r"[^\w\s-]", "", f"{artist} - {title}").strip()
    return os.path.join(CACHE_DIR, re.sub(r"\s+", "_", safe) + ".json")
def fetch_lyrics(artist, title):
    cp = cache_path(artist, title)
    if os.path.exists(cp):
        with open(cp) as f: return json.load(f)
    url = "https://lrclib.net/api/get?" + urllib.parse.urlencode({"artist_name": artist, "track_name": title})
    try:
        with urllib.request.urlopen(url, timeout=6) as resp: data = json.loads(resp.read())
    except: return None
    synced = data.get("syncedLyrics", "")
    if not synced: return None
    lines = parse_lrc(synced)
    if not lines: return None
    with open(cp, "w") as f: json.dump(lines, f)
    return lines
def parse_lrc(text):
    pat = re.compile(r"\[(\d+):(\d+\.\d+)\](.*)")
    lines = []
    for line in text.splitlines():
        m = pat.match(line.strip())
        if m:
            mins, secs, lyric = m.groups()
            ts = int(mins) * 60 + float(secs)
            lyric = lyric.strip()
            if lyric: lines.append([ts, lyric])
    lines.sort(key=lambda x: x[0])
    return lines

def run():
    sys.stdout.write(ESC + "[?25l"); sys.stdout.flush()
    tracker = Tracker()
    current_track = None; lines = []; line_idx = -1
    history = []
    idle_thread = None; stop_idle = None
    def start_idle():
        nonlocal idle_thread, stop_idle
        if idle_thread and idle_thread.is_alive(): return
        stop_idle = threading.Event()
        idle_thread = threading.Thread(target=idle_animation, args=(stop_idle,), daemon=True)
        idle_thread.start()
    def stop_idle_anim():
        nonlocal idle_thread, stop_idle
        if stop_idle: stop_idle.set()
        if idle_thread: idle_thread.join(timeout=0.5)
        idle_thread = None; stop_idle = None
    start_idle()
    try:
        while True:
            artist, title, pos, playing = tracker.get()
            track = (artist, title) if artist else None
            if track != current_track:
                current_track = track; lines = []; line_idx = -1; history.clear()
                stop_idle_anim()
                if track:
                    display_status(f"{artist}  -  {title}")
                    fetched = fetch_lyrics(artist, title)
                    lines = fetched if fetched else []
                    if not lines: display_status("no lyrics found"); start_idle()
                else:
                    start_idle()
            if not lines or not playing:
                if not (idle_thread and idle_thread.is_alive()): start_idle()
                time.sleep(0.2); continue
            stop_idle_anim()
            lo, hi, new_idx = 0, len(lines) - 1, 0
            while lo <= hi:
                mid = (lo + hi) // 2
                if lines[mid][0] <= pos: new_idx = mid; lo = mid + 1
                else: hi = mid - 1
            if new_idx == line_idx:
                time.sleep(0.016); continue
            line_idx = new_idx
            cur_text = lines[line_idx][1]
            cur_end  = lines[line_idx + 1][0] if line_idx + 1 < len(lines) else lines[line_idx][0] + 4.0
            now_mono      = time.monotonic()
            line_end_mono = tracker.mono_for(cur_end)
            total_budget  = line_end_mono - now_mono
            if total_budget < 0.05:
                history.append(cur_text); redraw(history, ""); continue
            animate_line(history, cur_text, now_mono, line_end_mono)
            history.append(cur_text)
    except KeyboardInterrupt: pass
    finally:
        stop_idle_anim(); tracker.stop()
        sys.stdout.write(ESC + "[?25h"); sys.stdout.flush(); os.system("clear")

run()
