#!/usr/bin/env python3
"""Thin CLI adapter over the shared YAPPY-CLIPZ OneDrive action service."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from yappy_clipz.actions import ActionContext
from yappy_clipz.factory import create_runtime


def _emit(payload: Any) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True, default=str))


def _context(runtime) -> ActionContext:
    return ActionContext(actor_id="cli", scopes=tuple(runtime.auth.DEFAULT_SCOPES))


def _dispatch(action_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    runtime = create_runtime()
    return runtime.dispatcher.dispatch(action_id, payload, context=_context(runtime))


def _login(_: argparse.Namespace) -> int:
    start = _dispatch("source.onedrive.login.start", {})["result"]
    print(
        start.get("message")
        or f"Open {start['verificationUri']} and enter code {start['userCode']}."
    )
    result = _dispatch(
        "source.onedrive.login.complete",
        {"flowId": start["flowId"]},
    )
    _emit(result)
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="onedrive-footage",
        description=(
            "Read-only OneDrive source connector for YAPPY-CLIPZ. "
            "Every operation routes through the shared application action service."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    login = sub.add_parser("login", help="Sign in with Microsoft device code")
    login.set_defaults(func=_login)

    status = sub.add_parser("status", help="Show sanitized connection status")
    status.set_defaults(func=lambda _: (_emit(_dispatch("source.onedrive.status", {})), 0)[1])

    listing = sub.add_parser("list", help="List root or folder children")
    listing.add_argument("--item-id")
    listing.add_argument("--media-only", action="store_true")
    listing.add_argument("--max-items", type=int, default=200)
    listing.set_defaults(
        func=lambda args: (
            _emit(
                _dispatch(
                    "source.onedrive.list",
                    {
                        "itemId": args.item_id,
                        "mediaOnly": args.media_only,
                        "maxItems": args.max_items,
                    },
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
                _dispatch(
                    "source.onedrive.search",
                    {
                        "query": args.query,
                        "mediaOnly": not args.all_items,
                        "maxItems": args.max_items,
                    },
                )
            ),
            0,
        )[1]
    )

    metadata = sub.add_parser("metadata", help="Fetch one DriveItem")
    metadata.add_argument("item_id")
    metadata.set_defaults(
        func=lambda args: (
            _emit(_dispatch("source.onedrive.metadata", {"itemId": args.item_id})),
            0,
        )[1]
    )

    download = sub.add_parser(
        "download",
        help="Download one immutable working copy into a bounded workspace",
    )
    download.add_argument("item_id")
    download.add_argument("--workspace", required=True, type=Path)
    download.set_defaults(
        func=lambda args: (
            _emit(
                _dispatch(
                    "source.onedrive.download",
                    {"itemId": args.item_id, "workspace": str(args.workspace)},
                )
            ),
            0,
        )[1]
    )

    proxy = sub.add_parser(
        "import-proxy",
        help="Download a source copy and create an editable proxy with FFmpeg",
    )
    proxy.add_argument("item_id")
    proxy.add_argument("--workspace", required=True, type=Path)
    proxy.add_argument("--height", type=int, default=720)
    proxy.set_defaults(
        func=lambda args: (
            _emit(
                _dispatch(
                    "source.onedrive.import-proxy",
                    {
                        "itemId": args.item_id,
                        "workspace": str(args.workspace),
                        "height": args.height,
                    },
                )
            ),
            0,
        )[1]
    )

    logout = sub.add_parser(
        "logout",
        help="Remove only local OAuth state; never changes OneDrive",
    )
    logout.set_defaults(
        func=lambda _: (_emit(_dispatch("source.onedrive.disconnect", {})), 0)[1]
    )

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
