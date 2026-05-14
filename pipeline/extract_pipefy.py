"""
TRK Experience — Extração Pipefy
================================

Extrai cards de cada pipe do ranking via GraphQL allCards(pipeId, ...) e
retorna DataFrames com nomes de coluna IDÊNTICOS aos XLSX antigos, para que
o calculate.py possa permanecer agnóstico à origem.

Colunas geradas para cada pipe (sempre):
    - id                          (card.id)
    - Título                      (card.title)
    - Criado em                   (card.createdAt — parseado para datetime)
    - Fase atual                  (card.current_phase.name)
    - URL                         (card.url)

Colunas derivadas, uma tripla por fase listada em config/fields_map.json:
    - Primeira vez que entrou na fase <X>     (phases_history.firstTimeIn)
    - Última vez que saiu da fase <X>         (phases_history.lastTimeOut, null se ainda na fase)
    - Tempo total na fase <X> (dias)          (phases_history.duration / 86400)

Colunas de campos mapeados (uma por entrada em fields_map[<pipe>].fields):
    - <label do manual>           (datetime_value / date_value / value / array_value,
                                   conforme o `type` registrado no fields_map)

Cache opcional em dados/raw/<pipe_id>.json (lista bruta de cards).
Rate limit: ~2s entre requests paginados.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

# Windows: força UTF-8 no stdout para suportar acentos e símbolos nos prints.
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# permite rodar diretamente: `python -m pipeline.extract_pipefy <key>`
# ou importar: `from pipeline.extract_pipefy import extract_pipe`
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))
from pipefy_auth import gql  # type: ignore  # noqa: E402

# ────────────────────────────────────────────────────────────────────
# Constantes e config
# ────────────────────────────────────────────────────────────────────

FIELDS_MAP_PATH = ROOT / "config" / "fields_map.json"
RAW_DIR = ROOT / "dados" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

PAGE_SIZE = 50
RATE_LIMIT_SLEEP = 2.1   # seg entre requests (≈ 28 req/min, com folga)

CARD_QUERY = """
query($pipeId: ID!, $first: Int!, $after: String) {
  allCards(pipeId: $pipeId, first: $first, after: $after) {
    totalCount
    pageInfo { hasNextPage endCursor }
    edges {
      cursor
      node {
        id
        title
        createdAt
        finished_at
        done
        due_date
        url
        assignees { id name }
        current_phase { id name }
        fields {
          name
          value
          array_value
          datetime_value
          date_value
          native_value
          float_value
          assignee_values { id name email }
          field { id internal_id }
        }
        phases_history {
          phase { id name }
          firstTimeIn
          lastTimeIn
          lastTimeOut
          duration
        }
      }
    }
  }
}
"""


def _load_fields_map() -> dict[str, dict]:
    return json.loads(FIELDS_MAP_PATH.read_text(encoding="utf-8"))


# ────────────────────────────────────────────────────────────────────
# Fetching com paginação + cache
# ────────────────────────────────────────────────────────────────────

def fetch_all_cards(pipe_id: str, *, use_cache: bool = True, verbose: bool = True) -> list[dict]:
    """
    Pagina por allCards(pipeId) em batches de PAGE_SIZE e retorna lista de cards.

    Cache: se use_cache e dados/raw/<pipe_id>.json existir, retorna do disco.
    """
    cache_path = RAW_DIR / f"{pipe_id}.json"
    if use_cache and cache_path.exists():
        if verbose:
            print(f"  [cache] {pipe_id} ← {cache_path.relative_to(ROOT)}")
        return json.loads(cache_path.read_text(encoding="utf-8"))

    cards: list[dict] = []
    cursor: str | None = None
    page = 0
    while True:
        page += 1
        data = gql(CARD_QUERY, {"pipeId": pipe_id, "first": PAGE_SIZE, "after": cursor})
        ac = data["allCards"]
        edges = ac["edges"]
        cards.extend(e["node"] for e in edges)
        total = ac.get("totalCount") or len(cards)
        if verbose:
            print(f"  [fetch] pipe={pipe_id} pág {page}: +{len(edges)} cards (total acumulado {len(cards)}/{total})")
        if not ac["pageInfo"]["hasNextPage"]:
            break
        cursor = ac["pageInfo"]["endCursor"]
        time.sleep(RATE_LIMIT_SLEEP)

    cache_path.write_text(json.dumps(cards, ensure_ascii=False), encoding="utf-8")
    if verbose:
        print(f"  [cache] gravado {cache_path.relative_to(ROOT)} ({len(cards)} cards)")
    return cards


# ────────────────────────────────────────────────────────────────────
# Conversão Card → linha do DataFrame
# ────────────────────────────────────────────────────────────────────

def _parse_dt(v: Any) -> Any:
    if v is None or v == "":
        return pd.NaT
    return pd.to_datetime(v, errors="coerce", utc=True)


def _extract_field_value(cf: dict, field_type: str) -> Any:
    """
    Extrai o valor "natural" de um CardField conforme o type registrado no fields_map.

    Regras:
    - datetime / date / due_date → datetime tz-aware
    - assignee_select            → lista de nomes (strings)
    - number / currency          → float
    - select / radio / label_select / short/long_text / connector → value (string)
    - attachment / checklist     → value bruto (string, geralmente JSON serializado)
    """
    if cf is None:
        return None
    t = (field_type or "").lower()
    if t in ("datetime", "due_date"):
        return _parse_dt(cf.get("datetime_value"))
    if t == "date":
        return _parse_dt(cf.get("date_value") or cf.get("datetime_value"))
    if t == "assignee_select":
        avs = cf.get("assignee_values") or []
        return [a.get("name") for a in avs if a.get("name")]
    if t in ("number", "currency", "id"):
        v = cf.get("float_value")
        if v is not None:
            return v
        raw = cf.get("native_value") or cf.get("value")
        try:
            return float(raw) if raw not in (None, "") else None
        except (TypeError, ValueError):
            return raw
    # default: value string
    return cf.get("value") or cf.get("native_value")


def _card_to_row(card: dict, cfg: dict) -> dict:
    row: dict[str, Any] = {
        "id": card.get("id"),
        "Título": card.get("title"),
        "Criado em": _parse_dt(card.get("createdAt")),
        "Fase atual": (card.get("current_phase") or {}).get("name"),
        "URL": card.get("url"),
        "_done": bool(card.get("done")),
        "_finished_at": _parse_dt(card.get("finished_at")),
        # "Responsáveis" = card-level assignees (plural — bate com export XLSX antigo).
        # Distinto de qualquer campo de form chamado "Responsável" (singular).
        "Responsáveis": [a.get("name") for a in (card.get("assignees") or []) if a.get("name")],
    }

    # Campos mapeados — lookup por field.id
    fields_by_id = {(f.get("field") or {}).get("id"): f for f in (card.get("fields") or []) if f.get("field")}
    for label, info in (cfg.get("fields") or {}).items():
        cf = fields_by_id.get(info["id"])
        row[label] = _extract_field_value(cf, info.get("type", ""))

    # Derivações por fase
    ph_by_id = {(h.get("phase") or {}).get("id"): h for h in (card.get("phases_history") or [])}
    for phase_name, info in (cfg.get("phases") or {}).items():
        h = ph_by_id.get(info["id"])
        col_in = f"Primeira vez que entrou na fase {phase_name}"
        col_out = f"Última vez que saiu da fase {phase_name}"
        col_dur = f"Tempo total na fase {phase_name} (dias)"
        if h:
            row[col_in] = _parse_dt(h.get("firstTimeIn"))
            row[col_out] = _parse_dt(h.get("lastTimeOut"))
            dur = h.get("duration")
            row[col_dur] = (dur / 86400.0) if dur is not None else None
        else:
            row[col_in] = pd.NaT
            row[col_out] = pd.NaT
            row[col_dur] = None
    return row


# ────────────────────────────────────────────────────────────────────
# API pública
# ────────────────────────────────────────────────────────────────────

def extract_pipe(pipe_key: str, *, use_cache: bool = True, verbose: bool = True) -> pd.DataFrame:
    """
    Extrai um pipe do ranking como DataFrame, com colunas no nome do manual/XLSX.
    """
    fmap = _load_fields_map()
    if pipe_key not in fmap:
        raise KeyError(f"pipe_key {pipe_key!r} não está em fields_map.json. Disponíveis: {list(fmap)}")
    cfg = fmap[pipe_key]
    if verbose:
        print(f"\n[extract] {pipe_key} ← pipe {cfg['pipe_id']} ({cfg['pipe_name']})")
    cards = fetch_all_cards(cfg["pipe_id"], use_cache=use_cache, verbose=verbose)
    rows = [_card_to_row(c, cfg) for c in cards]
    df = pd.DataFrame(rows)
    if verbose:
        print(f"  [shape] {df.shape[0]} linhas × {df.shape[1]} colunas")
    return df


def extract_all(*, use_cache: bool = True, verbose: bool = True) -> dict[str, pd.DataFrame]:
    """Extrai todos os 12 pipes do ranking. Retorna dict pipe_key → DataFrame."""
    return {key: extract_pipe(key, use_cache=use_cache, verbose=verbose) for key in _load_fields_map()}


# ────────────────────────────────────────────────────────────────────
# CLI
# ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print("uso: python -m pipeline.extract_pipefy <pipe_key> [--no-cache] [--sample N]")
        print(f"chaves: {list(_load_fields_map())}")
        sys.exit(1)

    key = args[0]
    use_cache = "--no-cache" not in args
    sample = 10
    if "--sample" in args:
        sample = int(args[args.index("--sample") + 1])

    df = extract_pipe(key, use_cache=use_cache)
    print(f"\n=== Sample {sample} linhas / {len(df.columns)} colunas ===")
    print(f"Colunas: {list(df.columns)}")
    print("\n", df.head(sample).to_string())
