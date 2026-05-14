"""
Lista pipes visíveis pela SA. Usa include_publics:true para alcançar
todos os pipes públicos da org. Pipes privados exigem membership explícita.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from pipefy_auth import gql

sys.stdout.reconfigure(encoding="utf-8")

OUT = Path(__file__).resolve().parent.parent / "config" / "_raw_pipes.json"

QUERY = """
query {
  organization(id: "300542579") {
    id
    name
    pipesCount
    pipes(include_publics: true) {
      id
      name
      uuid
      public
    }
  }
}
"""


def main() -> None:
    print("[pipes] consultando organization.pipes(include_publics: true)…")
    data = gql(QUERY)
    org = data["organization"]
    pipes = org["pipes"] or []
    print(f"[pipes] org={org['name']}  pipesCount={org['pipesCount']}  visíveis para SA={len(pipes)}")
    print(f"[pipes] privados (não visíveis): {org['pipesCount'] - len(pipes)}\n")

    for p in sorted(pipes, key=lambda x: x["name"].lower()):
        pub = "[pub]" if p.get("public") else "[priv-membro]"
        print(f"  {pub} id={p['id']:<10} {p['name']}")

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(pipes, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[pipes] {len(pipes)} pipes salvos em {OUT.relative_to(OUT.parent.parent)}")


if __name__ == "__main__":
    main()
