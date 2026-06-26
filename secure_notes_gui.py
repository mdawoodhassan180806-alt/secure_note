#!/usr/bin/env python3
"""
Secure Notes — GUI (Tkinter) front-end.

Encryption/auth logic lives in core.py and is shared with the CLI
(secure_notes_cli.py) so both interfaces use the identical, audited
security code path.

Run:  python3 secure_notes_gui.py
"""

import time
import tkinter as tk
from tkinter import ttk, messagebox

from cryptography.fernet import Fernet, InvalidToken

from core import AuthStore, NotesStore


class SecureNotesApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Secure Notes")
        self.geometry("520x460")
        self.resizable(False, False)

        self.auth = AuthStore()
        self.notes = NotesStore()
        self.fernet: Fernet | None = None  # set after successful login

        self._build_container()
        if self.auth.is_initialized():
            self.show_login_screen()
        else:
            self.show_setup_screen()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_container(self):
        self.container = ttk.Frame(self, padding=20)
        self.container.pack(fill="both", expand=True)

    def _clear_container(self):
        for widget in self.container.winfo_children():
            widget.destroy()

    # ---- Setup (first run) -------------------------------------------------
    def show_setup_screen(self):
        self._clear_container()
        ttk.Label(self.container, text="Create Master Password", font=("Helvetica", 16, "bold")).pack(pady=(0, 15))
        ttk.Label(self.container, text="This password encrypts all your notes.\n"
                                        "It is not stored anywhere — if you forget it,\n"
                                        "your notes cannot be recovered.",
                  justify="center", foreground="#555").pack(pady=(0, 20))

        ttk.Label(self.container, text="Password:").pack(anchor="w")
        pw1 = ttk.Entry(self.container, show="*")
        pw1.pack(fill="x", pady=(0, 10))

        ttk.Label(self.container, text="Confirm Password:").pack(anchor="w")
        pw2 = ttk.Entry(self.container, show="*")
        pw2.pack(fill="x", pady=(0, 20))

        def submit():
            p1, p2 = pw1.get(), pw2.get()
            if len(p1) < 8:
                messagebox.showerror("Weak Password", "Use at least 8 characters.")
                return
            if p1 != p2:
                messagebox.showerror("Mismatch", "Passwords do not match.")
                return
            self.auth.set_master_password(p1)
            messagebox.showinfo("Success", "Master password set. Please log in.")
            self.show_login_screen()

        ttk.Button(self.container, text="Create Account", command=submit).pack(fill="x")
        pw1.focus()
        self.bind("<Return>", lambda e: submit())

    # ---- Login ---------------------------------------------------------------
    def show_login_screen(self):
        self._clear_container()
        self.fernet = None
        ttk.Label(self.container, text="Secure Notes — Login", font=("Helvetica", 16, "bold")).pack(pady=(0, 25))

        ttk.Label(self.container, text="Master Password:").pack(anchor="w")
        pw = ttk.Entry(self.container, show="*")
        pw.pack(fill="x", pady=(0, 20))

        status = ttk.Label(self.container, text="", foreground="red")
        status.pack()

        def submit():
            key = self.auth.verify_and_get_key(pw.get())
            if key is None:
                status.config(text="Incorrect password.")
                pw.delete(0, "end")
                return
            self.fernet = Fernet(key)
            self.show_main_screen()

        ttk.Button(self.container, text="Unlock", command=submit).pack(fill="x")
        pw.focus()
        self.bind("<Return>", lambda e: submit())

    # ---- Main notes screen -----------------------------------------------
    def show_main_screen(self):
        self._clear_container()
        self.unbind("<Return>")

        top = ttk.Frame(self.container)
        top.pack(fill="x", pady=(0, 10))
        ttk.Label(top, text="Your Notes", font=("Helvetica", 16, "bold")).pack(side="left")
        ttk.Button(top, text="Logout", command=self.logout).pack(side="right")

        self.listbox = tk.Listbox(self.container, height=14)
        self.listbox.pack(fill="both", expand=True, pady=(0, 10))
        self.listbox.bind("<<ListboxSelect>>", lambda e: self._update_buttons())

        btns = ttk.Frame(self.container)
        btns.pack(fill="x")
        ttk.Button(btns, text="Add Note", command=self.add_note_dialog).pack(side="left", expand=True, fill="x", padx=2)
        self.view_btn = ttk.Button(btns, text="View", command=self.view_selected_note, state="disabled")
        self.view_btn.pack(side="left", expand=True, fill="x", padx=2)
        self.del_btn = ttk.Button(btns, text="Delete", command=self.delete_selected_note, state="disabled")
        self.del_btn.pack(side="left", expand=True, fill="x", padx=2)

        self._refresh_list()

    def _refresh_list(self):
        self.listbox.delete(0, "end")
        self._note_ids = []
        for note in sorted(self.notes.list_notes(), key=lambda n: n["created"], reverse=True):
            ts = time.strftime("%Y-%m-%d %H:%M", time.localtime(note["created"]))
            self.listbox.insert("end", f"{note['title']}    ({ts})")
            self._note_ids.append(note["id"])
        self._update_buttons()

    def _update_buttons(self):
        has_sel = bool(self.listbox.curselection())
        state = "normal" if has_sel else "disabled"
        self.view_btn.config(state=state)
        self.del_btn.config(state=state)

    def _selected_id(self):
        sel = self.listbox.curselection()
        if not sel:
            return None
        return self._note_ids[sel[0]]

    def add_note_dialog(self):
        win = tk.Toplevel(self)
        win.title("New Note")
        win.geometry("420x380")
        win.grab_set()

        ttk.Label(win, text="Title:").pack(anchor="w", padx=10, pady=(10, 0))
        title_entry = ttk.Entry(win)
        title_entry.pack(fill="x", padx=10)

        ttk.Label(win, text="Content:").pack(anchor="w", padx=10, pady=(10, 0))
        body = tk.Text(win, height=12, wrap="word")
        body.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        def save():
            title = title_entry.get().strip()
            content = body.get("1.0", "end").strip()
            if not title or not content:
                messagebox.showerror("Missing Info", "Title and content are required.", parent=win)
                return
            self.notes.add_note(self.fernet, title, content)
            win.destroy()
            self._refresh_list()

        ttk.Button(win, text="Save (Encrypt & Store)", command=save).pack(fill="x", padx=10, pady=(0, 10))
        title_entry.focus()

    def view_selected_note(self):
        note_id = self._selected_id()
        if not note_id:
            return
        try:
            content = self.notes.get_note(self.fernet, note_id)
        except InvalidToken:
            messagebox.showerror("Decryption Failed", "Could not decrypt this note (data may be corrupted).")
            return

        win = tk.Toplevel(self)
        win.title("View Note")
        win.geometry("420x380")
        text = tk.Text(win, wrap="word")
        text.insert("1.0", content)
        text.config(state="disabled")
        text.pack(fill="both", expand=True, padx=10, pady=10)

    def delete_selected_note(self):
        note_id = self._selected_id()
        if not note_id:
            return
        if messagebox.askyesno("Confirm Delete", "Permanently delete this note?"):
            self.notes.delete_note(note_id)
            self._refresh_list()

    def logout(self):
        self.fernet = None
        self.show_login_screen()

    def _on_close(self):
        self.fernet = None
        self.destroy()


if __name__ == "__main__":
    SecureNotesApp().mainloop()
