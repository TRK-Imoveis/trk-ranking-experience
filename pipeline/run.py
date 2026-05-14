"""
TRK Experience — Orquestrador principal
=======================================

Roda o pipeline completo:
1. Extrai os 12 pipes do Pipefy (usa cache em dados/raw/ se disponível).
2. Calcula ranking dos 5 colaboradores.
3. (Opcional) Compara com baselines.json se --validate.
4. Salva painel/dados/atual.json com a estrutura PESSOAS/IMOVEIS/PROC_RICH.

CLI:
    python -m pipeline.run                 # snapshot completo
    python -m pipeline.run --validate      # roda também a validação
    python -m pipeline.run --no-cache      # força re-extract
    python -m pipeline.run --ref 2026-05-11  # data de referência (ISO)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

from calculate import calcular_ranking
from pipeline.extract_pipefy import extract_pipe
from pipeline.validate import validar

OUT_JSON = ROOT / "painel" / "dados" / "atual.json"


def carregar_dataframes(use_cache: bool) -> dict:
    keys = [
        "comercial_locacao", "cont_locacao", "cont_adm", "rescisao_adm", "rescisao_loc",
        "reparos", "renovacao", "inadimplencia", "backoffice", "dirf_darf",
        "vistorias", "contestacoes",
    ]
    return {k: extract_pipe(k, use_cache=use_cache) for k in keys}


def main(argv: list[str]) -> None:
    use_cache = "--no-cache" not in argv
    validate = "--validate" in argv
    ref = None
    if "--ref" in argv:
        ref = pd.Timestamp(argv[argv.index("--ref") + 1], tz="UTC")

    print(f"[run] use_cache={use_cache}  validate={validate}  ref={ref}")

    dataframes = carregar_dataframes(use_cache=use_cache)
    # Octadesk ainda não — placeholders vazios para não quebrar orquestração.
    for k in ("conversas", "tickets", "aval_tickets"):
        dataframes[k] = pd.DataFrame()

    if validate:
        validar(ref if ref is not None else pd.Timestamp.utcnow())
        return

    # snapshot final → painel/dados/atual.json
    # OBS: enquanto Octadesk não estiver pronto, calcular_ranking pode falhar nas funções WhatsApp/Ticket.
    # Para já produzir um atual.json parcial, usar `--validate` apenas.
    print("[run] geração do atual.json depende das funções Octadesk — ainda não implementadas.")


if __name__ == "__main__":
    main(sys.argv[1:])
