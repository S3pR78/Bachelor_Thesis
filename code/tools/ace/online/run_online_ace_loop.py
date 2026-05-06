"""Thin CLI wrapper for the online ACE loop."""

from __future__ import annotations

from src.ace.online.cli import build_parser, execute_online_ace


def main() -> int:
    try:
        return execute_online_ace(build_parser().parse_args())
    except NotImplementedError as exc:
        print(str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
