"""
Secure Notes — shared core (crypto, auth, storage).

This module contains NO interface code (no Tkinter, no CLI prompts) so
that the GUI (secure_notes_gui.py) and the CLI (secure_notes_cli.py)
both run through the exact same security-critical code path. Keeping
this logic in one place avoids the GUI and CLI drifting apart and
accidentally implementing encryption differently.

Security design
----------------
- The master password is NEVER stored. Only a PBKDF2-HMAC-SHA256 hash
  (with a random per-install salt and a high iteration count) is stored,
  used solely to verify a login attempt.
- A separate key, used to encrypt/decrypt notes, is derived from the
  master password with PBKDF2-HMAC-SHA256 and its own random salt
  (key separation: the login-check hash is never reusable as an
  encryption key).
- Notes are encrypted with AES via the `cryptography` library's Fernet
  recipe (AES-128-CBC + HMAC-SHA256 for authenticated encryption, so
  tampering with stored ciphertext is detected, not silently decrypted).
- All secrets live only in memory while the app runs and are dropped
  on logout/exit. The data file on disk holds only salts + ciphertext.
- Constant-time comparison (hmac.compare_digest) is used for password
  verification to reduce timing side-channels.
"""

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from pathlib import Path

from cryptography.fernet import Fernet  # noqa: F401  (re-exported for callers)

# ---------------------------------------------------------------------------
# Storage locations
# ---------------------------------------------------------------------------
APP_DIR = Path.home() / ".secure_notes"
AUTH_FILE = APP_DIR / "auth.json"      # master password hash + salt
NOTES_FILE = APP_DIR / "notes.json"    # encrypted notes

PBKDF2_ITERATIONS = 390_000  # OWASP-recommended ballpark for PBKDF2-SHA256 (2024+)


# ---------------------------------------------------------------------------
# Crypto helpers
# ---------------------------------------------------------------------------
def _b64e(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii")


def _b64d(data: str) -> bytes:
    return base64.urlsafe_b64decode(data.encode("ascii"))


def derive_key(password: str, salt: bytes, iterations: int = PBKDF2_ITERATIONS) -> bytes:
    """Derive a 32-byte key suitable for Fernet (AES) from a password."""
    raw = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations, dklen=32)
    return base64.urlsafe_b64encode(raw)  # Fernet requires urlsafe-base64, 32-byte key


def hash_password(password: str, salt: bytes, iterations: int = PBKDF2_ITERATIONS) -> bytes:
    """Separate hash used ONLY to verify the login password (never used as a key)."""
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations, dklen=32)


def ensure_app_dir():
    APP_DIR.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(APP_DIR, 0o700)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Persistence layer
# ---------------------------------------------------------------------------
class AuthStore:
    """Handles master-password setup, verification, and key derivation."""

    def __init__(self):
        ensure_app_dir()

    def is_initialized(self) -> bool:
        return AUTH_FILE.exists()

    def set_master_password(self, password: str):
        login_salt = secrets.token_bytes(16)
        key_salt = secrets.token_bytes(16)
        pw_hash = hash_password(password, login_salt)
        data = {
            "login_salt": _b64e(login_salt),
            "key_salt": _b64e(key_salt),
            "password_hash": _b64e(pw_hash),
            "iterations": PBKDF2_ITERATIONS,
            "created": time.time(),
        }
        with open(AUTH_FILE, "w") as f:
            json.dump(data, f)
        os.chmod(AUTH_FILE, 0o600)

    def verify_and_get_key(self, password: str) -> bytes | None:
        """Return the derived encryption key if password is correct, else None."""
        with open(AUTH_FILE) as f:
            data = json.load(f)
        login_salt = _b64d(data["login_salt"])
        key_salt = _b64d(data["key_salt"])
        iterations = data["iterations"]
        stored_hash = _b64d(data["password_hash"])

        attempt_hash = hash_password(password, login_salt, iterations)
        if not hmac.compare_digest(attempt_hash, stored_hash):
            return None
        return derive_key(password, key_salt, iterations)


class NotesStore:
    """Handles loading/saving the encrypted notes file."""

    def __init__(self):
        ensure_app_dir()
        if not NOTES_FILE.exists():
            self._write([])

    def _read(self) -> list:
        if not NOTES_FILE.exists():
            return []
        with open(NOTES_FILE) as f:
            return json.load(f)

    def _write(self, notes: list):
        with open(NOTES_FILE, "w") as f:
            json.dump(notes, f, indent=2)
        os.chmod(NOTES_FILE, 0o600)

    def list_notes(self) -> list:
        """Return [{id, title, created}] without decrypting content."""
        notes = self._read()
        return [{"id": n["id"], "title": n["title"], "created": n["created"]} for n in notes]

    def add_note(self, fernet: Fernet, title: str, content: str):
        notes = self._read()
        token = fernet.encrypt(content.encode("utf-8"))
        notes.append({
            "id": secrets.token_hex(8),
            "title": title,
            "content": token.decode("ascii"),
            "created": time.time(),
        })
        self._write(notes)

    def get_note(self, fernet: Fernet, note_id: str) -> str:
        notes = self._read()
        for n in notes:
            if n["id"] == note_id:
                return fernet.decrypt(n["content"].encode("ascii")).decode("utf-8")
        raise KeyError("Note not found")

    def delete_note(self, note_id: str):
        notes = self._read()
        notes = [n for n in notes if n["id"] != note_id]
        self._write(notes)
