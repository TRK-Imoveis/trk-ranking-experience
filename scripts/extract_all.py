"""Roda extract_pipe em todos os 12 pipes, imprime tabela-resumo."""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8")

from pipeline.extract_pipefy import _load_fields_map, extract_pipe


def main() -> None:
    fmap = _load_fields_map()
    results = {}
    t0 = time.time()
    for key in fmap:
        try:
            df = extract_pipe(key, use_cache=True, verbose=True)
            results[key] = {"rows": df.shape[0], "cols": df.shape[1], "err": None}
        except Exception as e:
            results[key] = {"rows": 0, "cols": 0, "err": str(e)[:200]}
    elapsed = time.time() - t0

    print("\n\n" + "=" * 80)
    print("RESUMO DE EXTRAÇÃO")
    print("=" * 80)
    print(f"{'pipe_key':22} {'pipe_name':45} {'rows':>6} {'cols':>5}  status")
    print("-" * 80)
    for key, r in results.items():
        name = fmap[key]["pipe_name"]
        status = "OK" if r["err"] is None else f"FAIL: {r['err']}"
        print(f"{key:22} {name:45} {r['rows']:>6} {r['cols']:>5}  {status}")
    print("-" * 80)
    print(f"Total tempo: {elapsed:.1f}s   |   Total rows: {sum(r['rows'] for r in results.values())}")


if __name__ == "__main__":
    main()
