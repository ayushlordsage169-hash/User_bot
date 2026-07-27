import os
import time
import json
import random
import asyncio
import urllib.request
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from keep_alive import keep_alive

API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
SESSION_STRING = os.environ.get("SESSION_STRING")
WEBSITE_URL = "https://user-bot-6gxe.onrender.com"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# ==================== FONT SYSTEM ====================

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

def bold_upper_smallcaps_lower(text):
    out = []
    for c in text:
        if c.isupper():
            out.append(BOLD.get(c, c))
        elif c.islower():
            out.append(SMALL_CAPS.get(c, c))
        else:
            out.append(c)
    return "".join(out)

def full_small_caps(text):
    return "".join(SMALL_CAPS.get(c.lower(), c) if c.islower() else c for c in text)

def f1(t): return apply_map(t, SANS_BOLD_ITALIC)
def f2(t): return bold_upper_smallcaps_lower(t)
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
    "f1": ("Sans Bold Italic", f1), "f2": ("Bold + Small Caps", f2),
    "f3": ("Normal + Small Caps", f3), "f4": ("Bold", f4),
    "f5": ("Italic", f5), "f6": ("Monospace", f6),
    "f7": ("Double-struck", f7), "f8": ("Bold Fraktur", f8),
    "f9": ("Bold Script", f9), "f10": ("Circled", f10),
    "f11": ("Bold Italic", f11), "f12": ("Sans Bold", f12),
    "f13": ("Full Small Caps", f13), "f14": ("Squared", f14),
    "f15": ("Reverse Text", f15),
}

active_font = {"key": None}
skip_font_ids = set()

COMMAND_PREFIXES = ("/select", "/font_list", "/ping", "/auto_reply",
                     "/savage_reply", "/save_message", "/complete_message")

# ==================== GEMINI AUTO-REPLY ====================

GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

PERSONA_PROMPT = (
    "Tumhara naam 'Death Sage' hai (title: Death, name: Sage). "
    "Personality: friendly, smart, cool aura, confident, thoda dangerous/edgy vibe — "
    "lekin bilkul ek normal, real insaan ki tarah baat karo. Kabhi genuinely rude, "
    "threatening ya harmful nahi bante. "
    "Replies chhote aur seedhe rakho by default — sirf tab lamba likho jab genuinely "
    "detail ki zarurat ho (jaise koi specific sawaal poochhe). Chat casual ya funny "
    "direction mein ja rahi ho tab bhi tum thoda normal, careful tone mein hi raho — "
    "overboard funny banne ki koshish mat karo. "
    "Kabhi bhi anime characters ke naam (jaise Gojo, Sukuna, Fushiguro, Madara, Itachi, "
    "ya koi aur) apni marzi se mat lena — sirf tabhi jab user khud unka zikr kare ya "
    "poochhe. "
    "Language rule: chahe user English mein likhe ya Hindi mein, tum HAMESHA Hinglish "
    "(Hindi-English mix, Roman script) mein hi reply karoge, kabhi pure English ya "
    "pure Devanagari Hindi mein nahi likhoge."
)

def ask_gemini(user_message):
    body = {
        "contents": [{"parts": [{"text": user_message}]}],
        "systemInstruction": {"parts": [{"text": PERSONA_PROMPT}]},
    }
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        GEMINI_URL,
        data=data,
        headers={"Content-Type": "application/json", "x-goog-api-key": GEMINI_API_KEY},
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        result = json.loads(resp.read().decode())
    return result["candidates"][0]["content"]["parts"][0]["text"]

GROUP_KEYWORDS = ("hello", "death", "sage")

def has_keyword(text):
    lower = text.lower()
    return any(kw in lower for kw in GROUP_KEYWORDS)

async def send_with_typing_delay(event, text, as_reply):
    delay = random.uniform(1, 2) if len(text) <= 60 else random.uniform(3, 4)
    async with client.action(event.chat_id, 'typing'):
        await asyncio.sleep(delay)
    if as_reply:
        return await event.reply(text)
    return await event.respond(text)

auto_reply_chats = set()
savage_reply_count = {"total": 0}

# ---- Save Message / Savage Reply state ----
saved_messages = []
save_mode = {"active": False}
savage_targets = {}  # (chat_id, user_id) -> {"index": 0}

def next_savage_message(key):
    state = savage_targets[key]
    idx = state["index"]
    msg = saved_messages[idx % len(saved_messages)]
    state["index"] = idx + 1
    return msg

@client.on(events.NewMessage(outgoing=True, pattern=r'(?i)^/auto_reply (on|off)$'))
async def auto_reply_toggle(event):
    mode = event.pattern_match.group(1).lower()
    chat_id = event.chat_id
    if mode == "on":
        auto_reply_chats.add(chat_id)
        await event.edit("✅ Auto-reply ON is chat ke liye.")
    else:
        auto_reply_chats.discard(chat_id)
        await event.edit("✅ Auto-reply OFF is chat ke liye.")

@client.on(events.NewMessage(outgoing=True, pattern=r'(?i)^/save_message$'))
async def save_message_start(event):
    save_mode["active"] = True
    saved_messages.clear()
    await event.edit("✅ Saving shuru — jo bhi messages ab bhejoge wo list mein save honge. Khatam karne ke liye /complete_message bhejo.")

@client.on(events.NewMessage(outgoing=True, pattern=r'(?i)^/complete_message$'))
async def save_message_end(event):
    save_mode["active"] = False
    await event.edit(f"✅ {len(saved_messages)} messages save ho gaye.")

@client.on(events.NewMessage(outgoing=True, pattern=r'(?i)^/savage_reply (on|off)$'))
async def savage_reply_toggle(event):
    mode = event.pattern_match.group(1).lower()
    if not event.is_reply:
        await event.edit("❌ Us insaan ke kisi message pe reply karke ye command bhejo.")
        return
    replied = await event.get_reply_message()
    target_id = replied.sender_id
    key = (event.chat_id, target_id)
    if mode == "on":
        if not saved_messages:
            await event.edit("❌ Pehle /save_message se kuch messages save karo.")
            return
        savage_targets[key] = {"index": 0}
        await event.edit("✅ Savage reply ON is user ke liye — ab inka har message reply hoga, koi keyword/tag zaroori nahi.")
    else:
        savage_targets.pop(key, None)
        await event.edit("✅ Savage reply OFF is user ke liye.")

@client.on(events.NewMessage(outgoing=True))
async def capture_saved_message(event):
    if not save_mode["active"]:
        return
    text = event.raw_text
    if not text or text.startswith("/"):
        return
    saved_messages.append(text)

@client.on(events.NewMessage(incoming=True))
async def incoming_handler(event):
    text = event.raw_text
    if not text:
        return

    chat_id = event.chat_id
    is_group = not event.is_private
    key = (chat_id, event.sender_id)

    # Savage reply: sabse pehle check, koi gating nahi — target ka koi bhi
    # message trigger karega, chahe wo kisi aur ko tag kare.
    if key in savage_targets:
        if not saved_messages:
            return
        reply_text = f2(next_savage_message(key))
        sent = await send_with_typing_delay(event, reply_text, as_reply=True)
        skip_font_ids.add(sent.id)
        savage_reply_count["total"] += 1
        return

    # Normal auto-reply: group mein keyword/mention gating lagti hai
    if is_group:
        triggered = has_keyword(text) or event.message.mentioned
        if not triggered:
            return

    if chat_id not in auto_reply_chats:
        return
    try:
        reply = ask_gemini(text)
        sent = await send_with_typing_delay(event, reply, as_reply=is_group)
        skip_font_ids.add(sent.id)
    except Exception as e:
        print(f"Gemini error: {e}")

# ==================== COMMANDS ====================

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
            f"Total round-trip: {total_http_ms:.0f} ms\n"
            f"Savage replies sent: {savage_reply_count['total']}"
        )
    except Exception as e:
        result = (
            f"🏓 Telegram edit: {telegram_edit_ms:.0f} ms\n"
            f"❌ Website unreachable: {e}\n"
            f"Savage replies sent: {savage_reply_count['total']}"
        )
    await event.edit(result)

@client.on(events.NewMessage(outgoing=True))
async def convert_message(event):
    if event.id in skip_font_ids:
        skip_font_ids.discard(event.id)
        return
    text = event.raw_text
    if text.startswith(COMMAND_PREFIXES):
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
