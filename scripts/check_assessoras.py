"""Compara funções das assessoras (Natália + Gardênia) contra baseline 10ª Edição."""
from __future__ import annotations

import sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

from calculate import (
    calc_assessora_contrato_adm,
    calc_assessora_rescisao_adm,
    calc_assessora_rescisao_locacao,
    calc_assessora_reparos,
    calc_assessora_renovacao,
    calc_assessora_backoffice,
    calc_assessora_dirf_darf,
)
from pipeline.extract_pipefy import extract_pipe

REF = pd.Timestamp("2026-05-11", tz="UTC")

BASELINE = {
    "natalia": [
        ("Cont. ADM — Conferência ≤2h",                       2,  12),
        ("Rescisão ADM — Repasse <12h",                       0,   2),
        ("Rescisão ADM — Distrato assinado",                  0,   2),
        ("Rescisão Loc. — Boleto prop <24h",                  4,   7),
        ("Rescisão Loc. — Boleto final <15d",                 2,   5),
        ("Reparos — Orçamento <4h",                          40,  51),
        ("Reparos — Pós-venda ≤7d",                          15,  51),
        ("Renovação — Contato >60d",                          3,  13),
        ("Renovação — Assinado antes vencimento",             1,   9),
        ("BackOffice — Pendência <24h",                       0,   3),
        ("DIRF/DARF — Concluído antes 29/05",                13,  31),
    ],
    "gardenia": [
        ("Cont. ADM — Conferência ≤2h",                       0,  13),
        ("Rescisão ADM — Repasse <12h",                       0,   2),
        ("Rescisão ADM — Distrato assinado",                  0,   5),
        ("Rescisão Loc. — Boleto prop <24h",                  7,  12),
        ("Rescisão Loc. — Boleto final <15d",                 7,   9),
        ("Reparos — Orçamento <4h",                          50,  72),
        ("Reparos — Pós-venda ≤7d",                          15,  43),
        ("Renovação — Contato >60d",                          5,  15),
        ("Renovação — Assinado antes vencimento",             4,   9),
        ("BackOffice — Pendência <24h",                       0,  11),
        ("DIRF/DARF — Concluído antes 29/05",                 2,   6),
    ],
}


def main() -> None:
    print(f"ref = {REF}\n")
    dfs = {k: extract_pipe(k, verbose=False) for k in
           ["cont_adm", "rescisao_adm", "rescisao_loc", "reparos", "renovacao", "backoffice", "dirf_darf"]}

    BONUS_VIST = {"natalia": 5, "gardenia": 4}
    for assess in ("natalia", "gardenia"):
        ind = []
        ind += calc_assessora_contrato_adm(dfs["cont_adm"], assess, bonus_n=BONUS_VIST[assess], ref=REF)["indicadores"]
        ind += calc_assessora_rescisao_adm(dfs["rescisao_adm"], assess, ref=REF)["indicadores"]
        ind += calc_assessora_rescisao_locacao(dfs["rescisao_loc"], assess, ref=REF)["indicadores"]
        ind += calc_assessora_reparos(dfs["reparos"], assess, ref=REF)["indicadores"]
        ind += calc_assessora_renovacao(dfs["renovacao"], assess, ref=REF)["indicadores"]
        ind += calc_assessora_backoffice(dfs["backoffice"], assess, ref=REF)["indicadores"]
        ind += calc_assessora_dirf_darf(dfs["dirf_darf"], assess, ref=REF)["indicadores"]

        print(f"\n=== {assess.upper()} ===")
        print(f"{'nome':45}  {'got':>10}  {'baseline':>10}  status")
        print("-" * 90)
        falhas = 0
        for nome, ok_b, tot_b in BASELINE[assess]:
            got = next((i for i in ind if i["nome"] == nome), None)
            if got is None:
                print(f"  [MISS] {nome:45}  vs {ok_b}/{tot_b}")
                falhas += 1
                continue
            diff_ok = abs(got["ok"] - ok_b)
            diff_tot = abs(got["tot"] - tot_b)
            ok = diff_ok <= 1 and diff_tot <= 1
            marker = "OK " if ok else "OFF"
            if not ok:
                falhas += 1
            print(f"  [{marker}] {nome:45}  {got['ok']:>4}/{got['tot']:>4}  vs {ok_b:>4}/{tot_b:>4}   Δok={diff_ok} Δtot={diff_tot}")
        print(f"  {len(BASELINE[assess]) - falhas}/{len(BASELINE[assess])} OK")


if __name__ == "__main__":
    main()
