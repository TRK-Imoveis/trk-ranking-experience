"""
Introspecciona campos (start_form + phase fields) e fases de um ou mais pipes.
Produz output legível e salva JSON cru para inspeção.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from pipefy_auth import gql

sys.stdout.reconfigure(encoding="utf-8")

OUT_DIR = Path(__file__).resolve().parent.parent / "config" / "_pipe_dumps"
OUT_DIR.mkdir(parents=True, exist_ok=True)

QUERY = """
query($id: ID!) {
  pipe(id: $id) {
    id
    name
    start_form_fields {
      id
      internal_id
      label
      type
      required
    }
    phases {
      id
      name
      cards_count
      fields {
        id
        internal_id
        label
        type
        required
      }
    }
  }
}
"""


def introspect_one(pipe_id: str, label_hint: str | None = None) -> dict | None:
    print(f"\n{'=' * 70}\nPipe {pipe_id}" + (f"  [{label_hint}]" if label_hint else "") + f"\n{'=' * 70}")
    try:
        data = gql(QUERY, {"id": pipe_id})
        pipe = data["pipe"]
    except Exception as e:
        print(f"  FAIL: {e}")
        return None

    print(f"name = {pipe['name']!r}")
    print(f"\n--- start_form_fields ({len(pipe['start_form_fields'])}) ---")
    for f in pipe["start_form_fields"]:
        print(f"  {f['id']:40}  internal_id={f['internal_id']:30}  label={f['label']!r}  type={f['type']}")

    print(f"\n--- phases ({len(pipe['phases'])}) ---")
    for ph in pipe["phases"]:
        print(f"  [{ph['id']}] {ph['name']:50} cards={ph['cards_count']}  campos={len(ph['fields'])}")

    # campos únicos por phase (sem repetir start_form)
    print(f"\n--- campos das fases (label  ←  id) ---")
    seen = {f["id"] for f in pipe["start_form_fields"]}
    for ph in pipe["phases"]:
        novos = [f for f in ph["fields"] if f["id"] not in seen]
        if not novos:
            continue
        print(f"  fase [{ph['name']}]:")
        for f in novos:
            print(f"    {f['id']:40}  label={f['label']!r}  type={f['type']}")
            seen.add(f["id"])

    # salvar dump
    safe = pipe["name"].replace("/", "_").replace("|", "_").replace(" ", "_")[:60]
    out = OUT_DIR / f"{pipe_id}__{safe}.json"
    out.write_text(json.dumps(pipe, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n  → dump salvo em {out.relative_to(out.parent.parent.parent)}")
    return pipe


def main() -> None:
    targets = []
    for arg in sys.argv[1:]:
        if ":" in arg:
            pid, hint = arg.split(":", 1)
            targets.append((pid, hint))
        else:
            targets.append((arg, None))
    if not targets:
        print("uso: python introspect_fields.py <pipe_id>[:hint] [<pipe_id>:hint ...]")
        sys.exit(1)
    for pid, hint in targets:
        introspect_one(pid, hint)


if __name__ == "__main__":
    main()
