#!/usr/bin/env python3
"""
Secure Notes — launcher.

Runs the GUI by default. Use --cli to run the terminal interface instead.

  python3 secure_notes.py            # GUI (Tkinter)
  python3 secure_notes.py --cli      # CLI (terminal)
  python3 secure_notes.py -c         # CLI (short flag)

You can also run the front-ends directly:
  python3 secure_notes_gui.py
  python3 secure_notes_cli.py

Both front-ends share the same encryption/auth code in core.py.
"""

import sys


def main():
    if "--cli" in sys.argv or "-c" in sys.argv:
        from secure_notes_cli import main as cli_main
        cli_main()
    else:
        from secure_notes_gui import SecureNotesApp
        SecureNotesApp().mainloop()


if __name__ == "__main__":
    main()
