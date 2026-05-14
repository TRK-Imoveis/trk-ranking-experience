"""
Compara calc_caio_comercial_locacao contra baseline 10ª Edição.
Baseline (10ª):
  - Comercial — Início processo <24h:  ok=7,  tot=41
  - Comercial — Anúncio publicado <72h: ok=26, tot=66
  - Comercial — Card na coluna correta: ok=15, tot=27
  - Bônus (★): N=4 → nota Com.Locação = 5,85
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

from calculate import calc_caio_comercial_locacao
from pipeline.extract_pipefy import extract_pipe

REF = pd.Timestamp("2026-05-13", tz="UTC")


def main() -> None:
    print(f"ref date = {REF}")
    df = extract_pipe("comercial_locacao", verbose=False)
    print(f"comercial_locacao DataFrame: {df.shape}")

    res = calc_caio_comercial_locacao(df, bonus_n=4, ref=REF)
    print(f"\nNota Com.Locação (com bônus N=4): {res['nota']}  (baseline: 5.85)")
    print("\nIndicadores:")
    for i in res["indicadores"]:
        print(f"  - {i['nome']:42}  ok={i['ok']:>3}  tot={i['tot']:>3}  pct={i['pct']}  peso={i['peso']}  score={i['score']}")

    print("\nBaseline 10ª (comparação):")
    baselines = [
        ("Comercial — Início processo <24h", 7, 41),
        ("Comercial — Anúncio publicado <72h", 26, 66),
        ("Comercial — Card na coluna correta", 15, 27),
    ]
    for nome, ok_b, tot_b in baselines:
        got = next((i for i in res["indicadores"] if i["nome"] == nome), None)
        diff_ok = abs(got["ok"] - ok_b) if got else "?"
        diff_tot = abs(got["tot"] - tot_b) if got else "?"
        marker = "OK" if got and abs(got["ok"] - ok_b) <= 1 and abs(got["tot"] - tot_b) <= 1 else "OFF"
        print(f"  [{marker}] {nome:42}  got {got['ok']}/{got['tot']} vs baseline {ok_b}/{tot_b}  (Δok={diff_ok}, Δtot={diff_tot})")


if __name__ == "__main__":
    main()
