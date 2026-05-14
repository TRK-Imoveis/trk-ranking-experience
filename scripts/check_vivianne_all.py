"""Compara as 12 funções Pipefy da Vivianne contra baseline 10ª Edição."""
from __future__ import annotations

import sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

from calculate import (
    calc_vivianne_contrato_adm,
    calc_vivianne_rescisao_adm,
    calc_vivianne_contrato_locacao,
    calc_vivianne_rescisao_locacao,
    calc_vivianne_renovacao,
    calc_vivianne_inadimplencia,
    calc_vivianne_backoffice,
)
from pipeline.extract_pipefy import extract_pipe

REF = pd.Timestamp("2026-05-11", tz="UTC")

BASELINE = [
    ("Cont. ADM — Confecção <2h",                          11,  27),
    ("Rescisão ADM — Encerramento <4h",                     2,   5),
    ("Cont. Locação — NIDO→Concluído <24h",                11,  34),
    ("Cont. Locação — Confecção <2h",                      36,  42),
    ("Rescisão Loc. — Levant. Taxas Prop <2h",             10,  19),
    ("Rescisão Loc. — Levant. Taxas Final <2h",            11,  18),
    ("Renovação — Confecção <4h",                           9,  21),
    ("Renovação — Finalização <16h",                        2,  17),
    ("Inadimplência — Cobrança <24h",                     238, 272),
    ("Inadimplência — CredPago ≤15d",                      12,  14),
    ("Inadimplência — Negativação 7-9d",                    2,  15),
    ("BackOffice — Concluído <24h",                       101, 146),
    ("BackOffice — Troca Titularidade <5d",                13,  28),
]


def main() -> None:
    print(f"ref = {REF}\n")
    dfs = {k: extract_pipe(k, verbose=False) for k in
           ["cont_adm", "rescisao_adm", "cont_locacao", "rescisao_loc", "renovacao", "inadimplencia", "backoffice"]}

    indicadores = []
    indicadores += calc_vivianne_contrato_adm(dfs["cont_adm"], ref=REF)["indicadores"]
    indicadores += calc_vivianne_rescisao_adm(dfs["rescisao_adm"], ref=REF)["indicadores"]
    indicadores += calc_vivianne_contrato_locacao(dfs["cont_locacao"], ref=REF)["indicadores"]
    indicadores += calc_vivianne_rescisao_locacao(dfs["rescisao_loc"], ref=REF)["indicadores"]
    indicadores += calc_vivianne_renovacao(dfs["renovacao"], ref=REF)["indicadores"]
    indicadores += calc_vivianne_inadimplencia(dfs["inadimplencia"], bonus_n=124, ref=REF)["indicadores"]
    indicadores += calc_vivianne_backoffice(dfs["backoffice"], ref=REF)["indicadores"]

    print(f"{'nome':45}  {'got':>10}  {'baseline':>10}  status")
    print("-" * 90)
    falhas = 0
    for nome, ok_b, tot_b in BASELINE:
        got = next((i for i in indicadores if i["nome"] == nome), None)
        if got is None:
            print(f"  [MISS] {nome:45}  ???  vs {ok_b}/{tot_b}")
            falhas += 1
            continue
        diff_ok = abs(got["ok"] - ok_b)
        diff_tot = abs(got["tot"] - tot_b)
        ok = diff_ok <= 1 and diff_tot <= 1
        marker = "OK " if ok else "OFF"
        if not ok:
            falhas += 1
        print(f"  [{marker}] {nome:45}  {got['ok']:>4}/{got['tot']:>4}  vs {ok_b:>4}/{tot_b:>4}   Δok={diff_ok} Δtot={diff_tot}")
    print(f"\n{len(BASELINE) - falhas}/{len(BASELINE)} OK")


if __name__ == "__main__":
    main()
