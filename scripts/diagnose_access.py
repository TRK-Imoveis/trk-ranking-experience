"""Diagnóstico — tentar variações de Organization.pipes."""
from __future__ import annotations

import sys

from pipefy_auth import gql

sys.stdout.reconfigure(encoding="utf-8")


def try_pipes(label: str, args_str: str) -> None:
    q = f"""
    query {{
      organization(id: "300542579") {{
        pipes({args_str}) {{ id name }}
      }}
    }}
    """
    try:
        d = gql(q)
        pipes = d["organization"]["pipes"] or []
        print(f"[{label}]  pipes({args_str}) → {len(pipes)}")
        for p in pipes[:3]:
            print(f"    - {p['id']}: {p['name']}")
        if len(pipes) > 3:
            print(f"    ... +{len(pipes) - 3} mais")
    except Exception as e:
        print(f"[{label}]  pipes({args_str}) → FAIL: {e}")


def main() -> None:
    try_pipes("default", "")
    try_pipes("publics", "include_publics: true")
    try_pipes("fully_off", "onlyFullyVisible: false")
    try_pipes("perm_read", 'with_permission: "read"')
    try_pipes("perm_any", 'with_permission: "any"')
    try_pipes("combo1", "include_publics: true, onlyFullyVisible: false")
    try_pipes("search_ranking", 'name_search: "ranking"')
    try_pipes("search_trk", 'name_search: "TRK"')


if __name__ == "__main__":
    main()
