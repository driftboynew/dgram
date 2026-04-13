"""
Nokia 216 Telegram Web Client
==============================
A lightweight Telegram client that runs in Opera Mini on Nokia 216.
Built with Flask + Telethon. Optimised for 240px screens, 2G data.

Setup:
  1. Get API_ID and API_HASH from https://my.telegram.org
  2. Set them as environment variables (see README.md)
  3. pip install -r requirements.txt
  4. python app.py
  5. Open http://localhost:5000 in Opera Mini
"""

import os
import io
import html
import threading
import tempfile
from datetime import datetime
from flask import Flask, request, session, redirect, send_file, Response
from telethon.sync import TelegramClient
from telethon.tl.types import DocumentAttributeAudio
from telethon.errors import (
    SessionPasswordNeededError,
    PhoneCodeInvalidError,
    PhoneCodeExpiredError,
    PasswordHashInvalidError,
)
try:
    from gtts import gTTS
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False

# ─── Config ───────────────────────────────────────────────────────────────────

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'nokia-tg-secret-change-me-2026')

API_ID   = int(os.environ.get('API_ID', 0))
API_HASH = os.environ.get('API_HASH', '')
SESSION_NAME = 'nokia_telegram'
PORT = int(os.environ.get('PORT', 5000))

# In-memory dialog cache so we can resolve entity IDs across requests
_dialog_cache = {}   # str(id) -> entity
_client = None
_lock = threading.Lock()

# ─── Telegram client helpers ──────────────────────────────────────────────────

def get_client():
    """Return a connected (but not necessarily authorised) Telethon client."""
    global _client
    with _lock:
        if _client is None:
            _client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
            _client.connect()
        elif not _client.is_connected():
            _client.connect()
    return _client


def is_authed():
    try:
        return get_client().is_user_authorized()
    except Exception:
        return False


def fmt_time(dt):
    """Format a datetime to HH:MM, handling None."""
    if dt is None:
        return ''
    try:
        return dt.strftime('%H:%M')
    except Exception:
        return ''


def fmt_date(dt):
    """Format a datetime to DD Mon HH:MM."""
    if dt is None:
        return ''
    try:
        return dt.strftime('%d %b %H:%M')
    except Exception:
        return ''


def peer_name(entity):
    """Get a display name from any Telegram entity."""
    if entity is None:
        return 'Unknown'
    first = getattr(entity, 'first_name', '') or ''
    last  = getattr(entity, 'last_name',  '') or ''
    title = getattr(entity, 'title',      '') or ''
    name = (first + ' ' + last).strip() or title or 'Unknown'
    return html.escape(name)


def safe_text(msg, limit=80):
    """Safely truncate and escape a message text."""
    if not msg:
        return ''
    t = msg if len(msg) <= limit else msg[:limit] + '...'
    return html.escape(t)

# ─── HTML helpers ─────────────────────────────────────────────────────────────

CSS = """
*{box-sizing:border-box}
body{margin:0;padding:0;background:#000;color:#bbb;font-family:sans-serif;font-size:13px;max-width:240px}
a{display:block;padding:8px 8px;color:#6af;text-decoration:none;border-bottom:1px solid #111}
a:focus,a:active{background:#002040;color:#fff;outline:none}
input,textarea,select{background:#0a0f16;border:1px solid #1a2535;color:#bbb;font-size:12px;padding:5px 6px;width:100%;display:block;margin-top:4px}
textarea{height:60px;resize:none}
input[type=submit],button{width:auto;background:#0060a9;color:#fff;border:none;padding:7px 16px;margin-top:8px;font-size:12px;display:block}
.hdr{background:#001020;padding:5px 8px;border-bottom:2px solid #0060a9}
.hdr b{color:#0090ff;font-size:14px;letter-spacing:2px}
.hdr small{color:#334;font-size:9px;display:block;margin-top:1px}
.nav{background:#000c1a;padding:5px 8px;border-bottom:1px solid #111;font-size:10px}
.nav a{display:inline;padding:0;border:none;color:#556;margin-right:10px}
.err{background:#200800;padding:6px 8px;color:#f66;font-size:11px;border-bottom:1px solid #300}
.ok{background:#002008;padding:6px 8px;color:#0f6;font-size:11px;border-bottom:1px solid #030}
.sec h2{margin:0;padding:4px 6px;background:#001428;color:#0090ff;font-size:11px;border-left:3px solid #0060a9;letter-spacing:1px}
.row{padding:7px 8px;border-bottom:1px solid #0d1318}
.row .name{color:#aac;font-size:12px}
.row .preview{color:#446;font-size:10px;margin-top:2px}
.row .badge{color:#0af;font-size:10px;float:right}
.msg-out{padding:6px 8px;border-bottom:1px solid #0a0f16;background:#001820}
.msg-in{padding:6px 8px;border-bottom:1px solid #0a0f16}
.who{font-size:10px;color:#0090ff;margin-bottom:2px}
.me{font-size:10px;color:#00a860;margin-bottom:2px}
.txt{color:#aaa;font-size:12px;word-break:break-word}
.time{color:#334;font-size:9px;margin-top:3px;text-align:right}
form{padding:8px}
label{display:block;font-size:10px;color:#556;margin-top:10px;margin-bottom:2px}
.ftr{padding:6px 8px;border-top:1px solid #112;font-size:9px;color:#223;text-align:center;margin-top:4px}
.info{padding:6px 8px;font-size:11px;color:#556}
.unread{color:#0af}
"""

def page(title, body, back=None, nav_links=None):
    """Render a full HTML page."""
    back_link = f'<a href="{back}">&#8592; Back</a>&nbsp;' if back else ''
    extra_nav = ''
    if nav_links:
        for label, href in nav_links:
            extra_nav += f'<a href="{href}">{label}</a>&nbsp;'
    nav = ''
    if back_link or extra_nav:
        nav = f'<div class="nav">{back_link}{extra_nav}</div>'

    return f"""<!DOCTYPE html>
<html><head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=240,user-scalable=no"/>
<meta name="HandheldFriendly" content="true"/>
<meta name="MobileOptimized" content="240"/>
<title>{html.escape(title)}</title>
<style>{CSS}</style>
</head><body>
<div class="hdr"><b>NOKIA</b><small>TELEGRAM &#8212; {html.escape(title.upper())}</small></div>
{nav}
{body}
<div class="ftr">NOKIA 216 TELEGRAM CLIENT</div>
</body></html>"""


def error_page(msg, back='/'):
    body = f'<div class="err">&#9888; {html.escape(str(msg))}</div>'
    return page('Error', body, back)

# ─── Routes ───────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    if not is_authed():
        return redirect('/login')
    return redirect('/chats')


# ── Login ──────────────────────────────────────────────────────────────────────

@app.route('/login', methods=['GET', 'POST'])
def login():
    if is_authed():
        return redirect('/chats')

    error = ''
    if request.method == 'POST':
        phone = request.form.get('phone', '').strip()
        if not phone:
            error = 'Please enter your phone number.'
        elif not API_ID or not API_HASH:
            error = 'API_ID / API_HASH not configured. See README.md.'
        else:
            try:
                c = get_client()
                c.send_code_request(phone)
                session['login_phone'] = phone
                return redirect('/verify')
            except Exception as e:
                error = str(e)

    body = f"""
{'<div class="err">'+html.escape(error)+'</div>' if error else ''}
<div class="info">Enter your Telegram phone number to log in.</div>
<form method="post" action="/login">
  <label>Phone number (with country code):</label>
  <input type="tel" name="phone" placeholder="+12345678900" autocomplete="off"/>
  <input type="submit" value="Send Code &#9658;"/>
</form>"""
    return page('Login', body)


@app.route('/verify', methods=['GET', 'POST'])
def verify():
    phone = session.get('login_phone')
    if not phone:
        return redirect('/login')

    error = ''
    need_2fa = session.get('need_2fa', False)

    if request.method == 'POST':
        code = request.form.get('code', '').strip()
        password = request.form.get('password', '').strip()
        c = get_client()

        if need_2fa:
            # 2FA password step
            try:
                c.sign_in(password=password)
                session.pop('need_2fa', None)
                session.pop('login_phone', None)
                return redirect('/chats')
            except PasswordHashInvalidError:
                error = 'Wrong 2FA password. Try again.'
            except Exception as e:
                error = str(e)
        else:
            # OTP code step
            try:
                c.sign_in(phone, code)
                session.pop('login_phone', None)
                return redirect('/chats')
            except SessionPasswordNeededError:
                session['need_2fa'] = True
                session['pending_code'] = code
                need_2fa = True
            except (PhoneCodeInvalidError, PhoneCodeExpiredError):
                error = 'Invalid or expired code. Please try again.'
            except Exception as e:
                error = str(e)

    if need_2fa:
        body = f"""
{'<div class="err">'+html.escape(error)+'</div>' if error else ''}
<div class="info">Your account has Two-Step Verification. Enter your 2FA password:</div>
<form method="post" action="/verify">
  <label>2FA Password:</label>
  <input type="password" name="password" autocomplete="off"/>
  <input type="submit" value="Login &#9658;"/>
</form>"""
    else:
        body = f"""
{'<div class="err">'+html.escape(error)+'</div>' if error else ''}
<div class="info">Code sent to {html.escape(phone)}. Enter it below:</div>
<form method="post" action="/verify">
  <label>Verification Code:</label>
  <input type="number" name="code" placeholder="12345" autocomplete="off"/>
  <input type="submit" value="Verify &#9658;"/>
</form>
<a href="/login">&#8592; Use a different number</a>"""

    return page('Verify', body)


# ── Chat list ──────────────────────────────────────────────────────────────────

@app.route('/chats')
def chats():
    if not is_authed():
        return redirect('/login')

    offset = int(request.args.get('offset', 0))
    limit  = 20

    try:
        c = get_client()
        me = c.get_me()
        dialogs = c.get_dialogs(limit=limit, offset_date=None)
    except Exception as e:
        return error_page(e, '/')

    items = ''
    for d in dialogs:
        try:
            eid = str(d.entity.id)
            _dialog_cache[eid] = d.entity

            name = peer_name(d.entity)
            unread = d.unread_count or 0
            badge = f'<span class="badge">[{unread}]</span>' if unread else ''
            cls = 'unread' if unread else ''

            preview = ''
            if d.message and getattr(d.message, 'message', None):
                preview = safe_text(d.message.message, 45)
            elif d.message:
                preview = '[media]'

            items += f"""<a href="/chat/{eid}">
<div class="row">
  {badge}
  <div class="name {cls}">{name}</div>
  <div class="preview">{preview}</div>
</div>
</a>"""
        except Exception:
            continue

    if not items:
        items = '<div class="info">No chats found.</div>'

    greeting = f'<div class="info">Hello, {peer_name(me)} &#10003;</div>'
    body = f'{greeting}<div class="sec"><h2>CHATS</h2>{items}</div>'
    return page('Chats', body, nav_links=[('Logout', '/logout')])


# ── Single chat ────────────────────────────────────────────────────────────────

@app.route('/chat/<chat_id>')
def chat(chat_id):
    if not is_authed():
        return redirect('/login')

    offset = int(request.args.get('offset', 0))
    limit  = 15

    try:
        c = get_client()
        me = c.get_me()

        # Resolve entity — try cache first, then API
        entity = _dialog_cache.get(chat_id)
        if entity is None:
            try:
                entity = c.get_entity(int(chat_id))
            except Exception:
                return error_page('Chat not found. Go back to chat list.', '/chats')

        messages = c.get_messages(entity, limit=limit, add_offset=offset)
        title = peer_name(entity)

    except Exception as e:
        return error_page(e, '/chats')

    msgs = ''
    for m in reversed(messages):
        if not getattr(m, 'message', None) and not getattr(m, 'media', None):
            continue

        txt = safe_text(getattr(m, 'message', '') or '', 300)
        if not txt:
            # Check if it's a voice/audio message — show download link
            if hasattr(m, 'media') and m.media:
                try:
                    doc = getattr(m.media, 'document', None)
                    if doc:
                        for attr in doc.attributes:
                            if isinstance(attr, DocumentAttributeAudio):
                                dur = attr.duration or 0
                                txt = f'<a href="/voice/{chat_id}/{m.id}">&#9660; Voice ({dur}s) - tap to download</a>'
                                break
                except Exception:
                    pass
            if not txt:
                txt = '<em>[media / sticker]</em>'

        is_me = (m.sender_id == me.id)
        cls = 'msg-out' if is_me else 'msg-in'
        who_cls = 'me' if is_me else 'who'

        if is_me:
            sender_label = 'You'
        elif m.sender:
            sender_label = peer_name(m.sender)
        else:
            sender_label = 'Unknown'

        time_str = fmt_date(m.date)

        msgs += f"""<div class="{cls}">
  <div class="{who_cls}">{sender_label}</div>
  <div class="txt">{txt}</div>
  <div class="time">{time_str}</div>
</div>"""

    if not msgs:
        msgs = '<div class="info">No messages yet.</div>'

    # Older messages link
    older_link = ''
    if len(messages) == limit:
        older_link = f'<a href="/chat/{chat_id}?offset={offset+limit}">&#8593; Older messages</a>'

    # Reply form — text + optional TTS voice
    tts_btn = '<input type="submit" name="action" value="Voice &#9835;"/>' if TTS_AVAILABLE else ''
    form = f"""
<form method="post" action="/chat/{chat_id}/send">
  <label>Message:</label>
  <textarea name="msg" placeholder="Type a message..."></textarea>
  <input type="submit" name="action" value="Send &#9654;"/>
  {tts_btn}
</form>"""

    body = f"""
{older_link}
<div class="sec"><h2>{title}</h2>
{msgs}
</div>
{form}"""

    return page(title, body, back='/chats')


# ── Send message ───────────────────────────────────────────────────────────────

@app.route('/chat/<chat_id>/send', methods=['POST'])
def send_message(chat_id):
    if not is_authed():
        return redirect('/login')

    msg_text = request.form.get('msg', '').strip()
    action   = request.form.get('action', 'Send')
    if not msg_text:
        return redirect(f'/chat/{chat_id}')

    try:
        c = get_client()
        entity = _dialog_cache.get(chat_id)
        if entity is None:
            entity = c.get_entity(int(chat_id))

        if 'Voice' in action and TTS_AVAILABLE:
            # Convert text to speech and send as voice note
            tts = gTTS(text=msg_text, lang='en')
            buf = io.BytesIO()
            tts.write_to_fp(buf)
            buf.seek(0)
            buf.name = 'voice.mp3'
            c.send_file(entity, buf, voice_note=True,
                        attributes=[DocumentAttributeAudio(
                            duration=0, voice=True)])
        else:
            c.send_message(entity, msg_text)

    except Exception as e:
        body = f"""
<div class="err">Failed to send: {html.escape(str(e))}</div>
<a href="/chat/{chat_id}">&#8592; Back to chat</a>"""
        return page('Send Error', body)

    return redirect(f'/chat/{chat_id}')


# ── Download voice/audio message ───────────────────────────────────────────────

@app.route('/voice/<chat_id>/<int:msg_id>')
def download_voice(chat_id, msg_id):
    """Download a voice/audio message as MP3 so Nokia media player can open it."""
    if not is_authed():
        return redirect('/login')
    try:
        c = get_client()
        entity = _dialog_cache.get(chat_id)
        if entity is None:
            entity = c.get_entity(int(chat_id))
        msgs = c.get_messages(entity, ids=msg_id)
        msg  = msgs if not isinstance(msgs, list) else (msgs[0] if msgs else None)
        if msg is None or not msg.media:
            return 'No media', 404
        buf = io.BytesIO()
        c.download_media(msg, file=buf)
        buf.seek(0)
        return Response(buf.read(), mimetype='audio/mpeg',
                        headers={'Content-Disposition': f'attachment; filename="voice_{msg_id}.mp3"'})
    except Exception as e:
        return f'Error: {html.escape(str(e))}', 500


# ── Search ─────────────────────────────────────────────────────────────────────

@app.route('/search', methods=['GET', 'POST'])
def search():
    if not is_authed():
        return redirect('/login')

    results = ''
    query = ''

    if request.method == 'POST':
        query = request.form.get('q', '').strip()
        if query:
            try:
                c = get_client()
                dialogs = c.get_dialogs(limit=100)
                q_lower = query.lower()
                for d in dialogs:
                    name = (getattr(d.entity, 'first_name', '') or '') + \
                           (getattr(d.entity, 'last_name',  '') or '') + \
                           (getattr(d.entity, 'title',      '') or '')
                    if q_lower in name.lower():
                        eid = str(d.entity.id)
                        _dialog_cache[eid] = d.entity
                        results += f'<a href="/chat/{eid}">{peer_name(d.entity)}</a>'
            except Exception as e:
                results = f'<div class="err">{html.escape(str(e))}</div>'

        if not results and query:
            results = '<div class="info">No results found.</div>'

    body = f"""
<form method="post" action="/search">
  <label>Search chats:</label>
  <input type="text" name="q" value="{html.escape(query)}" placeholder="Name or username..."/>
  <input type="submit" value="Search &#9658;"/>
</form>
{results}"""
    return page('Search', body, back='/chats')


# ── Logout ─────────────────────────────────────────────────────────────────────

@app.route('/logout')
def logout():
    global _client
    try:
        if _client and _client.is_connected():
            _client.log_out()
    except Exception:
        pass
    _client = None
    session.clear()
    _dialog_cache.clear()
    body = '<div class="ok">&#10003; Logged out successfully.</div><a href="/login">Login again</a>'
    return page('Logged Out', body)


# ── Status / health check ──────────────────────────────────────────────────────

@app.route('/status')
def status():
    authed = is_authed()
    api_ok = bool(API_ID and API_HASH)
    body = f"""
<div class="info">
  API configured: {'YES &#10003;' if api_ok else 'NO &#10007; - Set API_ID and API_HASH'}<br/>
  Logged in: {'YES &#10003;' if authed else 'NO'}<br/>
  Version: 1.0.0
</div>
<a href="/">Home</a>"""
    return page('Status', body)


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == '__main__':
    if not API_ID or not API_HASH:
        print("\n" + "="*50)
        print("ERROR: API_ID and API_HASH are not set!")
        print("Get them from: https://my.telegram.org")
        print("Then set environment variables:")
        print("  export API_ID=your_api_id")
        print("  export API_HASH=your_api_hash")
        print("="*50 + "\n")
    else:
        print(f"\nNokia 216 Telegram Client starting on port {PORT}...")
        print(f"Open http://localhost:{PORT} in your browser or Opera Mini\n")

    # threaded=False is important — Telethon sync doesn't like multi-threading
    app.run(host='0.0.0.0', port=PORT, threaded=False, debug=False)
