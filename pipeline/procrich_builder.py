"""
TRK Experience — Builder do dicionário PROC_RICH (paineis por processo)
========================================================================

Gera o dicionário PROC_RICH consumido pelo painel HTML (compatível com a 10ª Ed):
    13 entradas, uma por processo. Cada entrada tem:
      grupo, titulo, kpis (4), charts (2), indicadores (lista), insights (3)

Reaproveita PESSOAS (output do build_atual) — NÃO recomputa nada de calculate.py.

Insights:
    - Auto: regra "líder + gargalo + bônus/volume" gerada a partir dos indicadores.
    - Override manual: se a chave aparece em config/procrich_insights_overrides.json,
      esses 3 insights substituem os automáticos.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
OVERRIDES_PATH = ROOT / "config" / "procrich_insights_overrides.json"


# ────────────────────────────────────────────────────────────────────
# Metadados dos 13 processos (ordem do painel + grupos + títulos)
# ────────────────────────────────────────────────────────────────────

PROC_KEYS_ORDEM = [
    "Cont. ADM", "Rescisão ADM", "Com. Locação", "Cont. Locação", "Rescisão Loc.",
    "Reparos", "Renovação", "Inadimplência", "Vistorias", "BackOffice",
    "DIRF/DARF", "Ticket", "WhatsApp",
]

PROC_META = {
    "Cont. ADM":      {"grupo": "Operações Centrais", "titulo": "Contrato de Administração"},
    "Rescisão ADM":   {"grupo": "Operações Centrais", "titulo": "Rescisão de Administração"},
    "Com. Locação":   {"grupo": "Comercial",          "titulo": "Comercial de Locação"},
    "Cont. Locação":  {"grupo": "Operações Centrais", "titulo": "Contrato de Locação"},
    "Rescisão Loc.":  {"grupo": "Operações Centrais", "titulo": "Rescisão de Locação"},
    "Reparos":        {"grupo": "Manutenção",         "titulo": "Reparos"},
    "Renovação":      {"grupo": "Operações Centrais", "titulo": "Renovação de Contratos"},
    "Inadimplência":  {"grupo": "Financeiro",         "titulo": "Inadimplência"},
    "Vistorias":      {"grupo": "Operações",          "titulo": "Vistorias e Contestações (Marinho)"},
    "BackOffice":     {"grupo": "Operações Centrais", "titulo": "BackOffice"},
    "DIRF/DARF":      {"grupo": "Operações Centrais", "titulo": "DIRF/DARF"},
    "Ticket":         {"grupo": "Atendimento",        "titulo": "Tickets (Octadesk)"},
    "WhatsApp":       {"grupo": "Atendimento",        "titulo": "WhatsApp (Octadesk)"},
}

# Mapeamento processo → prefixos do nome do indicador em PESSOAS[*].detalhes
PREFIXOS_PROC = {
    "Cont. ADM":      ("Cont. ADM —",),
    "Rescisão ADM":   ("Rescisão ADM —",),
    "Com. Locação":   ("Comercial —",),
    "Cont. Locação":  ("Cont. Locação —",),
    "Rescisão Loc.":  ("Rescisão Loc. —",),
    "Reparos":        ("Reparos —",),
    "Renovação":      ("Renovação —",),
    "Inadimplência":  ("Inadimplência —",),
    "Vistorias":      ("Laudos entregues", "Vistorias dentro", "Contestaç"),
    "BackOffice":     ("BackOffice —",),
    "DIRF/DARF":      ("DIRF/DARF —",),
    "Ticket":         ("Tickets —",),
    "WhatsApp":       ("WhatsApp —",),
}

NOMES_RESP = {
    "caio": "Caio", "vivianne": "Vivianne", "marinho": "Marinho",
    "natalia": "Natália", "gardenia": "Gardênia",
}

CORES_BARV = ["#000", "#555", "#888", "#C8C4BC", "#E0DCD0"]


# Ordem dos KPIs por processo (decisão da gestora — by relevance, NÃO alfabética)
# Tokens aceitos:
#   "<pessoa>"              → 1 KPI: top-1 indicador da pessoa (maior peso)
#   "<pessoa>_indicadores"  → todos os indicadores da pessoa nesse processo
#   "caio_3indicadores"     → top 3 indicadores do Caio (Comercial)
#   "assessoras"            → Natália + Gardênia (1 cada)
#   "BONUS"                 → ★ N total do bonus_proc
#   "volume"                → tot do maior indicador (label "X cards no período")
ORDEM_KPIS_POR_PROCESSO = {
    "Cont. ADM":      ["natalia", "gardenia", "vivianne", "BONUS"],
    "Rescisão ADM":   ["natalia", "gardenia", "vivianne"],
    "Com. Locação":   ["caio_3indicadores", "BONUS"],
    "Cont. Locação":  ["caio", "vivianne_indicadores"],
    "Rescisão Loc.":  ["vivianne_indicadores", "assessoras"],
    "Reparos":        ["natalia", "gardenia"],
    "Renovação":      ["caio", "natalia", "gardenia", "vivianne_indicadores"],
    "Inadimplência":  ["vivianne_indicadores", "BONUS"],
    "Vistorias":      ["volume", "marinho_indicadores"],
    "BackOffice":     ["natalia", "gardenia", "vivianne_indicadores"],
    "DIRF/DARF":      ["natalia", "gardenia"],
    "Ticket":         ["caio", "natalia", "vivianne", "gardenia"],
    "WhatsApp":       ["caio", "natalia", "gardenia"],
}


# META_MAP — fidelidade ao manual (decisão da gestora). Keys são prefixos do nome
# real do indicador em PESSOAS.detalhes. Match por startswith + fallback heurística.
META_MAP = {
    # Cont. ADM
    "Cont. ADM — Conferência":     "≤2h úteis",
    "Cont. ADM — Confecção":       "≤2h úteis",
    "Cont. ADM — Criação→NIDO":    "≤7d corrido",
    "Cont. ADM — Vistoria de entrada": "+1/vistoria (bônus)",
    # Rescisão ADM
    "Rescisão ADM — Repasse":      "≤12h úteis",
    "Rescisão ADM — Distrato":     "Preenchido",
    "Rescisão ADM — Encerramento": "≤4h corrido",
    # Comercial Locação (Caio)
    "Comercial — Início":          "≤24h corrido",
    "Comercial — Anúncio":         "≤72h corrido",
    "Comercial — Card na coluna":  "Fase correta",
    "Comercial — Imóvel alugado":  "+1/imóvel (bônus)",
    # Cont. Locação
    "Cont. Locação — Ocupação":    "≤30d corrido",
    "Cont. Locação — Documentação":"≤24h úteis",
    "Cont. Locação — NIDO":        "≤24h corrido",
    "Cont. Locação — Confecção":   "≤2h corrido (Pipefy)",
    # Rescisão Loc.
    "Rescisão Loc. — Boleto prop": "≤24h corrido",
    "Rescisão Loc. — Boleto final":"≤15d corrido",
    "Rescisão Loc. — Levant. Taxas Prop":  "≤2h corrido",
    "Rescisão Loc. — Levant. Taxas Final": "≤2h corrido",
    # Reparos
    "Reparos — Orçamento":         "≤4h úteis",
    "Reparos — Pós-venda":         "≤7d corrido",
    # Renovação
    "Renovação — Contato":         ">60d antes do venc",
    "Renovação — Assinado":        "antes do venc",
    "Renovação — Confecção":       "≤4h corrido (Pipefy)",
    "Renovação — Finalização":     "≤16h úteis",
    "Renovação — Avaliação":       ">90d antes do venc",
    # Inadimplência
    "Inadimplência — Cobrança":    "≤24h corrido",
    "Inadimplência — CredPago":    "≤15d corrido",
    "Inadimplência — Negativação": "entre 7 e 9d corrido",
    "Inadimplência — Boletos em atraso": "Sim/Não (bônus)",
    # Vistorias (Marinho — nomes sem prefixo "Vistorias —")
    "Laudos entregues":            "≤48h corrido",
    "Vistorias dentro":            "≤ teto do balde +15%",
    "Contestações respondidas":    "≤24h corrido",
    # BackOffice
    "BackOffice — Pendência":      "≤24h corrido",
    "BackOffice — Concluído":      "≤24h corrido",
    "BackOffice — Troca":          "≤5d úteis",
    # DIRF/DARF
    "DIRF/DARF — Concluído":       "antes de 29/05/2026",
    # Tickets / WhatsApp
    "Tickets — SLA":               "≤4h úteis",
    "Tickets — Avaliações":        "% positivas",
    "WhatsApp — Resposta":         "≤5min",
    "WhatsApp — Avaliações":       "% positivas",
}


# ────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────

def _short_nome(nome: str) -> str:
    """'Cont. ADM — Confecção <2h' → 'Confecção <2h'. Para Marinho/Octadesk, mantém o nome."""
    if " — " in nome:
        return nome.split(" — ", 1)[1].strip()
    return nome.strip()


def _meta_from_nome(nome: str) -> str:
    """Deriva o campo 'meta'. 1º META_MAP (prefix match) → 2º heurística → fallback."""
    # 1. Match exato
    if nome in META_MAP:
        return META_MAP[nome]
    # 2. Prefix match (META_MAP key é prefixo do nome real)
    for key, val in META_MAP.items():
        if nome.startswith(key):
            return val
    # 3. Fallback heurística (genérico)
    n = nome.lower()
    if "★" in nome: return "+1/caso (bônus)"
    return "métrica de processo"


def _kpi_cls(pct: Optional[float]) -> str:
    """ok se ≥50%, bad se <50%, '' se None (volume)."""
    if pct is None: return ""
    return "ok" if pct >= 50 else "bad"


def _proc_de_indicador(nome: str) -> Optional[str]:
    """Retorna a chave de PROC_RICH que esse indicador pertence (ou None)."""
    for proc, prefixos in PREFIXOS_PROC.items():
        for pre in prefixos:
            if nome.startswith(pre):
                return proc
    return None


def _coletar_indicadores(pessoas: list) -> dict[str, list[dict]]:
    """Agrupa indicadores de PESSOAS[*].detalhes por processo. Adiciona campo `resp`."""
    by_proc: dict[str, list[dict]] = {p: [] for p in PROC_KEYS_ORDEM}
    for p in pessoas:
        resp_label = NOMES_RESP.get(p["id"], p["id"])
        for d in p.get("detalhes", []):
            proc = _proc_de_indicador(d["nome"])
            if proc is None:
                continue
            by_proc[proc].append({
                **d,
                "resp": resp_label,
                "pessoa_id": p["id"],
            })
    return by_proc


# ────────────────────────────────────────────────────────────────────
# Construção de KPIs / charts / indicadores
# ────────────────────────────────────────────────────────────────────

def _kpi_short_label(resp: str, ind_nome: str) -> str:
    """'Caio' + 'Início processo <24h' → 'Caio Início ≤24h' (curto para card KPI)."""
    sn = _short_nome(ind_nome)
    # encurta — pega os 2-3 primeiros tokens
    tokens = sn.split()
    short = " ".join(tokens[:3])
    if len(short) > 22:
        short = short[:22]
    return f"{resp} {short}".strip()


def _bonus_total_proc(proc: str, pessoas: list) -> int:
    """Soma o bônus N das pessoas cujo bonus_proc == proc."""
    return sum(p.get("bonus", 0) for p in pessoas if p.get("bonus_proc") == proc)


def _label_bonus_proc(proc: str) -> str:
    return {
        "Cont. ADM":     "Vistorias entrada",
        "Inadimplência": "Boletos antes repasse",
        "Com. Locação":  "Alugados sem anúncio",
    }.get(proc, "Bônus")


def _kpi_de_indicador(ind: dict) -> dict:
    """KPI a partir de 1 indicador normal."""
    pct = ind.get("pct")
    return {
        "v": f"{pct:.1f}%" if pct is not None else "—",
        "l": _kpi_short_label(ind["resp"], ind["nome"]),
        "cls": _kpi_cls(pct),
    }


def _inds_da_pessoa(pessoa_id: str, indicadores: list[dict]) -> list[dict]:
    """Filtra indicadores não-bônus de uma pessoa, ordenados por peso decrescente."""
    out = [i for i in indicadores
           if i.get("pessoa_id") == pessoa_id and "★" not in i["nome"]]
    out.sort(key=lambda i: (-(i.get("peso") or 0), i["nome"]))
    return out


def _build_kpis(proc: str, indicadores: list[dict], pessoas: list) -> list[dict]:
    """Gera 4 KPIs seguindo ORDEM_KPIS_POR_PROCESSO. Truncate em 4."""
    ordem = ORDEM_KPIS_POR_PROCESSO.get(proc, [])
    bonus_n = _bonus_total_proc(proc, pessoas)
    kpis: list[dict] = []

    for slot in ordem:
        if len(kpis) >= 4:
            break
        if slot == "BONUS":
            if bonus_n > 0:
                kpis.append({"v": f"★ {bonus_n}", "l": _label_bonus_proc(proc), "cls": ""})
        elif slot == "volume":
            # tot do maior indicador
            normais = [i for i in indicadores if "★" not in i["nome"]]
            if normais:
                top = max(normais, key=lambda i: i.get("tot", 0))
                if top.get("tot", 0) > 0:
                    label = "vistorias no período" if proc == "Vistorias" else f"Total {_short_nome(top['nome'])[:18]}"
                    kpis.append({"v": str(top["tot"]), "l": label, "cls": ""})
        elif slot == "assessoras":
            for pid in ("natalia", "gardenia"):
                if len(kpis) >= 4:
                    break
                inds = _inds_da_pessoa(pid, indicadores)
                if inds:
                    kpis.append(_kpi_de_indicador(inds[0]))
        elif slot.endswith("_3indicadores"):
            pid = slot.replace("_3indicadores", "")
            for ind in _inds_da_pessoa(pid, indicadores)[:3]:
                if len(kpis) >= 4:
                    break
                kpis.append(_kpi_de_indicador(ind))
        elif slot.endswith("_indicadores"):
            pid = slot.replace("_indicadores", "")
            for ind in _inds_da_pessoa(pid, indicadores):
                if len(kpis) >= 4:
                    break
                kpis.append(_kpi_de_indicador(ind))
        else:
            # token simples = pessoa_id → top-1 indicador
            inds = _inds_da_pessoa(slot, indicadores)
            if inds:
                kpis.append(_kpi_de_indicador(inds[0]))

    # Caso especial Vistorias: gestora pede formato 10ª (volume + Laudo, volume + Contestações)
    if proc == "Vistorias":
        normais = [i for i in indicadores if "★" not in i["nome"]]
        laudos  = next((i for i in normais if "Laudo" in i["nome"]), None)
        efic    = next((i for i in normais if "tempo padrão" in i["nome"]), None)
        contest = next((i for i in normais if "Contestaç" in i["nome"]), None)
        kpis = []
        if laudos:
            kpis.append({"v": str(laudos["tot"]), "l": "vistorias no período", "cls": ""})
            pct = laudos.get("pct")
            kpis.append({"v": f"{pct:.1f}%" if pct is not None else "—",
                         "l": "Laudo <48h", "cls": _kpi_cls(pct)})
        if efic:
            pct = efic.get("pct")
            kpis.append({"v": f"{pct:.1f}%" if pct is not None else "—",
                         "l": "Dentro do tempo padrão", "cls": _kpi_cls(pct)})
        if contest:
            pct = contest.get("pct")
            kpis.append({"v": f"{pct:.1f}%" if pct is not None else "—",
                         "l": "Contestações <24h", "cls": _kpi_cls(pct)})

    while len(kpis) < 4:
        kpis.append({"v": "—", "l": "", "cls": ""})
    return kpis[:4]


def _build_bar_h(proc: str, indicadores: list[dict]) -> dict:
    """Bar-h: todos indicadores não-bônus com label e pct vs meta 100."""
    normais = [i for i in indicadores if "★" not in i["nome"]]
    labels, data, metas = [], [], []
    for ind in normais:
        sn = _short_nome(ind["nome"])
        labels.append(f"{ind['resp']} {sn[:22]} ({ind['ok']}/{ind['tot']})")
        data.append(round(ind.get("pct") or 0, 1))
        metas.append(100)
    return {
        "tipo": "bar-h",
        "titulo": f"Indicadores · {proc}",
        "full": True,
        "labels": labels, "data": data, "metas": metas,
    }


def _build_bar_v(proc: str, pessoas: list) -> dict:
    """Bar-v: notas das pessoas que têm score nesse processo."""
    # Vistorias é caso especial: Marinho tem 'Vistorias' como score key combinada
    pares = []
    for p in pessoas:
        nota = p.get("scores", {}).get(proc)
        if nota is not None:
            pares.append((p["id"], NOMES_RESP.get(p["id"], p["id"]), nota))
    pares.sort(key=lambda x: x[2], reverse=True)
    labels = [r[1] for r in pares]
    data = [round(r[2], 3) for r in pares]
    colors = CORES_BARV[: len(pares)]
    return {
        "tipo": "bar-v", "titulo": "Notas",
        "labels": labels, "data": data, "colors": colors,
    }


def _build_indicadores_list(indicadores: list[dict]) -> list[dict]:
    """Espelho da lista, com nome curto e meta derivada."""
    out = []
    for ind in indicadores:
        out.append({
            "nome": _short_nome(ind["nome"]),
            "resp": ind["resp"],
            "meta": _meta_from_nome(ind["nome"]),
            "ok": ind["ok"],
            "tot": ind["tot"],
            "pct": ind.get("pct"),
        })
    return out


# ────────────────────────────────────────────────────────────────────
# Insights automáticos (3) — líder + gargalo + bônus/volume
# ────────────────────────────────────────────────────────────────────

def _insights_auto(proc: str, indicadores: list[dict], pessoas: list) -> list[dict]:
    """3 insights automáticos: SEMPRE pos para líder, neg para gargalo, pos/neu p/ bônus|volume."""
    insights: list[dict] = []
    normais = [i for i in indicadores if "★" not in i["nome"] and i.get("tot", 0) > 0]
    bonus_n = _bonus_total_proc(proc, pessoas)

    if normais:
        # Insight 1 — POS sempre para o líder (mesmo abaixo de 50%)
        lider = max(normais, key=lambda i: i.get("pct") or 0)
        pct_l = lider.get("pct") or 0
        if pct_l >= 50:
            txt = f"{lider['resp']} lidera {_short_nome(lider['nome'])}: {pct_l:.1f}%."
        else:
            txt = f"{lider['resp']} lidera com {pct_l:.1f}%, mas abaixo da meta."
        insights.append({"tipo": "pos", "txt": txt})

        # Insight 2 — NEG gargalo
        gargalo = min(normais, key=lambda i: i.get("pct") or 0)
        pct_g = gargalo.get("pct") or 0
        insights.append({
            "tipo": "neg",
            "txt": f"{gargalo['resp']} {_short_nome(gargalo['nome'])}: {pct_g:.1f}% — gargalo do processo.",
        })

    # Insight 3 — Bônus (POS) ou volume (NEU)
    if bonus_n > 0:
        label = {
            "Cont. ADM":     "vistorias de entrada criadas",
            "Inadimplência": "boletos cobrados antes do repasse",
            "Com. Locação":  "imóveis alugados antes de anunciados",
        }.get(proc, "bônus")
        insights.append({"tipo": "pos", "txt": f"★ Bônus: {bonus_n} {label}."})
    elif normais:
        total = sum(i.get("tot", 0) for i in normais)
        insights.append({"tipo": "neu", "txt": f"Volume de {total} cards no período."})
    else:
        insights.append({"tipo": "neu", "txt": "Volume baixo no período."})

    while len(insights) < 3:
        insights.append({"tipo": "neu", "txt": "—"})
    return insights[:3]


# ────────────────────────────────────────────────────────────────────
# Entry point
# ────────────────────────────────────────────────────────────────────

def _load_overrides() -> dict[str, list[dict]]:
    if not OVERRIDES_PATH.exists():
        return {}
    raw = json.loads(OVERRIDES_PATH.read_text(encoding="utf-8"))
    # remove chaves _comment
    return {k: v for k, v in raw.items() if not k.startswith("_")}


def gerar_proc_rich(pessoas: list[dict]) -> dict:
    """Retorna o dict PROC_RICH com as 13 chaves."""
    by_proc = _coletar_indicadores(pessoas)
    overrides = _load_overrides()
    out = {}
    for proc in PROC_KEYS_ORDEM:
        meta = PROC_META[proc]
        inds = by_proc.get(proc, [])
        insights = overrides.get(proc) or _insights_auto(proc, inds, pessoas)
        out[proc] = {
            "grupo": meta["grupo"],
            "titulo": meta["titulo"],
            "kpis": _build_kpis(proc, inds, pessoas),
            "charts": [_build_bar_h(proc, inds), _build_bar_v(proc, pessoas)],
            "indicadores": _build_indicadores_list(inds),
            "insights": insights,
        }
    return out
