#!/usr/bin/env python3
"""CLI for the read-only OneDrive documentary source connector."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from tools.onedrive_source import (
    complete_device_login,
    connection_status,
    disconnect,
    download_item,
    get_item,
    import_proxy,
    list_children,
    search_items,
    start_device_login,
)


def _emit(payload: Any) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True, default=str))


def _login(_: argparse.Namespace) -> int:
    flow = start_device_login()
    print(
        flow.get("message")
        or f"Open {flow['verification_uri']} and enter code {flow['user_code']}."
    )
    result = complete_device_login(
        flow["device_code"],
        interval=int(flow.get("interval", 5)),
        expires_in=int(flow.get("expires_in", 900)),
    )
    _emit(result)
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="onedrive-footage",
        description=(
            "Read-only OneDrive source connector for YAPPY-CLIPZ. "
            "Downloads protected working copies; never edits OneDrive originals."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    login = sub.add_parser("login", help="Sign in with Microsoft device code")
    login.set_defaults(func=_login)

    status = sub.add_parser("status", help="Show sanitized connection status")
    status.set_defaults(func=lambda _: (_emit(connection_status()), 0)[1])

    listing = sub.add_parser("list", help="List root or folder children")
    listing.add_argument("--item-id")
    listing.add_argument("--media-only", action="store_true")
    listing.add_argument("--max-items", type=int, default=200)
    listing.set_defaults(
        func=lambda args: (
            _emit(
                list_children(
                    args.item_id,
                    media_only=args.media_only,
                    max_items=args.max_items,
                )
            ),
            0,
        )[1]
    )

    search = sub.add_parser("search", help="Search OneDrive metadata")
    search.add_argument("query")
    search.add_argument("--all-items", action="store_true")
    search.add_argument("--max-items", type=int, default=200)
    search.set_defaults(
        func=lambda args: (
            _emit(
                search_items(
                    args.query,
                    media_only=not args.all_items,
                    max_items=args.max_items,
                )
            ),
            0,
        )[1]
    )

    metadata = sub.add_parser("metadata", help="Fetch one DriveItem")
    metadata.add_argument("item_id")
    metadata.set_defaults(func=lambda args: (_emit(get_item(args.item_id)), 0)[1])

    download = sub.add_parser(
        "download",
        help="Download one immutable working copy into a bounded workspace",
    )
    download.add_argument("item_id")
    download.add_argument("--workspace", required=True)
    download.set_defaults(
        func=lambda args: (_emit(download_item(args.item_id, args.workspace)), 0)[1]
    )

    proxy = sub.add_parser(
        "import-proxy",
        help="Download a source copy and create an editable proxy with FFmpeg",
    )
    proxy.add_argument("item_id")
    proxy.add_argument("--workspace", required=True)
    proxy.add_argument("--height", type=int, default=720)
    proxy.set_defaults(
        func=lambda args: (
            _emit(import_proxy(args.item_id, args.workspace, height=args.height)),
            0,
        )[1]
    )

    logout = sub.add_parser(
        "logout",
        help="Remove only the local OAuth token cache; never changes OneDrive",
    )
    logout.set_defaults(func=lambda _: (_emit(disconnect()), 0)[1])

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except Exception as exc:
        _emit({"ok": False, "error": str(exc)})
        return 1


if __name__ == "__main__":
    sys.exit(main())
