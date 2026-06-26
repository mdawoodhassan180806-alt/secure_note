#!/usr/bin/env python3
"""
Secure Notes — CLI front-end.

Encryption/auth logic lives in core.py and is shared with the GUI
(secure_notes_gui.py) so both interfaces use the identical, audited
security code path.

Run:  python3 secure_notes_cli.py
"""

import getpass
import sys
import time

from cryptography.fernet import Fernet, InvalidToken

from core import AuthStore, NotesStore


def prompt_new_password() -> str:
    while True:
        p1 = getpass.getpass("New master password (min 8 chars): ")
        if len(p1) < 8:
            print("  Too short — use at least 8 characters.\n")
            continue
        p2 = getpass.getpass("Confirm master password: ")
        if p1 != p2:
            print("  Passwords did not match, try again.\n")
            continue
        return p1


def setup_flow(auth: AuthStore):
    print("\nNo master password found — let's create one.")
    print("This password encrypts all your notes and is never stored.")
    print("If you forget it, your notes cannot be recovered.\n")
    password = prompt_new_password()
    auth.set_master_password(password)
    print("\nMaster password created. Please log in.\n")


def login_flow(auth: AuthStore) -> Fernet:
    attempts = 0
    while attempts < 5:
        password = getpass.getpass("Master password: ")
        key = auth.verify_and_get_key(password)
        if key is not None:
            return Fernet(key)
        attempts += 1
        print(f"  Incorrect password. ({5 - attempts} attempts left)\n")
    print("Too many failed attempts. Exiting.")
    sys.exit(1)


def print_menu():
    print("\n--- Secure Notes ---")
    print("1) List notes")
    print("2) Add note")
    print("3) View note")
    print("4) Delete note")
    print("5) Logout / Exit")
    print("--------------------")


def list_notes(notes: NotesStore) -> list:
    items = sorted(notes.list_notes(), key=lambda n: n["created"], reverse=True)
    if not items:
        print("\n(No notes yet.)")
        return items
    print()
    for i, n in enumerate(items, start=1):
        ts = time.strftime("%Y-%m-%d %H:%M", time.localtime(n["created"]))
        print(f"  [{i}] {n['title']}    ({ts})")
    return items


def add_note(fernet: Fernet, notes: NotesStore):
    title = input("Title: ").strip()
    if not title:
        print("  Title cannot be empty.")
        return
    print("Content (end with a single line containing only: END)")
    lines = []
    while True:
        line = input()
        if line.strip() == "END":
            break
        lines.append(line)
    content = "\n".join(lines).strip()
    if not content:
        print("  Content cannot be empty — note not saved.")
        return
    notes.add_note(fernet, title, content)
    print("  Note encrypted and saved.")


def pick_note(notes: NotesStore):
    items = list_notes(notes)
    if not items:
        return None
    choice = input("Enter note number: ").strip()
    if not choice.isdigit() or not (1 <= int(choice) <= len(items)):
        print("  Invalid selection.")
        return None
    return items[int(choice) - 1]


def view_note(fernet: Fernet, notes: NotesStore):
    selected = pick_note(notes)
    if not selected:
        return
    try:
        content = notes.get_note(fernet, selected["id"])
    except InvalidToken:
        print("  Decryption failed (data may be corrupted).")
        return
    print(f"\n----- {selected['title']} -----")
    print(content)
    print("-" * (12 + len(selected["title"])))


def delete_note(notes: NotesStore):
    selected = pick_note(notes)
    if not selected:
        return
    confirm = input(f"Delete '{selected['title']}'? Type 'yes' to confirm: ").strip().lower()
    if confirm == "yes":
        notes.delete_note(selected["id"])
        print("  Note deleted.")
    else:
        print("  Cancelled.")


def main():
    auth = AuthStore()
    notes = NotesStore()

    if not auth.is_initialized():
        setup_flow(auth)

    fernet = login_flow(auth)
    print("\nUnlocked. Welcome back.")

    while True:
        print_menu()
        choice = input("Choose an option: ").strip()
        if choice == "1":
            list_notes(notes)
        elif choice == "2":
            add_note(fernet, notes)
        elif choice == "3":
            view_note(fernet, notes)
        elif choice == "4":
            delete_note(notes)
        elif choice == "5":
            print("Goodbye.")
            break
        else:
            print("  Invalid option.")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nExiting.")
