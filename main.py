import os
import re
import time
import json
import random
import asyncio
import urllib.request
import urllib.error
from telethon import TelegramClient, events, functions
from telethon.sessions import StringSession
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.functions.messages import HideChatJoinRequestRequest, HideAllChatJoinRequestsRequest
from keep_alive import keep_alive

API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
SESSION_STRING = os.environ.get("SESSION_STRING")
WEBSITE_URL = "https://user-bot-p071.onrender.com"
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
START_TIME = time.time()

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

PROTECT_PATTERN = re.compile(r'(https?://\S+|@\w+)')

def apply_font_protected(text, font_fn):
    parts = PROTECT_PATTERN.split(text)
    result = []
    for part in parts:
        if part and PROTECT_PATTERN.fullmatch(part):
            result.append(part)
        else:
            result.append(font_fn(part))
    return "".join(result)

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

def sys_text(s):
    return full_small_caps(s)

# ==================== EMOTION LIBRARY ====================

EMOTIONS = {
    "e1": "⟵(๑¯◡¯๑)",
    "e2": "(☞ ͡° ͜ʖ ͡°)☞",
    "e3": "→_→",
    "e4": "(✧Д✧)→",
    "e5": "♡((灬º‿º灬)♡",
    "e6": "ᕙ( ~ . ~ )ᕗ",
    "e7": "⁄(⁄ ⁄•⁄-⁄•⁄ ⁄)⁄",
    "e8": "♪┌|∵|┘♪    ♪└|∵|┐♪",
    "e9": "ಥ‿ಥ",
    "e10": "(༎ຶ ෴ ༎ຶ)",
    "e11": "(----_____----)",
    "e12": "(٥↼_↼)",
    "e13": "(-_-メ)",
    "e14": "(๑•﹏•)",
    "e15": "´◔‿ゝ◔`)━☞",
    "e16": "←(-_-メ)",
}

active_emotion = {"key": None, "position": None}

def apply_emotion(text):
    if active_emotion["key"] is None:
        return text
    emo = EMOTIONS[active_emotion["key"]]
    pos = active_emotion["position"]
    if pos == "L":
        return f"{emo} {text}"
    if pos == "R":
        return f"{text} {emo}"
    if pos == "LR":
        return f"{emo} {text} {emo}"
    return text

COMMAND_PREFIXES = ("/select", "/font_list", "/ping", "/auto_reply",
                     "/savage_reply", "/save_message", "/complete_message",
                     "/current_reply_on", "/off_auto_reply_by_num",
                     "/off_savage_reply_by_num", "/command_list",
                     "/fire_all", "/clear_savage", "/s_e", "/dt",
                     "/approve_request")
