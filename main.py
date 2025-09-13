import tkinter as tk
from tkinter import font
import json
import random
import threading
import time
import os
import webbrowser
import pyperclip
import requests
from urllib.parse import urlparse
import asyncio

# -------------------------------
# Buttplug Python client (new API)
# -------------------------------
try:
    # The installed package exposes `Client` and `WebsocketConnector`.
    # Main code expects the older names `ButtplugClient`/`ButtplugClientWebsocketConnector`,
    # so import and alias them to keep the rest of the code unchanged.
    from buttplug.client import Client as ButtplugClient
    from buttplug.connectors import WebsocketConnector as ButtplugClientWebsocketConnector
except ImportError:
    raise ImportError("Please install the Buttplug Python client: pip install buttplug-py")

# Windows window detection
try:
    import pygetwindow as gw
except ImportError:
    raise ImportError("Please install pygetwindow: pip install pygetwindow")

# -------------------------------
# Load JSON Tasks
# -------------------------------
json_path = "tasks.json"
if not os.path.exists(json_path):
    raise FileNotFoundError(f"JSON file not found: {json_path}")

with open(json_path, "r") as f:
    tasks = json.load(f)

# -------------------------------
# Tkinter UI Setup
# -------------------------------
root = tk.Tk()
root.title("Simon Says: Windows Prototype")
root.geometry("700x500")
root.configure(bg="#222222")

root.tk.call('font', 'create', 'BebasNeue', '-family', 'Bebas Neue', '-size', 40)
title_font = font.Font(root=root, family='Bebas Neue', size=40, weight="bold")

canvas = tk.Canvas(root, width=700, height=100, bg="#222222", highlightthickness=0)
canvas.pack(pady=20)
title_shadow = canvas.create_text(352, 52, text="Simon Says!", font=title_font, fill="black")
title_text = canvas.create_text(350, 50, text="Simon Says!", font=title_font, fill="yellow")

task_var = tk.StringVar()
task_label = tk.Label(root, textvariable=task_var, font=("Arial", 18), fg="white", bg="#222222")
task_label.pack(pady=20)

button_frame = tk.Frame(root, bg="#222222")
button_frame.pack(pady=20)
open_btn = tk.Button(button_frame, text="Open Link / Do Task", font=("Arial", 14), bg="#555555", fg="white")
open_btn.grid(row=0, column=0, padx=10)
nothing_btn = tk.Button(button_frame, text="Do Nothing", font=("Arial", 14), bg="#555555", fg="white")
nothing_btn.grid(row=0, column=1, padx=10)
pick_task_btn = tk.Button(root, text="Pick Random Task", font=("Arial", 14), bg="#555555", fg="white")
pick_task_btn.pack(pady=10)

# -------------------------------
# Backend Logic
# -------------------------------
current_task = None
task_active = False
vibration_level = 0
_buttplug_client = None
_buttplug_device = None
_async_loop = None

# --- Async vibration client ---
async def async_init_vibration_client(url: str = "ws://127.0.0.1:12345"):
    """Connect to the Buttplug server, scan briefly, and pick the first device.
    This mirrors the example: connect then query client.devices.
    """
    global _buttplug_client, _buttplug_device
    client = ButtplugClient("SimonSaysClient")
    connector = ButtplugClientWebsocketConnector(url)

    try:
        await client.connect(connector)
    except Exception as e:
        print(f"[VIBRATION] Could not connect to Buttplug server: {e}")
        return

    _buttplug_client = client
    print("[VIBRATION] Buttplug client connected")

    # Start a short scan to populate devices then stop
    try:
        await client.start_scanning()
        await asyncio.sleep(2)
        await client.stop_scanning()
    except Exception:
        # Not fatal; some servers may not implement scanning the same way
        pass

    # Pick the first discovered device, if any
    devices = list(client.devices.values())
    if devices:
        _buttplug_device = devices[0]
        print(f"[VIBRATION] Using device: {_buttplug_device}")
    else:
        print("[VIBRATION] No Buttplug devices found after scan")

def init_vibration_client():
    """Create and run an asyncio event loop in a background thread, and schedule the async init.
    This keeps the loop running so run_coroutine_threadsafe can submit commands later.
    """
    global _async_loop
    _async_loop = asyncio.new_event_loop()

    def _run_loop():
        asyncio.set_event_loop(_async_loop)
        # Schedule the connection task
        _async_loop.create_task(async_init_vibration_client())
        _async_loop.run_forever()

    threading.Thread(target=_run_loop, daemon=True).start()

def set_vibration(level: int):
    global vibration_level, _buttplug_device, _buttplug_client
    vibration_level = max(0, min(100, int(level)))
    if _buttplug_device:
        amp = vibration_level / 100.0
        try:
            # Prefer actuator API if available
            if hasattr(_buttplug_device, 'actuators') and len(_buttplug_device.actuators) > 0:
                coro = _buttplug_device.actuators[0].command(amp)
            # Fallbacks for other implementations
            elif hasattr(_buttplug_device, 'send_vibrate_cmd'):
                coro = _buttplug_device.send_vibrate_cmd(amp)
            elif _buttplug_client and hasattr(_buttplug_client, 'stop_all'):
                # no-op: we can't vibrate, but avoid crash
                print('[VIBRATION] device has no vibrate method')
                return
            else:
                print('[VIBRATION] device has no vibrate method')
                return
            asyncio.run_coroutine_threadsafe(coro, _async_loop)
        except Exception as e:
            print(f"[VIBRATION] exception sending vibrate: {e}")
    else:
        print(f"[VIBRATION] (simulated) set to {vibration_level}%")

def stop_vibration():
    global vibration_level, _buttplug_device, _buttplug_client
    vibration_level = 0
    if _buttplug_device:
        try:
            if hasattr(_buttplug_device, 'stop'):
                coro = _buttplug_device.stop()
            elif hasattr(_buttplug_device, 'send_stop_device_cmd'):
                coro = _buttplug_device.send_stop_device_cmd()
            elif _buttplug_client and hasattr(_buttplug_client, 'stop_all'):
                coro = _buttplug_client.stop_all()
            else:
                print('[VIBRATION] device has no stop method')
                return
            asyncio.run_coroutine_threadsafe(coro, _async_loop)
        except Exception as e:
            print(f"[VIBRATION] exception stopping vibration: {e}")
    else:
        print("[VIBRATION] (simulated) stopped")

# Smooth color transition
colors = [
    (255, 255, 0), (0, 255, 0), (0, 255, 255),
    (255, 0, 255), (255, 165, 0), (255, 0, 0), (255, 255, 255)
]
current_index = 0
next_index = 1
steps = 25
step_count = 0

def rgb_to_hex(r,g,b):
    return f'#{int(r):02x}{int(g):02x}{int(b):02x}'

def update_color():
    global current_index, next_index, step_count
    c1 = colors[current_index]
    c2 = colors[next_index]
    r = c1[0] + (c2[0]-c1[0])*(step_count/steps)
    g = c1[1] + (c2[1]-c1[1])*(step_count/steps)
    b = c1[2] + (c2[2]-c1[2])*(step_count/steps)
    canvas.itemconfig(title_text, fill=rgb_to_hex(r,g,b))
    step_count +=1
    if step_count>steps:
        step_count=0
        current_index = next_index
        next_index = (next_index+1)%len(colors)
    root.after(30, update_color)

def animate_shadow():
    x_offset=random.randint(-3,3)
    y_offset=random.randint(-3,3)
    canvas.coords(title_shadow,350+x_offset+2,50+y_offset+2)
    root.after(100,animate_shadow)

def set_buttons(state:str):
    open_btn.config(state=state)
    nothing_btn.config(state=state)
    pick_task_btn.config(state=state)

# -------------------------------
# Windows-specific detection (partial, case-insensitive)
# -------------------------------
def is_task_running(task):
    if "window_title" in task:
        target_title = task["window_title"].lower()
        titles = gw.getAllTitles()
        for t in titles:
            if target_title in t.lower():
                return True
        return False
    else:
        # If the task doesn't specify a window_title we should not assume it's running
        return False

def monitor_task_start_and_countdown():
    global vibration_level
    while task_active:
        # For bluesky_post tasks we do NOT start the countdown here; countdown should begin
        # only after the user explicitly presses the Open button (so they have to perform the action).
        if is_task_running(current_task):
            stop_vibration()
            print("[VIBRATION] Task detected, stop 30% vibration, starting countdown")
            if current_task["duration"]>0:
                countdown_task(current_task["duration"])
            return
        time.sleep(1)

def countdown_task(seconds):
    for remaining in range(seconds, 0, -1):
        if not task_active:
            return

        # Preserve "Simon says" prefix
        simon_prefix = "Simon says: " if current_task and current_task.get('simon') else ""
        task_var.set(f"{simon_prefix}{current_task['name']} ({remaining}s left)")

        # If the task requires a window to be open, check every second
        if current_task and "window_title" in current_task:
            if not is_task_running(current_task):
                print("[RULE] Required window closed before time was up. Fail.")
                end_task(success=False)
                return

        time.sleep(1)

    # After countdown finishes
    if task_active:
        if current_task.get("type") == "bluesky_post":
            verify_bluesky_post()
        else:
            end_task(success=True)


def penalty_vibration():
    global vibration_level
    time.sleep(10)
    stop_vibration()
    print("[VIBRATION] Penalty finished, vibration stopped")
    set_buttons("normal")

def end_task(success=True):
    global task_active, vibration_level
    task_active = False
    if success:
        stop_vibration()
        print("[VIBRATION] Task completed correctly, stop vibration")
        set_buttons("normal")
    else:
        set_vibration(100)
        print(f"[VIBRATION] Wrong or abandoned! 100% vibration for 10s")
        set_buttons("disabled")
        threading.Thread(target=penalty_vibration, daemon=True).start()

# -------------------------------
# Resolve DID from handle (robust, multi-host)
# -------------------------------
HOSTS = ["bsky.app", "bsky.social", "public.bsky.social"]


def extract_handle(input_str):
    s = input_str.strip()
    if "://" in s:
        p = urlparse(s)
        path = p.path
        if path.startswith("/profile/"):
            return path.split("/profile/")[-1]
        parts = [seg for seg in path.split("/") if seg]
        if parts:
            return parts[-1]
        return s
    return s.lstrip('@')


def get_did_from_handle(handle):
    """Try resolving a handle against multiple known Bluesky hosts.
    Accepts plain handles, @handles, or full profile URLs.
    Returns DID string or None.
    """
    handle = extract_handle(handle)
    for host in HOSTS:
        url = f"https://{host}/xrpc/com.atproto.identity.resolveHandle?handle={handle}"
        try:
            r = requests.get(url, timeout=8)
            if r.status_code == 200:
                try:
                    data = r.json()
                    did = data.get("did")
                    if did:
                        print(f"Resolved DID on {host}: {did}")
                        return did
                except Exception as e:
                    print(f"Failed to parse JSON from {host}: {e}")
            else:
                print(f"Failed to resolve handle on {host}: {r.status_code}")
        except Exception as e:
            print(f"Request exception resolving on {host}: {e}")
    return None


def fetch_author_feed_try(did, limit=5):
    """Try several candidate endpoints to fetch the author feed without authentication.
    Returns JSON feed or None.
    """
    candidates = [f"https://{host}/xrpc/app.bsky.feed.getAuthorFeed" for host in HOSTS]
    candidates += [
        "https://public.bsky.app/xrpc/app.bsky.feed.getAuthorFeed",
        "https://public.api.bsky.app/xrpc/app.bsky.feed.getAuthorFeed",
        "https://bsky.app/xrpc/app.bsky.feed.getAuthorFeed",
    ]

    params = {"actor": did, "limit": limit}
    for ep in candidates:
        try:
            r = requests.get(ep, params=params, timeout=8)
            print(f"Feed endpoint {ep} returned {r.status_code}")
            if r.status_code == 200:
                try:
                    return r.json()
                except Exception as e:
                    print(f"Failed to parse JSON from {ep}: {e}")
            elif r.status_code in (401, 403):
                print(f"Authentication required at {ep}: {r.status_code}")
            else:
                print(f"Non-200 from {ep}: {r.status_code}")
        except Exception as e:
            print(f"Request exception for {ep}: {e}")
    return None

# -------------------------------
# Verify Bluesky post
# -------------------------------
def verify_bluesky_post():
    # Show "Simon is checking" while authenticating/validating
    task_var.set("Simon is checking...")

    post_text = current_task.get("post_text", "").lower()
    bluesky_did = current_task.get("bluesky_did")
    if not post_text:
        print("Bluesky verification skipped: missing post text")
        end_task(success=False)
        return

    if not bluesky_did:
        # First try to read the account from config.json
        did = None
        try:
            cfg_path = "config.json"
            if os.path.exists(cfg_path):
                with open(cfg_path, "r") as cf:
                    cfg = json.load(cf)
                    account = cfg.get("bluesky_account")
                    if account:
                        print(f"Using account from config: {account}")
                        did = get_did_from_handle(account)
        except Exception as e:
            print(f"Error reading config.json: {e}")

        # Fall back to interactive prompt if config didn't yield a DID
        if not did:
            handle = input("Enter your Bluesky handle or profile URL (e.g., https://bsky.app/profile/username.bsky.social): ")
            did = get_did_from_handle(handle)

        if did:
            current_task["bluesky_did"] = did
            bluesky_did = did
        else:
            print("Could not resolve DID, task will fail.")
            end_task(success=False)
            return

    print("Verifying Bluesky post...")
    feed = fetch_author_feed_try(bluesky_did, limit=10)
    if not feed:
        print("Failed to retrieve posts from public relays or authentication required.")
        end_task(success=False)
        return

    posts = feed.get("feed", [])
    if not posts:
        print("No posts found.")
        end_task(success=False)
        return

    found = False
    for post_obj in posts:
        text = post_obj.get("post", {}).get("text") or post_obj.get("post", {}).get("record", {}).get("text") or ""
        if post_text in text.lower():
            found = True
            break

    if found:
        print(f"Bluesky post found: '{post_text}'")
        end_task(success=True)
    else:
        print(f"No matching post found for '{post_text}'")
        end_task(success=False)

# -------------------------------
# Pick and auto-open tasks
# -------------------------------
def pick_task():
    global current_task, task_active, vibration_level
    # copy task to avoid mutating the original list
    current_task = random.choice(tasks).copy()
    # decide whether this task is prefixed with "Simon says"
    simon_flag = random.random() < 0.5
    current_task['simon'] = simon_flag
    simon_prefix = "Simon says: " if simon_flag else ""
    task_var.set(f"{simon_prefix}{current_task['name']} ({current_task['duration']}s)")
    task_active = True
    set_vibration(30)
    print(f"[VIBRATION] Start at {vibration_level}%")
    # keep buttons enabled so user can respond; monitoring thread will still run for detection

    # Do not auto-open links or copy clipboard here — wait for the user's button press
    # Info messages only
    if current_task.get("type")=="open_link" and "link" in current_task:
        print(f"[INFO] Link available: {current_task['link']}")

    if current_task.get("type")=="bluesky_post" and "post_text" in current_task:
        print(f"[BLUESKY] Post text ready to copy when you press the button")
        if "bluesky_open" in current_task and current_task["bluesky_open"]:
            print("[INFO] Bluesky profile can be opened when you press the button")

    # Start the monitor only for tasks that rely on window detection or a duration-based countdown.
    # Bluesky posts require the user to press Open first, so don't spawn the monitor here for them.
    if current_task["duration"]>0 and current_task.get("type")!="bluesky_post":
        threading.Thread(target=monitor_task_start_and_countdown,daemon=True).start()
    else:
        set_buttons("normal")

def open_task():
    if not task_active:
        return

    # If Simon didn't say, pressing this is an instant fail
    if current_task and not current_task.get('simon'):
        print("[RULE] Simon didn't say! You lose.")
        end_task(success=False)
        return

    # Otherwise, run the actual task
    try:
        if current_task.get("type")=="open_link" and "link" in current_task:
            print(f"[ACTION] Opening link: {current_task['link']}")
            webbrowser.open(current_task["link"])

        if current_task.get("type")=="bluesky_post" and "post_text" in current_task:
            try:
                pyperclip.copy(current_task["post_text"])
                print("[BLUESKY] Post text copied to clipboard")
            except Exception:
                print("[BLUESKY] Could not copy to clipboard")

            if current_task.get("bluesky_open"):
                print("[ACTION] Opening Bluesky profile")
                webbrowser.open("https://bsky.app")

            run_short_countdown(10)

        # For non-bluesky tasks, now rely on monitor/countdown instead of ending instantly
        elif current_task.get("duration", 0) > 0:
            threading.Thread(target=monitor_task_start_and_countdown, daemon=True).start()

    except Exception as e:
        print(f"Exception performing action: {e}")
        end_task(success=False)



def run_short_countdown(seconds=60):
    def _runner():
        for remaining in range(seconds, 0, -1):
            if not task_active:
                return
            simon_prefix = "Simon says: " if current_task and current_task.get('simon') else ""
            task_var.set(f"{simon_prefix}{current_task['name']} ({remaining}s left)")
            time.sleep(1)

        # After countdown, trigger verification
        if task_active and current_task.get("type") == "bluesky_post":
            task_var.set("Simon is checking...")
            verify_bluesky_post()

    threading.Thread(target=_runner, daemon=True).start()


def do_nothing_task():
    if not task_active:
        return

    # If Simon didn't say, doing nothing is correct
    if current_task and not current_task.get('simon'):
        print("[RULE] Correct! You ignored the command.")
        end_task(success=True)
    else:
        print("[RULE] Simon DID say, but you did nothing. Fail.")
        end_task(success=False)

open_btn.config(command=lambda: open_task())
nothing_btn.config(command=lambda: do_nothing_task())
pick_task_btn.config(command=lambda: threading.Thread(target=pick_task,daemon=True).start())

init_vibration_client()
animate_shadow()
update_color()

root.mainloop()
