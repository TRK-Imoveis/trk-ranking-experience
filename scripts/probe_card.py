"""Probe — inspecionar CardSearch (singular) e tentar fetch done."""
from __future__ import annotations

import json
import sys

from pipefy_auth import gql

sys.stdout.reconfigure(encoding="utf-8")


def main() -> None:
    print("=== Campos do CardSearch ===")
    q = """query { __type(name: "CardSearch") { inputFields { name type { name kind ofType { name kind ofType { name kind } } } } } }"""
    d = gql(q)
    t = d["__type"]
    for f in t["inputFields"]:
        tt = f["type"]
        tname = tt.get("name") or (tt.get("ofType") or {}).get("name") or tt.get("kind")
        print(f"  {f['name']}: {tname}")

    # Tentar variações com base nos campos reais
    print("\n=== Tentando cards(search:{...}) em fase Concluído ===")
    phase_id = "311416149"
    sample_args = [
        'search: {filter: {ids: []}}',
        'search: {term: ""}',
        'search: {includeDone: true}',
        'search: {done: true}',
        'search: {filterBy: {done: true}}',
    ]
    for s in sample_args:
        q = f'query {{ phase(id: "{phase_id}") {{ cards(first: 1, {s}) {{ edges {{ node {{ id title }} }} }} }} }}'
        try:
            data = gql(q)
            edges = data["phase"]["cards"]["edges"]
            print(f"  [{s}]  edges={len(edges)}")
        except Exception as e:
            print(f"  [{s}]  FAIL: {str(e)[:180]}")


if __name__ == "__main__":
    main()
