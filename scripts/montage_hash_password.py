#!/usr/bin/env python3
"""Generate a scrypt password hash for Montage owner authentication."""

from __future__ import annotations

import getpass
import hashlib
import secrets


def main() -> None:
    password = getpass.getpass("Montage owner password: ")
    confirm = getpass.getpass("Confirm password: ")
    if not password or password != confirm:
        raise SystemExit("Passwords did not match or were empty.")
    salt = secrets.token_hex(16)
    derived = hashlib.scrypt(password.encode(), salt=salt.encode(), n=16384, r=8, p=1, dklen=64)
    print(f"scrypt:{salt}:{derived.hex()}")


if __name__ == "__main__":
    main()
