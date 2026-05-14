"""
Introspecta Card, PhasesHistory e o resolver cards() da Pipe.
Também busca 1 card real do Contestações para validar o shape.
"""
from __future__ import annotations

import json
import sys

from pipefy_auth import gql

sys.stdout.reconfigure(encoding="utf-8")


def list_fields(type_name: str) -> None:
    q = """
    query($t: String!) {
      __type(name: $t) {
        name
        fields {
          name
          args { name type { name kind ofType { name kind } } }
          type { name kind ofType { name kind ofType { name kind } } }
        }
      }
    }
    """
    data = gql(q, {"t": type_name})
    t = data["__type"]
    if not t:
        print(f"[{type_name}] tipo não existe")
        return
    print(f"\n=== {t['name']} ===")
    for f in t["fields"]:
        ft = f["type"]
        tname = ft.get("name") or (ft.get("ofType") or {}).get("name") or ft.get("kind")
        args = ", ".join(f"{a['name']}" for a in (f["args"] or []))
        if args:
            print(f"  {f['name']}({args}) : {tname}")
        else:
            print(f"  {f['name']} : {tname}")


def main() -> None:
    for t in ["Card", "PhaseDetail", "CardField", "CardConnection", "CardEdge", "PageInfo", "Phase"]:
        list_fields(t)

    # Provar campo `cards` da Pipe
    print("\n=== Pipe.cards args ===")
    q = """query { __type(name: "Pipe") { fields { name args { name type { name kind ofType { name kind } } } } } }"""
    data = gql(q)
    for f in data["__type"]["fields"]:
        if f["name"] in ("cards", "allCards", "cardsByQuery"):
            args = [(a["name"], (a["type"].get("name") or (a["type"].get("ofType") or {}).get("name") or a["type"].get("kind"))) for a in (f["args"] or [])]
            print(f"  {f['name']}{args}")


if __name__ == "__main__":
    main()
