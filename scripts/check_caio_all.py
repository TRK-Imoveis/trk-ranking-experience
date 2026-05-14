"""Compara todas as 4 funções Pipefy do Caio contra baseline 10ª Edição."""
from __future__ import annotations

import sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

from calculate import (
    calc_caio_comercial_locacao,
    calc_caio_contrato_locacao,
    calc_caio_contrato_adm,
    calc_caio_renovacao,
)
from pipeline.extract_pipefy import extract_pipe

REF = pd.Timestamp("2026-05-11", tz="UTC")


BASELINE = [
    ("Comercial — Início processo <24h",   7, 41),
    ("Comercial — Anúncio publicado <72h", 26, 66),
    ("Comercial — Card na coluna correta", 15, 27),
    ("Cont. Locação — Ocupação <30d",       5,  6),
    ("Cont. Locação — Documentação <24h",  24, 42),
    ("Cont. ADM — Criação→NIDO <7d",        2,  5),
    ("Renovação — Avaliação >90d",         11, 38),
]


def main() -> None:
    print(f"ref = {REF}\n")
    com = extract_pipe("comercial_locacao", verbose=False)
    cl = extract_pipe("cont_locacao", verbose=False)
    cadm = extract_pipe("cont_adm", verbose=False)
    ren = extract_pipe("renovacao", verbose=False)

    indicadores = []
    indicadores += calc_caio_comercial_locacao(com, bonus_n=4, ref=REF)["indicadores"]
    indicadores += calc_caio_contrato_locacao(com, cl, ref=REF)["indicadores"]
    indicadores += calc_caio_contrato_adm(cadm, ref=REF)["indicadores"]
    indicadores += calc_caio_renovacao(ren, ref=REF)["indicadores"]

    print(f"{'nome':42}  {'got':>10}  {'baseline':>10}  status")
    print("-" * 80)
    for nome, ok_b, tot_b in BASELINE:
        got = next((i for i in indicadores if i["nome"] == nome), None)
        if got is None:
            print(f"  [MISS] {nome:42}  ???  vs {ok_b}/{tot_b}")
            continue
        diff_ok = abs(got["ok"] - ok_b)
        diff_tot = abs(got["tot"] - tot_b)
        ok = diff_ok <= 1 and diff_tot <= 1
        marker = "OK " if ok else "OFF"
        print(f"  [{marker}] {nome:42}  {got['ok']:>3}/{got['tot']:>3}  vs {ok_b:>3}/{tot_b:>3}   Δok={diff_ok} Δtot={diff_tot}")


if __name__ == "__main__":
    main()
