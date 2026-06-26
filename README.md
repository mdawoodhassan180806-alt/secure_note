# Secure Notes

An encrypted, password-protected notes manager with **two interfaces
sharing the same security code**:
- **GUI** (Tkinter) — point-and-click desktop window
- **CLI** (terminal) — menu-driven, works over SSH with no display needed

All notes are AES-encrypted; the master password is never stored, only
its hash.

## How the security works
- **Master password**: only a salted PBKDF2-HMAC-SHA256 hash (390,000
  iterations) is stored, in `~/.secure_notes/auth.json`. The raw
  password is never written to disk.
- **Encryption key**: derived from the master password with PBKDF2
  using a *separate* salt, so the login-check hash can never double
  as the encryption key.
- **Note encryption**: AES (via Fernet — AES-128-CBC + HMAC-SHA256),
  authenticated, so tampered ciphertext is rejected instead of
  silently decrypted to garbage.
- File permissions on `~/.secure_notes/` and its contents are set to
  `0700`/`0600` (owner-only) on creation.

## Files
- `core.py` — shared encryption/auth/storage logic (used by both interfaces)
- `secure_notes_gui.py` — GUI front-end (Tkinter)
- `secure_notes_cli.py` — CLI front-end (terminal menu)
- `secure_notes.py` — launcher: runs GUI by default, `--cli` for CLI
- `requirements.txt` — Python dependency (just `cryptography`)

## Run on Kali Linux — step by step

1. **Open a terminal** and confirm Python 3 is present (Kali ships
   with it by default):
   ```bash
   python3 --version
   ```

2. **Install Tkinter** — only needed for GUI mode; skip this if you
   only plan to use the CLI:
   ```bash
   sudo apt update
   sudo apt install -y python3-tk
   ```

3. **Unzip / copy the project** to a folder, e.g.:
   ```bash
   mkdir -p ~/secure_notes && cd ~/secure_notes
   # place core.py, secure_notes.py, secure_notes_gui.py,
   # secure_notes_cli.py, and requirements.txt here
   ```

4. **Check the dependency**: Kali's system Python often already has
   `cryptography` preinstalled (`/usr/lib/python3/dist-packages`). Check
   first before bothering with a venv:
   ```bash
   pip install -r requirements.txt
   ```
   If you see `Requirement already satisfied: cryptography...`, you're
   done — skip straight to step 5.

   If it's genuinely missing and pip refuses with an "externally
   managed environment" error (common on Kali/Debian), install it
   system-wide with:
   ```bash
   pip install -r requirements.txt --break-system-packages
   ```

   > **Note on virtual environments:** `python3 -m venv venv` can fail
   > on Kali with an `ensurepip is not available` error, suggesting you
   > install a `python3.11-venv`-style package. That package name often
   > doesn't exist in Kali's repos (Kali may ship a different Python
   > minor version), so this path is a dead end on many Kali installs.
   > Since `cryptography` is usually already present system-wide, a
   > venv isn't necessary for this app — just use the system Python
   > as above.

5. **Run the app:**

   **GUI mode (default):**
   ```bash
   python3 secure_notes.py
   ```
   This opens a Tkinter window. If you're on a remote/SSH session with
   no display, make sure you're either on the physical Kali desktop, a
   VNC/X session, or run with `ssh -X` / `ssh -Y` to forward the
   display. Otherwise you'll get a `no display name and no $DISPLAY
   environment variable` error.

   **CLI mode** (no GUI/display required — works fine over plain SSH):
   ```bash
   python3 secure_notes.py --cli
   ```
   You'll get a numbered menu (List / Add / View / Delete / Exit)
   instead of a window. Password entry is hidden (uses `getpass`).

   You can also call the front-ends directly instead of going through
   the launcher:
   ```bash
   python3 secure_notes_gui.py
   python3 secure_notes_cli.py
   ```

6. **First run** — you'll be asked to create a master password
   (8+ characters). This sets up `~/.secure_notes/auth.json`.

7. **Subsequent runs** — you'll be asked to log in with that
   password. After login you can (same actions in both GUI and CLI):
   - **Add Note** — enter a title + content, it's encrypted and saved.
   - **View** — select a note, decrypt and read it.
   - **Delete** — select a note, permanently remove it.
   - **Logout/Exit** — clears the in-memory key (GUI: "Logout" button
     returns to login screen; CLI: option 5 exits the program). Data
     stays encrypted on disk either way.

## Data location
All data lives in `~/.secure_notes/`:
- `auth.json` — salts + password hash (not the password)
- `notes.json` — note titles (plaintext, for the list view) + AES-encrypted content

To fully reset the app (e.g. forgot the master password — note that
this destroys all notes since there's no recovery path), delete that
folder:
```bash
rm -rf ~/.secure_notes
```

## Notes on the "no password recovery" tradeoff
This is intentional: the encryption key is derived from the master
password and nothing else is stored that could reconstruct it. Adding
password recovery would require either storing the key in a recoverable
form (defeating the purpose) or a separate recovery-key mechanism,
which is out of scope here but is a reasonable extension if you need it
(e.g. generate a one-time recovery code at setup, encrypt the data key
with it as a secondary access path).# secure_note
