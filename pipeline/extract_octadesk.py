"""
TRK Experience — Extração Octadesk (LOCAL)
==========================================

Lê os arquivos XLSX do Octadesk de `dados/octadesk/` (não consome API).
Quando a API entrar, substituir esta camada sem mexer no resto.

Convenção de nomes (ordem alfanumérica = ordem cronológica):
    Total_de_conversas-YYYYMMDD-HHMM.xlsx
    Tickets_totais-YYYYMMDD-HHMM.xlsx
    Avaliacoes-TICKET-YYYYMMDD-HHMM.xlsx

Regra de seleção: pega o arquivo mais recente (último em sorted desc) por padrão.
Se a pasta estiver vazia, retorna DataFrame vazio + log "SKIP".
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent
OCTADESK_DIR = ROOT / "dados" / "octadesk"

# Suporta tanto underscore quanto espaço no nome (alguns exports variam).
PATTERNS = {
    "conversas":     ["Total_de_conversas-*.xlsx", "Total de conversas-*.xlsx"],
    "tickets":       ["Tickets_totais-*.xlsx",     "Tickets totais-*.xlsx"],
    "aval_tickets":  ["Avaliacoes-TICKET-*.xlsx",  "Avaliacoes-*.xlsx"],
}


AVAL_MAX_DIAS = 14   # idade máxima do Avaliacoes-*.xlsx antes de avisar no log


def _latest(patterns: list[str]) -> Path | None:
    """Retorna o arquivo mais recente que casa com qualquer um dos padrões, ou None."""
    matches: list[Path] = []
    for p in patterns:
        matches.extend(OCTADESK_DIR.glob(p))
    if not matches:
        return None
    return sorted(matches, key=lambda p: p.name, reverse=True)[0]


def _load_xlsx(path: Path, *, verbose: bool = True) -> pd.DataFrame:
    try:
        df = pd.read_excel(path)
        if verbose:
            print(f"  [octadesk] {path.name}: {df.shape[0]} linhas × {df.shape[1]} colunas")
        return df
    except Exception as e:
        print(f"  [octadesk] ERRO lendo {path.name}: {e}")
        return pd.DataFrame()


def extract_octadesk(*, verbose: bool = True) -> dict[str, pd.DataFrame]:
    """
    Retorna dict {"conversas", "tickets", "aval_tickets"} com DataFrames.
    DataFrame vazio quando o arquivo correspondente não está na pasta.
    """
    if not OCTADESK_DIR.exists():
        if verbose:
            print(f"[octadesk] pasta {OCTADESK_DIR.relative_to(ROOT)} não existe — SKIP completo")
        return {k: pd.DataFrame() for k in PATTERNS}

    out: dict[str, pd.DataFrame] = {}
    for key, patterns in PATTERNS.items():
        path = _latest(patterns)
        if path is None:
            if verbose:
                print(f"[octadesk] SKIP — sem arquivo casando {patterns} em dados/octadesk/")
            out[key] = pd.DataFrame()
        else:
            out[key] = _load_xlsx(path, verbose=verbose)
            # ARQUIVO VELHO (01/11/2026) — as Avaliações de ticket são o único
            # export manual que sobrou (a nota não vem na API do Octadesk). Com a
            # rodada automática ninguém mais olha a pasta, então o log avisa quando
            # o arquivo passa de AVAL_MAX_DIAS. Só aviso: a rodada publica mesmo
            # assim, com o arquivo que tem. Tarefa recorrente no Todoist (segundas).
            if key == "aval_tickets":
                import re as _re
                from datetime import datetime as _dt
                m = _re.search(r"(\d{8})-(\d{4})", path.name)
                try:
                    dt_arq = (_dt.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M") if m
                              else _dt.fromtimestamp(path.stat().st_mtime))
                    idade = (_dt.now() - dt_arq).days
                    if idade > AVAL_MAX_DIAS:
                        print(f"  ⚠️  [octadesk] {path.name} tem {idade} dias (limite {AVAL_MAX_DIAS}) — "
                              "exportar Avaliações de tickets no Octadesk e salvar em dados/octadesk/")
                except Exception:
                    pass
    return out


if __name__ == "__main__":
    res = extract_octadesk()
    for k, df in res.items():
        print(f"{k:14}: shape={df.shape}")
