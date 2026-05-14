"""Debuga a 'Coluna correta' do Caio."""
from __future__ import annotations
import sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

from calculate import _expected_phase_desocupacao, excluir_rascunhos, aplicar_cutoff, filtrar_por_assignee
from pipeline.extract_pipefy import extract_pipe

REF = pd.Timestamp("2026-05-13", tz="UTC")


def main() -> None:
    df = extract_pipe("comercial_locacao", verbose=False)
    df = excluir_rascunhos(df)
    df = aplicar_cutoff(df, "Criado em", ref=REF)
    df = filtrar_por_assignee(df, "Profissional responsável", "Caio")

    col_cf = "Primeira vez que entrou na fase Conferência Final"
    col_pub = "Data publicação Anúncio"
    mask = df[col_cf].notna() & (df["Fase atual"] != "Concluído")
    sub = df[mask].copy()
    sub["dias_desocup"] = (REF - sub[col_pub]).dt.total_seconds() / 86400.0
    sub["expected"] = sub["dias_desocup"].apply(_expected_phase_desocupacao)
    sub["ok"] = sub["Fase atual"] == sub["expected"]

    print(f"Denominador: {len(sub)}")
    print(f"Numerador (ok=True): {sub['ok'].sum()}")
    print()
    # ordena por dias_desocup
    cols_show = [col_pub, "dias_desocup", "expected", "Fase atual", "ok"]
    print(sub[cols_show].sort_values("dias_desocup").to_string())


if __name__ == "__main__":
    main()
