import os
import time
import urllib.request
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from keep_alive import keep_alive

API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
SESSION_STRING = os.environ.get("SESSION_STRING")
WEBSITE_URL = "https://user-bot-g3kn.onrender.com"

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

def build_map(upper_start, lower_start):
    m = {}
    for i, c in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
        m[c] = chr(upper_start + i)
    for i, c in enumerate("abcdefghijklmnopqrstuvwxyz"):
        m[c] = chr(lower_start + i)
    return m

def build_upper_only(start):
    m = {}
    for i, c in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
        m[c] = chr(start + i)
    for c in "abcdefghijklmnopqrstuvwxyz":
        m[c] = m[c.upper()]
    return m

SMALL_CAPS = {
    'a':'ᴀ','b':'ʙ','c':'ᴄ','d':'ᴅ','e':'ᴇ','f':'ꜰ','g':'ɢ','h':'ʜ','i':'ɪ','j':'ᴊ',
    'k':'ᴋ','l':'ʟ','m':'ᴍ','n':'ɴ','o':'ᴏ','p':'ᴘ','q':'ǫ','r':'ʀ','s':'s','t':'ᴛ',
    'u':'ᴜ','v':'ᴠ','w':'ᴡ','x':'x','y':'ʏ','z':'ᴢ'
}

BOLD = build_map(0x1D400, 0x1D41A)

ITALIC = build_map(0x1D434, 0x1D44E)
ITALIC.update({'h': '\u210E'})

SANS_BOLD_ITALIC = build_map(0x1D63C, 0x1D656)
MONOSPACE = build_map(0x1D670, 0x1D68A)

DOUBLE_STRUCK = build_map(0x1D538, 0x1D552)
DOUBLE_STRUCK.update({'C':'\u2102','H':'\u210D','N':'\u2115','P':'\u2119',
                       'Q':'\u211A','R':'\u211D','Z':'\u2124'})

BOLD_FRAKTUR = build_map(0x1D56C, 0x1D586)
BOLD_SCRIPT = build_map(0x1D4D0, 0x1D4EA)
BOLD_ITALIC = build_map(0x1D468, 0x1D482)
SANS_BOLD = build_map(0x1D5D4, 0x1D5EE)
SQUARED = build_upper_only(0x1F130)

CIRCLED = {}
for i, c in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
    CIRCLED[c] = chr(0x24B6 + i)
for i, c in enumerate("abcdefghijklmnopqrstuvwxyz"):
    CIRCLED[c] = chr(0x24D0 + i)

def apply_map(text, m):
    return "".join(m.get(ch, ch) for ch in text)

def title_small_caps(text, bold_first=False):
    words = text.split(" ")
    out = []
    for w in words:
        if not w:
            out.append(w)
            continue
        first, rest = w[0], w[1:]
        if bold_first:
            first = BOLD.get(first, first)
        rest = "".join(SMALL_CAPS.get(c.lower(), c) for c in rest)
        out.append(first + rest)
    return " ".join(out)

def full_small_caps(text):
    return "".join(SMALL_CAPS.get(c.lower(), c) if c.islower() else c for c in text)

def f1(t): return apply_map(t, SANS_BOLD_ITALIC)
def f2(t): return title_small_caps(t, bold_first=True)
def f3(t): return title_small_caps(t, bold_first=False)
def f4(t): return apply_map(t, BOLD)
def f5(t): return apply_map(t, ITALIC)
def f6(t): return apply_map(t, MONOSPACE)
def f7(t): return apply_map(t, DOUBLE_STRUCK)
def f8(t): return apply_map(t, BOLD_FRAKTUR)
def f9(t): return apply_map(t, BOLD_SCRIPT)
def f10(t): return apply_map(t, CIRCLED)
def f11(t): return apply_map(t, BOLD_ITALIC)
def f12(t): return apply_map(t, SANS_BOLD)
def f13(t): return full_small_caps(t)
def f14(t): return apply_map(t, SQUARED)
def f15(t): return t[::-1]

FONTS = {
    "f1": ("Sans Bold Italic", f1),
    "f2": ("Bold + Small Caps", f2),
    "f3": ("Normal + Small Caps", f3),
    "f4": ("Bold", f4),
    "f5": ("Italic", f5),
    "f6": ("Monospace", f6),
    "f7": ("Double-struck", f7),
    "f8": ("Bold Fraktur", f8),
    "f9": ("Bold Script", f9),
    "f10": ("Circled", f10),
    "f11": ("Bold Italic", f11),
    "f12": ("Sans Bold", f12),
    "f13": ("Full Small Caps", f13),
    "f14": ("Squared", f14),
    "f15": ("Reverse Text", f15),
}

active_font = {"key": None}

@client.on(events.NewMessage(outgoing=True, pattern=r'(?i)^/select (\S+)$'))
async def select_font(event):
    choice = event.pattern_match.group(1).lower()
    if choice == "none":
        active_font["key"] = None
        await event.edit("✅ Font reset to normal.")
        return
    if choice in FONTS:
        active_font["key"] = choice
        name = FONTS[choice][0]
        await event.edit(f"✅ Font set to {choice.upper()} ({name}).")
    else:
        await event.edit("❌ Invalid font. Use /font_list to see options.")

@client.on(events.NewMessage(outgoing=True, pattern=r'(?i)^/font_list$'))
async def font_list(event):
    lines = ["Available Fonts:\n"]
    for key, (name, fn) in FONTS.items():
        sample = fn("Hello")
        lines.append(f"{key} -> {sample}  ({name})")
    lines.append("\n/select f1 se f15 tak, ya /select none")
    await event.edit("\n".join(lines))

@client.on(events.NewMessage(outgoing=True, pattern=r'(?i)^/ping$'))
async def ping(event):
    t0 = time.time()
    await event.edit("🏓 Pinging...")
    t1 = time.time()
    telegram_edit_ms = (t1 - t0) * 1000

    try:
        t_before = time.time()
        with urllib.request.urlopen(WEBSITE_URL + "/ping", timeout=15) as resp:
            server_ts = float(resp.read().decode().strip())
        t_after = time.time()

        to_website_ms = (server_ts - t_before) * 1000
        from_website_ms = (t_after - server_ts) * 1000
        total_http_ms = (t_after - t_before) * 1000

        result = (
            "🏓 Pong!\n\n"
            f"Telegram edit: {telegram_edit_ms:.0f} ms\n"
            f"Telegram -> Website: {to_website_ms:.0f} ms\n"
            f"Website -> Telegram: {from_website_ms:.0f} ms\n"
            f"Total round-trip: {total_http_ms:.0f} ms"
        )
    except Exception as e:
        result = f"🏓 Telegram edit: {telegram_edit_ms:.0f} ms\n❌ Website unreachable: {e}"

    await event.edit(result)

@client.on(events.NewMessage(outgoing=True))
async def convert_message(event):
    text = event.raw_text
    if text.startswith("/select") or text.startswith("/font_list") or text.startswith("/ping"):
        return
    key = active_font["key"]
    if key is None:
        return
    fn = FONTS[key][1]
    new_text = fn(text)
    if new_text != text:
        await event.edit(new_text)

async def notify_started():
    await client.send_message("me", "✅ Userbot Connected — font system ready.")

if __name__ == "__main__":
    keep_alive()
    with client:
        client.loop.run_until_complete(notify_started())
        print("Userbot running...")
        client.run_until_disconnected()
