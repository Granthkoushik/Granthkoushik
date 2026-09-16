import json
import os
import secrets
import subprocess
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

HOST = "127.0.0.1"
PORT = 8765
TOKEN_FILE = Path.home() / ".avatar_agent_token"


def get_token():
    if TOKEN_FILE.exists():
        token = TOKEN_FILE.read_text(encoding="utf-8").strip()
        if token:
            return token
    token = secrets.token_urlsafe(24)
    TOKEN_FILE.write_text(token, encoding="utf-8")
    return token

TOKEN = get_token()


def launch_target(target: str):
    t = target.strip()
    low = t.lower()
    apps = {
        "notepad": "notepad.exe",
        "calculator": "calc.exe",
        "paint": "mspaint.exe",
        "explorer": "explorer.exe",
        "vscode": "code.exe",
        "vs code": "code.exe",
        "chrome": "chrome.exe",
        "edge": "msedge.exe",
        "thonn y": "thonny.exe",
        "thonny": "thonny.exe",
        "terminal": "wt.exe",
        "powershell": "powershell.exe",
    }
    if low in apps:
        subprocess.Popen([apps[low]], shell=False)
        return f"Opened {t}."
    if low.startswith(("http://", "https://")):
        webbrowser.open(t)
        return f"Opened {t}."
    p = Path(os.path.expandvars(os.path.expanduser(t))).resolve()
    if p.exists():
        os.startfile(str(p))
        return f"Opened {p}."
    raise ValueError("Target was not found. Use an allowed app name, URL, or existing path.")


def run_command(text: str, confirmed: bool = False):
    q = text.strip()
    low = q.lower()
    if not q:
        raise ValueError("Empty command.")

    # Safe, explicit actions.
    if low.startswith("open "):
        return {"ok": True, "message": launch_target(q[5:])}
    if low in {"open github", "github"}:
        return {"ok": True, "message": launch_target("https://github.com/Granthkoushik")}
    if low in {"open linkedin", "linkedin"}:
        return {"ok": True, "message": launch_target("https://www.linkedin.com/in/granth-koushik-7bb5ba37b")}
    if low in {"list files", "list current folder", "show files"}:
        items = [p.name for p in Path.cwd().iterdir()]
        return {"ok": True, "message": "Current folder: " + str(Path.cwd()), "items": items[:100]}
    if low in {"lock", "lock computer", "lock pc", "lock laptop"}:
        if not confirmed:
            return {"ok": False, "needs_confirmation": True, "message": "Locking the computer requires confirmation."}
        subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"], check=False)
        return {"ok": True, "message": "Computer locked."}

    # Arbitrary shell is deliberately gated behind an explicit confirmation.
    if low.startswith("run "):
        command = q[4:].strip()
        if not confirmed:
            return {"ok": False, "needs_confirmation": True, "message": "Running a terminal command requires confirmation.", "command": command}
        completed = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=60)
        return {"ok": True, "message": "Command finished.", "returncode": completed.returncode, "stdout": completed.stdout[-8000:], "stderr": completed.stderr[-8000:]}

    return {"ok": False, "message": "I can currently execute: open <app/url/path>, list files, lock computer, or run <command> with confirmation."}


class Handler(BaseHTTPRequestHandler):
    def _headers(self, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Avatar-Token")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def _json(self, payload, status=200):
        self._headers(status)
        self.wfile.write(json.dumps(payload).encode("utf-8"))

    def _authorized(self):
        return secrets.compare_digest(self.headers.get("X-Avatar-Token", ""), TOKEN)

    def do_OPTIONS(self):
        self._headers(204)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/status":
            self._json({"ok": True, "agent": "Avatar Local Agent", "version": "0.1", "host": HOST, "port": PORT})
            return
        self._json({"ok": False, "message": "Avatar agent is running."}, 404)

    def do_POST(self):
        path = urlparse(self.path).path
        if not self._authorized():
            self._json({"ok": False, "message": "Unauthorized. Enter the local Avatar token."}, 401)
            return
        length = int(self.headers.get("Content-Length", "0"))
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            self._json({"ok": False, "message": "Invalid JSON."}, 400)
            return
        if path == "/command":
            try:
                result = run_command(body.get("text", ""), bool(body.get("confirmed", False)))
                self._json(result, 200 if result.get("ok") else 400)
            except Exception as exc:
                self._json({"ok": False, "message": str(exc)}, 400)
            return
        self._json({"ok": False, "message": "Unknown endpoint."}, 404)

    def log_message(self, fmt, *args):
        print("[Avatar] " + fmt % args)


if __name__ == "__main__":
    print("\n=== AVATAR LOCAL AGENT ===")
    print(f"Listening only on http://{HOST}:{PORT}")
    print("Local token (paste this into the public Avatar page):")
    print(TOKEN)
    print("Press Ctrl+C to stop.\n")
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nAvatar agent stopped.")
        server.shutdown()
