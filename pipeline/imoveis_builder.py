"""
TRK Experience — Builder do dicionário IMOVEIS (drilldown property-level)
=========================================================================

Gera o dicionário IMOVEIS consumido pelo painel HTML (compatível com a 10ª Ed).
Cada chave produz {titulo, cols, rows} no formato exato esperado pelo JS do painel.

Reaproveita a lógica das funções `calc_*` de calculate.py para garantir
consistência: ok/tot do indicador no PESSOAS.detalhes bate com o número de
linhas marcadas ✓/✗ no IMOVEIS.

Status do tipo Octadesk e tipos de Bônus seguem regras específicas (★).
Status do tipo SLA é ✓ se atingiu a meta, ✗ caso contrário.
Ordenação padrão: pior caso primeiro (tempo decrescente), depois alfabético por IM.

Esta iteração implementa 5 chaves de teste cobrindo 4 tipos estruturais.
As outras 50 chaves serão adicionadas após validação do usuário.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent

from calculate import (
    excluir_rascunhos, aplicar_cutoff, filtrar_por_assignee, extrair_im, NOMES_AGENTE,
    RENOV_ANTECEDENCIA_MIN, _renov_nao_renova,
    _whatsapp_indicadores, _tickets_filtrados, _ticket_sla_ind, _ticket_aval_ind,
    horas_uteis, horas_uteis_fase, horas_corridas, dias_corridos,
    primeira_saida_fase, CUTOFF_CONT_ADM_CAIO_FIXO, _meta_tol,
    avaliar_eficiencia_vistoria,
    _expected_phase_desocupacao, _now_ref, _nome_assessora_alt, _contem_qualquer, _as_list,
    DIRF_DARF_ANO_BASE, DIRF_DARF_CUTOFF,
)
from datetime import datetime, timedelta


# ────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────

def _fmt_im(im: int | float | str) -> str:
    """Formata IM no padrão 'IMXXX' sem espaço."""
    try:
        return f"IM{int(float(im))}"
    except (ValueError, TypeError):
        return f"IM{im}"


def _fmt_horas(h: float) -> str:
    """Formata tempo em horas: 'X.Xh'."""
    if pd.isna(h):
        return "—"
    return f"{max(h, 0):.1f}h"


def _fmt_dias(d: float, *, signed: bool = False) -> str:
    """Formata em dias: 'Xd' (inteiro) ou 'X.Xd'. Se signed, preserva sinal."""
    if pd.isna(d):
        return "—"
    val = d if signed else max(d, 0)
    if abs(val - int(val)) < 0.05:
        return f"{int(val)}d"
    return f"{val:.1f}d"


def _extrair_im_do_titulo(titulo: str) -> Optional[int]:
    """'IM357 - CLN 412...' → 357. None se não casar."""
    m = re.match(r"IM\s*(\d+)", str(titulo).strip(), re.IGNORECASE)
    return int(m.group(1)) if m else None


def _im_label(card_row: pd.Series) -> str:
    """Coluna 'Imóvel' do drilldown.
    Se Título tem padrão 'IMXXX', usa esse. Caso contrário, fallback: 'IM#<card_id>'.
    """
    im = _extrair_im_do_titulo(card_row.get("Título", ""))
    if im is not None:
        return f"IM{im}"
    # fallback usando id do card Pipefy (sinaliza cadastro irregular)
    return f"IM#{card_row.get('id', '')}"


def _endereco_from_row(card_row: pd.Series) -> str:
    """Coluna 'Endereço' do drilldown — extrai o endereço significativo.
    Prioridade: campo 'Endereço' → 'Imóvel' (connector, lista) → Título sem prefixo 'IMXXX -'.
    """
    for c in ("Endereço", "Imóvel"):
        v = card_row.get(c)
        if isinstance(v, list):
            v = ", ".join(str(x) for x in v) if v else None
        if v and str(v).strip():
            return str(v).strip()
    titulo = str(card_row.get("Título", "")).strip()
    # remove prefixo "IM<num> -" ou "IM<num>/<n> -" ou "IM<num>:"
    cleaned = re.sub(r"^IM\s*\d+(?:/\d+)?\s*[-–|:]\s*", "", titulo, flags=re.IGNORECASE)
    return cleaned or titulo


def _ord_pior_primeiro(rows: list[list], idx_valor: int) -> list[list]:
    """Ordena rows por valor numérico no idx_valor (decrescente). Empate: alfabético IM."""
    def _key(r):
        v = r[idx_valor]
        # extrai número do formato 'X.Xh', 'Xd', 'X%', 'X', 'X/X'
        m = re.match(r"([\d.]+)", str(v))
        num = float(m.group(1)) if m else 0.0
        return (-num, str(r[0]))
    return sorted(rows, key=_key)


# ────────────────────────────────────────────────────────────────────
# CAIO — Comercial
# ────────────────────────────────────────────────────────────────────

def caio_inicio(df_comercial: pd.DataFrame, ref: pd.Timestamp) -> dict:
    """Caio · Comercial · Início <24h. Tempo entre Criado em e firstTimeIn Avaliação Técnica."""
    df = excluir_rascunhos(df_comercial)
    df = aplicar_cutoff(df, "Criado em", ref=ref)
    df = filtrar_por_assignee(df, "Profissional responsável", "Caio")
    col_avt_in = "Primeira vez que entrou na fase Avaliação Técnica"
    sub = df.dropna(subset=[col_avt_in]).copy()
    horas = sub.apply(lambda r: horas_uteis(r["Criado em"], r[col_avt_in]), axis=1)
    horas = horas.clip(lower=0)
    rows = []
    for (_, r), h in zip(sub.iterrows(), horas):
        rows.append([
            _im_label(r),
            r["Título"],
            _fmt_horas(h),
            "✓" if h <= _meta_tol(24) else "✗",
        ])
    ok = int((horas <= _meta_tol(24)).sum())
    return {
        "titulo": f"Caio — Comercial: Início processo <24h ({ok}/{len(sub)})",
        "cols": ["Imóvel", "Título", "Tempo", "Status"],
        "rows": _ord_pior_primeiro(rows, idx_valor=2),
    }


def caio_anuncio(df_comercial: pd.DataFrame, ref: pd.Timestamp) -> dict:
    """Caio · Comercial · Anúncio <72h. Tempo entre liberação (saída AvalTec OU Cadastro/NIDO) e publicação."""
    df = excluir_rascunhos(df_comercial)
    df = aplicar_cutoff(df, "Criado em", ref=ref)
    df = filtrar_por_assignee(df, "Profissional responsável", "Caio")
    col_avt_out = "Última vez que saiu da fase Avaliação Técnica"
    col_nido_out = "Última vez que saiu da fase Cadastro / Reativação no NIDO"
    col_pub = "Data publicação Anúncio"
    liberacao = df[col_avt_out].where(df[col_avt_out].notna(), df[col_nido_out])
    mask = liberacao.notna() | df[col_pub].notna()
    sub = df[mask].copy()
    lib2 = liberacao[mask]
    pub2 = sub[col_pub]
    horas = pd.Series([horas_uteis(i, f) for i, f in zip(lib2, pub2)], index=pub2.index)
    horas = horas.clip(lower=0)
    rows = []
    for (_, r), h in zip(sub.iterrows(), horas):
        rows.append([
            _im_label(r),
            r["Título"],
            _fmt_horas(h) if pd.notna(h) else "—",
            "✓" if (pd.notna(h) and h <= _meta_tol(72)) else "✗",
        ])
    ok = int((horas <= _meta_tol(72)).sum())
    return {
        "titulo": f"Caio — Comercial: Anúncio publicado <72h ({ok}/{len(sub)})",
        "cols": ["Imóvel", "Título", "Tempo", "Status"],
        "rows": _ord_pior_primeiro(rows, idx_valor=2),
    }


def caio_bonus(df_comercial: pd.DataFrame, df_cont_loc: pd.DataFrame, ref: pd.Timestamp) -> dict:
    """Caio · Comercial · Imóvel alugado antes de anunciado ★. IMs validados em config/bonus_caio.json.
    Lookup de título: 1º Comercial Caio → 2º Cont.Locação → 3º fallback texto.
    """
    cfg = json.loads((ROOT / "config" / "bonus_caio.json").read_text(encoding="utf-8"))
    # Mesma composição do N em run._contar_bonus_caio (Armadilha 1): continuação +
    # validados + override manual (IM143). Mantém drilldown↔pontuação consistentes.
    ims_validados = (cfg.get("edicao_12_continuacao", []) + cfg.get("edicao_12_validados", [])
                     + (cfg.get("edicao_12_override_incluir", {}) or {}).get("ims", []))

    com = excluir_rascunhos(df_comercial)
    com = filtrar_por_assignee(com, "Profissional responsável", "Caio").copy()
    com["_IM"] = com["Título"].apply(_extrair_im_do_titulo)
    cl = df_cont_loc.copy()
    cl["_IM"] = cl["Título"].apply(_extrair_im_do_titulo)

    rows = []
    for im in ims_validados:
        # 1) Comercial Caio
        m = com[com["_IM"] == im]
        if len(m) > 0:
            titulo = m.iloc[0]["Título"]
        else:
            # 2) Cont. Locação (cruzamento por IM no Título)
            m2 = cl[cl["_IM"] == im]
            titulo = m2.iloc[0]["Título"] if len(m2) > 0 else f"IM{im} — (sem dados)"
        rows.append([_fmt_im(im), titulo, "alugado sem anúncio", "★"])

    return {
        "titulo": f"Caio — Comercial: Imóvel alugado antes anunciado ★ ({len(ims_validados)} casos)",
        "cols": ["Imóvel", "Título", "Situação", "Bônus"],
        "rows": rows,
    }


# ────────────────────────────────────────────────────────────────────
# CAIO — chaves restantes
# ────────────────────────────────────────────────────────────────────

def caio_coluna(df_comercial: pd.DataFrame, ref: pd.Timestamp) -> dict:
    """Caio · Comercial · Coluna correta. Compara Fase atual com expected baseado em dias_desocup."""
    df = excluir_rascunhos(df_comercial)
    df = aplicar_cutoff(df, "Criado em", ref=ref)
    df = filtrar_por_assignee(df, "Profissional responsável", "Caio")
    col_cf_in = "Primeira vez que entrou na fase Conferência Final"
    col_pub = "Data publicação Anúncio"
    now = _now_ref(ref)
    mask = df[col_cf_in].notna() & (df["Fase atual"] != "Concluído")
    sub = df[mask].copy()
    dias_desocup = (now - sub[col_pub]).dt.total_seconds() / 86400.0
    rows = []
    for (_, r), d in zip(sub.iterrows(), dias_desocup):
        expected = _expected_phase_desocupacao(d)
        situacao = f"{int(d)}d → {expected}" if (pd.notna(d) and expected) else "—"
        status = "✓" if (expected is not None and r["Fase atual"] == expected) else "✗"
        rows.append([_im_label(r), r["Título"], situacao, status])
    ok = sum(1 for r in rows if r[3] == "✓")
    return {
        "titulo": f"Caio — Comercial: Coluna correta ({ok}/{len(sub)})",
        "cols": ["Imóvel", "Título", "Situação", "Status"],
        "rows": _ord_pior_primeiro(rows, idx_valor=2),
    }


def caio_ocupacao(df_comercial: pd.DataFrame, df_cont_loc: pd.DataFrame, ref: pd.Timestamp) -> dict:
    """Caio · Cont. Locação · Ocupação <30d. Cruzamento Comercial × Cont.Loc por IM."""
    com = excluir_rascunhos(df_comercial)
    com = aplicar_cutoff(com, "Criado em", ref=ref)
    com = filtrar_por_assignee(com, "Profissional responsável", "Caio")
    cl = excluir_rascunhos(df_cont_loc)
    cl = aplicar_cutoff(cl, "Criado em", ref=ref)

    col_pub = "Data publicação Anúncio"
    col_boleto = "Primeira vez que entrou na fase 1º Boleto"

    pub_por_im: dict[int, list[pd.Timestamp]] = {}
    for im_val, pub in com[["IM", col_pub]].dropna(subset=[col_pub]).itertuples(index=False):
        if pd.isna(im_val):
            continue
        pub_por_im.setdefault(int(im_val), []).append(pd.Timestamp(pub))

    rows = []
    for _, row in cl.dropna(subset=[col_boleto]).iterrows():
        im = extrair_im(row.get("Imóvel", "")) or _extrair_im_do_titulo(row.get("Título", ""))
        if im is None:
            continue
        bol = pd.Timestamp(row[col_boleto])
        pubs = sorted(pub_por_im.get(im, []))
        anteriores = [p for p in pubs if p <= bol]
        posteriores = [p for p in pubs if p > bol]
        if not anteriores:
            continue  # sem anúncio anterior (excluído ou sem dados)
        dias = max((bol - anteriores[-1]).total_seconds() / 86400.0, 0.0)
        rows.append([
            _im_label(row), row["Título"],
            _fmt_dias(dias), "✓" if dias <= 30 else "✗",
        ])
    ok = sum(1 for r in rows if r[3] == "✓")
    return {
        "titulo": f"Caio — Cont. Locação: Ocupação <30d ({ok}/{len(rows)})",
        "cols": ["Imóvel", "Título", "Dias", "Status"],
        "rows": _ord_pior_primeiro(rows, idx_valor=2),
    }


def caio_docs(df_cont_loc: pd.DataFrame, ref: pd.Timestamp) -> dict:
    """Caio · Cont. Locação · Documentação <24h úteis."""
    cl = excluir_rascunhos(df_cont_loc)
    cl = aplicar_cutoff(cl, "Criado em", ref=ref)
    col_conf_in = "Primeira vez que entrou na fase Confecção do contrato de locação"
    sub = cl.dropna(subset=[col_conf_in]).copy()
    rows = []
    for _, r in sub.iterrows():
        h = horas_uteis(r["Criado em"], r[col_conf_in])
        rows.append([
            _im_label(r), r["Título"],
            _fmt_horas(h), "✓" if h <= _meta_tol(24) else "✗",
        ])
    ok = sum(1 for r in rows if r[3] == "✓")
    return {
        "titulo": f"Caio — Cont. Locação: Documentação <24h ({ok}/{len(sub)})",
        "cols": ["Imóvel", "Título", "Tempo", "Status"],
        "rows": _ord_pior_primeiro(rows, idx_valor=2),
    }


def caio_cadm(df_cont_adm: pd.DataFrame, ref: pd.Timestamp) -> dict:
    """Caio · Cont. ADM · Criação→NIDO <7d. Cutoff FIXO 01/03/2026."""
    df = excluir_rascunhos(df_cont_adm)
    df = aplicar_cutoff(df, "Criado em", data_fixa=CUTOFF_CONT_ADM_CAIO_FIXO)
    col_nido = "Primeira vez que entrou na fase Contrato assinado - Conferir Nido"
    sub = df.dropna(subset=[col_nido]).copy()
    dias = (sub[col_nido] - sub["Criado em"]).dt.total_seconds() / 86400.0
    dias = dias.clip(lower=0)
    rows = []
    for (_, r), d in zip(sub.iterrows(), dias):
        rows.append([
            _im_label(r), r["Título"],
            _fmt_dias(d), "✓" if d < 7 else "✗",
        ])
    ok = sum(1 for r in rows if r[3] == "✓")
    return {
        "titulo": f"Caio — Cont. ADM: Criação→NIDO <7d ({ok}/{len(sub)})",
        "cols": ["Imóvel", "Título", "Dias", "Status"],
        "rows": _ord_pior_primeiro(rows, idx_valor=2),
    }


def caio_renov(df_renov: pd.DataFrame, ref: pd.Timestamp) -> dict:
    """Caio · Renovação · Avaliação >90d antes do vencimento."""
    df = excluir_rascunhos(df_renov)
    df = aplicar_cutoff(df, "Criado em", ref=ref)
    col_aval_out = "Última vez que saiu da fase Avaliação de mercado"
    col_venc = "Data de vencimento"
    sub = df.dropna(subset=[col_aval_out, col_venc]).copy()
    dias = (sub[col_venc] - sub[col_aval_out]).dt.total_seconds() / 86400.0
    rows = []
    for (_, r), d in zip(sub.iterrows(), dias):
        endereco = r.get("Endereço") or r.get("Imóvel") or r["Título"]
        if isinstance(endereco, list):
            endereco = ", ".join(str(x) for x in endereco) if endereco else r["Título"]
        rows.append([
            _im_label(r), str(endereco),
            _fmt_dias(d, signed=True), "✓" if d > 90 else "✗",
        ])
    ok = sum(1 for r in rows if r[3] == "✓")
    return {
        "titulo": f"Caio — Renovação: Avaliação >90d ({ok}/{len(sub)})",
        "cols": ["Imóvel", "Endereço", "Dias", "Status"],
        "rows": _ord_pior_primeiro(rows, idx_valor=2),
    }


# ────────────────────────────────────────────────────────────────────
# VIVIANNE — 13 chaves Pipefy
# ────────────────────────────────────────────────────────────────────

def _gen_indicador_horas(df: pd.DataFrame, col_in: str, col_out: str,
                          meta_h: float, titulo: str, modo: str = "uteis") -> dict:
    """Helper genérico: gera dict IMOVEIS para indicador de tempo (úteis ou corrido)."""
    sub = df.dropna(subset=[col_in, col_out]).copy()
    if modo == "uteis":
        horas = sub.apply(lambda r: horas_uteis(r[col_in], r[col_out]), axis=1)
    else:
        horas = (sub[col_out] - sub[col_in]).dt.total_seconds() / 3600
        horas = horas.clip(lower=0)
    rows = []
    for (_, r), h in zip(sub.iterrows(), horas):
        rows.append([_im_label(r), r["Título"], _fmt_horas(h), "✓" if h <= _meta_tol(meta_h) else "✗"])
    ok = sum(1 for r in rows if r[3] == "✓")
    return {
        "titulo": titulo.format(ok=ok, tot=len(sub)),
        "cols": ["Imóvel", "Título", "Tempo", "Status"],
        "rows": _ord_pior_primeiro(rows, idx_valor=2),
    }


def _gen_indicador_uteis_fase(df: pd.DataFrame, fase: str, meta_h: float, titulo: str) -> dict:
    """
    Drilldown de indicador em horas ÚTEIS dentro de UMA fase, robusto a reabertura.
    Espelha calc_*_contrato_adm: usa calculate.horas_uteis_fase (mesma fonte de
    verdade do ✓/✗ da pontuação — ver Armadilha 1 do CHECKLIST).
    """
    col_in = f"Primeira vez que entrou na fase {fase}"
    col_lastin = f"Última vez que entrou na fase {fase}"
    col_out = f"Última vez que saiu da fase {fase}"
    col_dur = f"Tempo total na fase {fase} (dias)"
    sub = df.dropna(subset=[col_in, col_out]).copy()
    horas = sub.apply(
        lambda r: horas_uteis_fase(r[col_in], r.get(col_lastin), r[col_out], r.get(col_dur)),
        axis=1,
    )
    rows = []
    for (_, r), h in zip(sub.iterrows(), horas):
        rows.append([_im_label(r), r["Título"], _fmt_horas(h), "✓" if h <= _meta_tol(meta_h) else "✗"])
    ok = sum(1 for r in rows if r[3] == "✓")
    return {
        "titulo": titulo.format(ok=ok, tot=len(sub)),
        "cols": ["Imóvel", "Título", "Tempo", "Status"],
        "rows": _ord_pior_primeiro(rows, idx_valor=2),
    }


def _gen_indicador_tempo_col(df: pd.DataFrame, col_tempo_dias: str, meta_h: float,
                              titulo: str, cols_endereco: bool = False) -> dict:
    """Helper genérico para 'Tempo total na fase X (dias)'.

    HORAS ÚTEIS desde 12/08/2026 (decisão da gestora): antes era × 24 (corrido).
    A fase é derivada do próprio nome da coluna, então o denominador continua
    exatamente o mesmo do calculate.py — só a medida do tempo muda (Armadilha 1).
    """
    fase = col_tempo_dias[len("Tempo total na fase "):-len(" (dias)")]
    sub = df.dropna(subset=[col_tempo_dias]).copy()
    horas = sub.apply(lambda r: horas_uteis_fase(
        r.get(f"Primeira vez que entrou na fase {fase}"),
        r.get(f"Última vez que entrou na fase {fase}"),
        r.get(f"Última vez que saiu da fase {fase}"),
        r.get(col_tempo_dias)), axis=1)
    rows = []
    for (_, r), h in zip(sub.iterrows(), horas):
        end_col = _endereco_from_row(r) if cols_endereco else r["Título"]
        rows.append([_im_label(r), end_col, _fmt_horas(h), "✓" if h <= _meta_tol(meta_h) else "✗"])
    ok = sum(1 for r in rows if r[3] == "✓")
    return {
        "titulo": titulo.format(ok=ok, tot=len(sub)),
        "cols": ["Imóvel", "Endereço" if cols_endereco else "Título", "Tempo", "Status"],
        "rows": _ord_pior_primeiro(rows, idx_valor=2),
    }


def vivi_cadm(df_cont_adm: pd.DataFrame, ref: pd.Timestamp) -> dict:
    """Vivianne · Cont. ADM · Confecção <2h ÚTEIS (robusto a reabertura — 12ª Ed)."""
    df = excluir_rascunhos(df_cont_adm)
    df = aplicar_cutoff(df, "Criado em", ref=ref)
    return _gen_indicador_uteis_fase(
        df, "Confecção do contrato",
        2, "Vivianne — Cont. ADM: Confecção <2h ({ok}/{tot})",
    )


def vivi_resc_adm(df_resc_adm: pd.DataFrame, ref: pd.Timestamp) -> dict:
    """Vivianne · Rescisão ADM · Encerramento <4h CORRIDO (duration cumulativo, espelha calc_vivianne_rescisao_adm)."""
    df = excluir_rascunhos(df_resc_adm)
    df = aplicar_cutoff(df, "Criado em", ref=ref)
    return _gen_indicador_tempo_col(
        df,
        "Tempo total na fase Encerramento (dias)",
        4, "Vivianne — Resc. ADM: Encerramento <4h ({ok}/{tot})",
    )


def vivi_nido(df_cont_loc: pd.DataFrame, ref: pd.Timestamp) -> dict:
    """Vivianne · Cont. Locação · NIDO→Concluído <24h CORRIDO."""
    df = excluir_rascunhos(df_cont_loc)
    df = aplicar_cutoff(df, "Criado em", ref=ref)
    return _gen_indicador_horas(
        df,
        "Primeira vez que entrou na fase Fechamento NIDO",
        "Primeira vez que entrou na fase Concluído",
        24, "Vivianne — Cont. Locação: NIDO→Concluído <24h ({ok}/{tot})",
        modo="uteis",   # horas úteis desde 12/08/2026
    )


def vivi_confec_loc(df_cont_loc: pd.DataFrame, ref: pd.Timestamp) -> dict:
    """Vivianne · Cont. Locação · Confecção <2h CORRIDO (via Tempo total na fase × 24)."""
    df = excluir_rascunhos(df_cont_loc)
    df = aplicar_cutoff(df, "Criado em", ref=ref)
    return _gen_indicador_tempo_col(
        df,
        "Tempo total na fase Confecção do contrato de locação (dias)",
        2, "Vivianne — Cont. Locação: Confecção <2h ({ok}/{tot})",
    )


def vivi_lev_prop(df_resc_loc: pd.DataFrame, ref: pd.Timestamp) -> dict:
    """Vivianne · Rescisão Loc. · Levant. Taxas Prop <2h CORRIDO (Tempo total × 24)."""
    df = excluir_rascunhos(df_resc_loc)
    df = aplicar_cutoff(df, "Criado em", ref=ref)
    return _gen_indicador_tempo_col(
        df,
        "Tempo total na fase Levant. Taxas Proporcionais (dias)",
        2, "Vivianne — Resc. Loc.: Levant. Taxas Prop <2h ({ok}/{tot})",
    )


def vivi_lev_final(df_resc_loc: pd.DataFrame, ref: pd.Timestamp) -> dict:
    """Vivianne · Rescisão Loc. · Levantamento de taxas <2h CORRIDO (Tempo total × 24)."""
    df = excluir_rascunhos(df_resc_loc)
    df = aplicar_cutoff(df, "Criado em", ref=ref)
    return _gen_indicador_tempo_col(
        df,
        "Tempo total na fase Levantamento de taxas (dias)",
        2, "Vivianne — Resc. Loc.: Levant. Taxas Final <2h ({ok}/{tot})",
    )


def vivi_ren_confec(df_renov: pd.DataFrame, ref: pd.Timestamp) -> dict:
    """Vivianne · Renovação · Confecção <4h CORRIDO (Tempo total × 24)."""
    df = excluir_rascunhos(df_renov)
    df = aplicar_cutoff(df, "Criado em", ref=ref)
    return _gen_indicador_tempo_col(
        df,
        "Tempo total na fase Confecção do contrato (dias)",
        4, "Vivianne — Renovação: Confecção <4h ({ok}/{tot})",
        cols_endereco=True,
    )


def vivi_ren_final(df_renov: pd.DataFrame, ref: pd.Timestamp) -> dict:
    """Vivianne · Renovação · Finalização <16h ÚTEIS."""
    df = excluir_rascunhos(df_renov)
    df = aplicar_cutoff(df, "Criado em", ref=ref)
    col_in = "Primeira vez que entrou na fase Contrato assinado / Finalizar"
    col_out = "Primeira vez que entrou na fase Processo concluído"
    sub = df.dropna(subset=[col_in, col_out]).copy()
    horas = sub.apply(lambda r: horas_uteis(r[col_in], r[col_out]), axis=1)
    rows = []
    for (_, r), h in zip(sub.iterrows(), horas):
        rows.append([_im_label(r), _endereco_from_row(r), _fmt_horas(h), "✓" if h <= _meta_tol(16) else "✗"])
    ok = sum(1 for r in rows if r[3] == "✓")
    return {
        "titulo": f"Vivianne — Renovação: Finalização <16h ({ok}/{len(sub)})",
        "cols": ["Imóvel", "Endereço", "Tempo", "Status"],
        "rows": _ord_pior_primeiro(rows, idx_valor=2),
    }


def vivi_cob(df_inad: pd.DataFrame, ref: pd.Timestamp) -> dict:
    """Vivianne · Inadimplência · Cobrança <24h CORRIDO (Criado em → entrada Cobrança inicial)."""
    df = excluir_rascunhos(df_inad)
    df = aplicar_cutoff(df, "Criado em", ref=ref)
    col_cob = "Primeira vez que entrou na fase Cobrança (inicial)"
    sub = df.dropna(subset=[col_cob]).copy()
    horas = sub.apply(lambda r: horas_uteis(r["Criado em"], r[col_cob]), axis=1)
    horas = horas.clip(lower=0)
    rows = []
    for (_, r), h in zip(sub.iterrows(), horas):
        rows.append([_im_label(r), _endereco_from_row(r), _fmt_horas(h), "✓" if h <= _meta_tol(8) else "✗"])
    ok = sum(1 for r in rows if r[3] == "✓")
    return {
        "titulo": f"Vivianne — Inadim.: Cobrança <8h úteis ({ok}/{len(sub)})",
        "cols": ["Imóvel", "Endereço", "Tempo", "Status"],
        "rows": _ord_pior_primeiro(rows, idx_valor=2),
    }


def vivi_cred(df_inad: pd.DataFrame, ref: pd.Timestamp) -> dict:
    """Vivianne · Inadimplência · CredPago ≤15d CORRIDO (Vencimento 1º Boleto → entrada CredPago)."""
    df = excluir_rascunhos(df_inad)
    df = aplicar_cutoff(df, "Criado em", ref=ref)
    col_venc = "Vencimento 1º Boleto:"
    col_cred = "Primeira vez que entrou na fase CredPago: Acionar"
    sub = df.dropna(subset=[col_venc, col_cred]).copy()
    dias = (sub[col_cred] - sub[col_venc]).dt.total_seconds() / 86400
    dias = dias.clip(lower=0)
    rows = []
    for (_, r), d in zip(sub.iterrows(), dias):
        rows.append([_im_label(r), _endereco_from_row(r), _fmt_dias(d), "✓" if d <= 15 else "✗"])
    ok = sum(1 for r in rows if r[3] == "✓")
    return {
        "titulo": f"Vivianne — Inadim.: CredPago ≤15d ({ok}/{len(sub)})",
        "cols": ["Imóvel", "Endereço", "Dias", "Status"],
        "rows": _ord_pior_primeiro(rows, idx_valor=2),
    }


def vivi_neg(df_inad: pd.DataFrame, ref: pd.Timestamp) -> dict:
    """Vivianne · Inadimplência · Negativação 7-9d CORRIDO. ATENÇÃO: dupla condição (≥7 E ≤9)."""
    df = excluir_rascunhos(df_inad)
    df = aplicar_cutoff(df, "Criado em", ref=ref)
    col_venc = "Vencimento 1º Boleto:"
    col_neg = "Primeira vez que entrou na fase Negativação (No 8º dia de atraso)"
    sub = df.dropna(subset=[col_venc, col_neg]).copy()
    dias = (sub[col_neg] - sub[col_venc]).dt.total_seconds() / 86400
    rows = []
    for (_, r), d in zip(sub.iterrows(), dias):
        rows.append([_im_label(r), _endereco_from_row(r),
                     _fmt_dias(d, signed=True),
                     "✓" if (7 <= d <= 9) else "✗"])
    ok = sum(1 for r in rows if r[3] == "✓")
    return {
        "titulo": f"Vivianne — Inadim.: Negativação 7-9d ({ok}/{len(sub)})",
        "cols": ["Imóvel", "Endereço", "Dias", "Status"],
        "rows": _ord_pior_primeiro(rows, idx_valor=2),
    }


def vivi_bo_concl(df_bo: pd.DataFrame, ref: pd.Timestamp) -> dict:
    """Vivianne · BackOffice · Concluído <24h CORRIDO (apenas cards SEM Troca de Titularidade)."""
    df = excluir_rascunhos(df_bo)
    df = aplicar_cutoff(df, "Criado em", ref=ref)
    col_troca = "Primeira vez que entrou na fase ↪️ Troca de Titularidade"
    col_concl = "Primeira vez que entrou na fase Concluído"
    sem_troca = df[df[col_troca].isna()].copy()
    sub = sem_troca.dropna(subset=[col_concl]).copy()
    horas = sub.apply(lambda r: horas_uteis(r["Criado em"], r[col_concl]), axis=1)
    rows = []
    for (_, r), h in zip(sub.iterrows(), horas):
        rows.append([_im_label(r), r["Título"], _fmt_horas(h), "✓" if h <= _meta_tol(24) else "✗"])
    ok = sum(1 for r in rows if r[3] == "✓")
    return {
        "titulo": f"Vivianne — BackOffice: Concluído <24h ({ok}/{len(sub)})",
        "cols": ["Imóvel", "Título", "Tempo", "Status"],
        "rows": _ord_pior_primeiro(rows, idx_valor=2),
    }


def vivi_bo_troca(df_bo: pd.DataFrame, ref: pd.Timestamp) -> dict:
    """Vivianne · BackOffice · Troca Titularidade <5d ÚTEIS (=50h úteis). Cards COM Troca."""
    df = excluir_rascunhos(df_bo)
    df = aplicar_cutoff(df, "Criado em", ref=ref)
    col_troca = "Primeira vez que entrou na fase ↪️ Troca de Titularidade"
    col_concl = "Primeira vez que entrou na fase Concluído"
    com_troca = df[df[col_troca].notna()].copy()
    sub = com_troca.dropna(subset=[col_concl]).copy()
    horas = sub.apply(lambda r: horas_uteis(r["Criado em"], r[col_concl]), axis=1)
    rows = []
    for (_, r), h in zip(sub.iterrows(), horas):
        rows.append([_im_label(r), r["Título"], _fmt_horas(h), "✓" if h <= 50 else "✗"])
    ok = sum(1 for r in rows if r[3] == "✓")
    return {
        "titulo": f"Vivianne — BackOffice: Troca Titularidade <5d ({ok}/{len(sub)})",
        "cols": ["Imóvel", "Título", "Tempo", "Status"],
        "rows": _ord_pior_primeiro(rows, idx_valor=2),
    }


# ────────────────────────────────────────────────────────────────────
# VIVIANNE — Inadimplência (bônus agregado)
# ────────────────────────────────────────────────────────────────────

def _ed_inadim() -> dict:
    return json.loads((ROOT / "config" / "bonus_vivianne.json").read_text(encoding="utf-8"))["edicao_12"]


def vivi_cobertura() -> dict:
    """Vivianne · Inadim.: COBERTURA — dos boletos em atraso, em quantos abriu cobrança."""
    ed = _ed_inadim()
    cobrados = ed["antes_count"] + ed["depois_count"]
    denom = ed["denominador_R1"]
    return {
        "titulo": f"Vivianne — Inadim.: Cobrança dos boletos em atraso ({cobrados}/{denom})",
        "cols": ["Categoria", "Quantidade", "Status"],
        "rows": [
            ["✓ Cobrança proativa aberta (card antes ou no dia do pagamento)", str(cobrados), "✓"],
            ["✗ Sem card no mês esperado — passou batido", str(ed["sem_card_count"]), "✗"],
            ["✗ Cobrança reativa (card criado depois do pagamento)", str(ed["reativos_count"]), "✗"],
        ],
    }


def vivi_bonus_inadim() -> dict:
    """Vivianne · Inadim.: RESULTADO — dos boletos cobrados, quantos entraram antes do repasse."""
    ed = _ed_inadim()
    cobrados = ed["antes_count"] + ed["depois_count"]
    return {
        "titulo": f"Vivianne — Inadim.: Recebido antes do repasse ({ed['antes_count']}/{cobrados})",
        "cols": ["Categoria", "Quantidade", "Status"],
        "rows": [
            ["✓ Pago até a data do repasse ao proprietário", str(ed["antes_count"]), "✓"],
            ["✗ Pago depois do repasse — entrou no mês seguinte", str(ed["depois_count"]), "✗"],
        ],
    }


# ────────────────────────────────────────────────────────────────────
# ASSESSORAS — 12 funções parametrizadas (geram 24 chaves: nat_X / gar_X)
# ────────────────────────────────────────────────────────────────────

def _vist_preenchida(v) -> bool:
    """True se 'Criar Card de Vistoria Técnica' tem conteúdo não-vazio."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return False
    if isinstance(v, list):
        return len(v) > 0
    s = str(v).strip()
    return s not in ("", "[]", "null", "None")


def _label_pessoa(assessora: str) -> str:
    return "Natália" if assessora == "natalia" else "Gardênia"


def assessora_cadm(df_cont_adm: pd.DataFrame, assessora: str, ref: pd.Timestamp) -> dict:
    """Cont. ADM · Conferência ≤2h ÚTEIS. Filtro Assessor (lista) + regra Gardênia."""
    df = excluir_rascunhos(df_cont_adm)
    df = aplicar_cutoff(df, "Criado em", ref=ref)
    nomes = _nome_assessora_alt(assessora)
    mask = df["Assessor (lista)"].apply(lambda v: _contem_qualquer(v, nomes))
    if assessora == "gardenia":
        sem_assessor = df["Assessor (lista)"].apply(lambda v: not _as_list(v))
        concluido = df["Primeira vez que entrou na fase Concluído"].notna()
        mask = mask | (sem_assessor & concluido)
    df_assess = df[mask].copy()
    # Robusto a reabertura (12ª Ed): mesma fonte de verdade da pontuação.
    return _gen_indicador_uteis_fase(
        df_assess, "Conferência do contrato",
        2, f"{_label_pessoa(assessora)} — Cont. ADM: Conferência ≤2h ({{ok}}/{{tot}})",
    )


def assessora_cadm_bonus(df_cont_adm: pd.DataFrame, assessora: str, ref: pd.Timestamp) -> dict:
    """Cont. ADM Bônus · Vistoria de entrada realizada ★. Mesma regra de _contar_bonus_assessora."""
    df = excluir_rascunhos(df_cont_adm)
    df = aplicar_cutoff(df, "Criado em", ref=ref)
    col_vist = "Criar Card de Vistoria Técnica"
    col_assess = "Assessor (lista)"
    nomes = _nome_assessora_alt(assessora)
    mask_nome = df[col_assess].apply(lambda v: _contem_qualquer(v, nomes))
    if assessora == "gardenia":
        sem_assessor = df[col_assess].apply(lambda v: not _as_list(v))
        concluido = df.get("Primeira vez que entrou na fase Concluído",
                            pd.Series(pd.NaT, index=df.index)).notna()
        mask_nome = mask_nome | (sem_assessor & concluido)
    mask_final = mask_nome & df[col_vist].apply(_vist_preenchida)
    sub = df[mask_final]
    rows = []
    for _, r in sub.iterrows():
        rows.append([_im_label(r), r["Título"], "vistoria criada", "★"])
    label = _label_pessoa(assessora)
    return {
        "titulo": f"{label} — Cont. ADM: Vistoria de entrada ★ ({len(sub)})",
        "cols": ["Imóvel", "Título", "Situação", "Bônus"],
        "rows": rows,
    }


def _resc_adm_recorte(df_resc_adm: pd.DataFrame, assessora: str, ref: pd.Timestamp) -> pd.DataFrame:
    """Recorte comum da Rescisão ADM (13ª Ed): assessora + última saída da Caixa em 180d."""
    df = excluir_rascunhos(df_resc_adm)
    nomes = _nome_assessora_alt(assessora)
    df = df[df["Assessor (lista)"].apply(lambda v: _contem_qualquer(v, nomes))].copy()
    return aplicar_cutoff(df, "Última vez que saiu da fase Caixa de entrada", ref=ref)


def assessora_resc_adm_ali(df_resc_adm: pd.DataFrame, assessora: str, ref: pd.Timestamp) -> dict:
    """Rescisão ADM · Alinhamento com o proprietário ≤24h (soma do tempo na fase)."""
    df = _resc_adm_recorte(df_resc_adm, assessora, ref)
    col_dur = "Tempo total na fase Alinhamento com o proprietário (dias)"
    if col_dur in df.columns:
        horas = pd.to_numeric(df[col_dur], errors="coerce") * 24
    else:
        horas = pd.Series(dtype="float64", index=df.index)
    sub = df[horas.notna() & (horas > 0)]
    rows = []
    for (_, r), h in zip(sub.iterrows(), horas.loc[sub.index]):
        rows.append([_im_label(r), r["Título"], _fmt_horas(h),
                     "✓" if h <= _meta_tol(24) else "✗"])
    ok = sum(1 for r in rows if r[3] == "✓")
    return {
        "titulo": f"{_label_pessoa(assessora)} — Resc. ADM: Alinhamento ≤24h ({ok}/{len(sub)})",
        "cols": ["Imóvel", "Título", "Tempo na fase", "Status"],
        "rows": _ord_pior_primeiro(rows, idx_valor=2),
    }


def assessora_resc_adm_concl(df_resc_adm: pd.DataFrame, assessora: str, ref: pd.Timestamp) -> dict:
    """Rescisão ADM · Conclusão ≤10 dias.
    1ª saída da Caixa de entrada → 1ª saída do Repasse final (primeira_saida_fase).
    Denominador: cards que entraram no Repasse. Entrou e não saiu = ✗.
    """
    df = _resc_adm_recorte(df_resc_adm, assessora, ref)
    F_CX, F_REP = "Caixa de entrada", "Repasse final / Distrato (FINANCEIRO)"
    col_rep_in = f"Primeira vez que entrou na fase {F_REP}"
    sub = df.dropna(subset=[col_rep_in]).copy()
    rows = []
    for _, r in sub.iterrows():
        ini = primeira_saida_fase(r.get(f"Primeira vez que entrou na fase {F_CX}"),
                                  r.get(f"Última vez que entrou na fase {F_CX}"),
                                  r.get(f"Última vez que saiu da fase {F_CX}"),
                                  r.get(f"Tempo total na fase {F_CX} (dias)"))
        fim = primeira_saida_fase(r.get(col_rep_in),
                                  r.get(f"Última vez que entrou na fase {F_REP}"),
                                  r.get(f"Última vez que saiu da fase {F_REP}"),
                                  r.get(f"Tempo total na fase {F_REP} (dias)"))
        if pd.isna(ini) or pd.isna(fim):
            rows.append([_im_label(r), r["Título"], "em andamento", "✗"])
        else:
            # dias_corridos() zera negativos; aqui negativo = passagem-fantasma
            # (card arrastado no fechamento) e conta ✗ — ver calculate.py.
            d = (pd.Timestamp(fim) - pd.Timestamp(ini)).total_seconds() / 86400
            rotulo = f"{d:.1f}d" if d >= 0 else f"{d:.1f}d (arrasto)"
            rows.append([_im_label(r), r["Título"], rotulo, "✓" if 0 <= d <= 10 else "✗"])
    ok = sum(1 for r in rows if r[3] == "✓")
    return {
        "titulo": f"{_label_pessoa(assessora)} — Resc. ADM: Conclusão ≤10 dias ({ok}/{len(sub)})",
        "cols": ["Imóvel", "Título", "Tempo", "Status"],
        "rows": _ord_pior_primeiro(rows, idx_valor=2),
    }


def assessora_resc_adm_dist(df_resc_adm: pd.DataFrame, assessora: str, ref: pd.Timestamp) -> dict:
    """Rescisão ADM · Distrato assinado — INDICADOR peso 3 (13ª Ed, 13/08/2026).
    Era bônus; virou indicador porque tem denominador natural (cards concluídos,
    campo preenchido com Sim ou Não). Cards com o campo vazio ficam FORA."""
    df = _resc_adm_recorte(df_resc_adm, assessora, ref)
    col_concl = "Primeira vez que entrou na fase Concluído"
    sub = df.dropna(subset=[col_concl]) if col_concl in df.columns else df.iloc[0:0]
    rows = []
    for _, r in sub.iterrows():                       # espelha calculate.py
        raw = r.get("Termo de Distrato assinado", "")
        val = "" if pd.isna(raw) else str(raw).strip()
        is_sim = val.lower() == "sim"
        rotulo = val if val and val.lower() not in ("nan", "none") else "(em branco)"
        rows.append([_im_label(r), r["Título"], rotulo, "✓" if is_sim else "✗"])
    ok = sum(1 for r in rows if r[3] == "✓")
    # ordena: ✗ primeiro (problemas), ✓ depois — empate alfabético
    rows.sort(key=lambda r: (r[3] == "✓", str(r[0])))
    return {
        "titulo": f"{_label_pessoa(assessora)} — Resc. ADM: Distrato assinado ({ok}/{len(sub)})",
        "cols": ["Imóvel", "Título", "Distrato", "Status"],
        "rows": rows,
    }


def _inicio_rescisao_loc(df: pd.DataFrame,
                        distratos: dict | None = None) -> tuple[pd.Series, pd.Series]:
    """Início de Boleto prop/final — espelha calculate.calc_assessora_rescisao_locacao.
    Prioridade (13ª Ed): data_distrato do Imobiliar → campo Pipefy →
    fase CHAVES RECEBIDAS → fallback por indicador.
    """
    chaves_campo = df["Data do recebimento das chaves:"]
    chaves_fase = df.get("Primeira vez que entrou na fase CHAVES RECEBIDAS",
                          pd.Series(pd.NaT, index=df.index))
    sai_vist = df["Última vez que saiu da fase Vistoria recebida"]
    sai_agend = df["Última vez que saiu da fase Agendamento de vistoria"]

    distratos = distratos or {}
    def _distrato(r):
        im = extrair_im(r.get("Imóvel")) or extrair_im(r.get("Título"))
        return distratos.get(im, pd.NaT) if im is not None else pd.NaT
    chaves_imob = (df.apply(_distrato, axis=1) if len(df)
                   else pd.Series(pd.NaT, index=df.index))
    chaves_imob = pd.to_datetime(chaves_imob, errors="coerce", utc=True)

    chaves_efetivas = chaves_imob.where(chaves_imob.notna(), chaves_campo)
    chaves_efetivas = chaves_efetivas.where(chaves_efetivas.notna(), chaves_fase)
    inicio_prop = chaves_efetivas.where(chaves_efetivas.notna(), sai_vist)
    inicio_final = chaves_efetivas.where(chaves_efetivas.notna(), sai_agend)
    return inicio_prop, inicio_final


def assessora_rl_prop(df_resc_loc: pd.DataFrame, assessora: str, ref: pd.Timestamp,
                      distratos: dict | None = None) -> dict:
    """Rescisão Loc. · Boleto prop ≤48h CORRIDO a partir da entrega das chaves.
    48h = "até o fim do dia seguinte", porque data_distrato não tem hora (13ª Ed).
    Negativo (levantamento antes da entrega) sai do denominador → linha 'revisar'.
    """
    df = excluir_rascunhos(df_resc_loc)
    df = aplicar_cutoff(df, "Criado em", ref=ref)
    nomes = _nome_assessora_alt(assessora)
    df = df[df["Assessor (lista)"].apply(lambda v: _contem_qualquer(v, nomes))].copy()
    inicio_prop, _ = _inicio_rescisao_loc(df, distratos)
    col_lev_prop = "Primeira vez que entrou na fase Levant. Taxas Proporcionais"
    mask = inicio_prop.notna() & df[col_lev_prop].notna()
    sub = df[mask].copy()
    horas = (df.loc[mask, col_lev_prop] - inicio_prop[mask]).dt.total_seconds() / 3600
    rows, tot = [], 0
    for (_, r), h in zip(sub.iterrows(), horas):
        if h < 0:
            rows.append([_im_label(r), r["Título"], f"{h:.1f}h", "revisar"])
        else:
            tot += 1
            rows.append([_im_label(r), r["Título"], _fmt_horas(h),
                         "✓" if h <= 48 else "✗"])   # 48h já é a folga; sem tolerância
    ok = sum(1 for r in rows if r[3] == "✓")
    return {
        "titulo": f"{_label_pessoa(assessora)} — Resc. Loc.: Boleto prop <48h ({ok}/{tot})",
        "cols": ["Imóvel", "Título", "Tempo", "Status"],
        "rows": _ord_pior_primeiro(rows, idx_valor=2),
    }


def assessora_rl_final(df_resc_loc: pd.DataFrame, assessora: str, ref: pd.Timestamp,
                       distratos: dict | None = None) -> dict:
    """Rescisão Loc. · Boleto final <15d CORRIDO. Nova regra de início (11ª Ed)."""
    df = excluir_rascunhos(df_resc_loc)
    df = aplicar_cutoff(df, "Criado em", ref=ref)
    nomes = _nome_assessora_alt(assessora)
    df = df[df["Assessor (lista)"].apply(lambda v: _contem_qualquer(v, nomes))].copy()
    _, inicio_final = _inicio_rescisao_loc(df, distratos)
    col_env_bol = "Primeira vez que entrou na fase Envio do boleto final"
    mask = inicio_final.notna() & df[col_env_bol].notna()
    sub = df[mask].copy()
    dias = (df.loc[mask, col_env_bol] - inicio_final[mask]).dt.total_seconds() / 86400
    rows, tot = [], 0
    for (_, r), d in zip(sub.iterrows(), dias):
        if d < 0:
            rows.append([_im_label(r), r["Título"], f"{d:.1f}d", "revisar"])
        else:
            tot += 1
            rows.append([_im_label(r), r["Título"], _fmt_dias(d), "✓" if d <= 15 else "✗"])
    ok = sum(1 for r in rows if r[3] == "✓")
    return {
        "titulo": f"{_label_pessoa(assessora)} — Resc. Loc.: Boleto final <15d ({ok}/{tot})",
        "cols": ["Imóvel", "Título", "Dias", "Status"],
        "rows": _ord_pior_primeiro(rows, idx_valor=2),
    }


def assessora_ren_salvos(df_renov: pd.DataFrame, assessora: str, ref: pd.Timestamp) -> dict:
    """Renovação · BÔNUS — card aberto sem prazo mas assinado antes do vencimento."""
    df = excluir_rascunhos(df_renov)
    df = aplicar_cutoff(df, "Criado em", ref=ref)
    nomes = _nome_assessora_alt(assessora)
    df = df[df["Assessor (lista)"].apply(lambda v: _contem_qualquer(v, nomes))].copy()
    df = df.dropna(subset=["Data de vencimento"]).copy()
    ant = (df["Data de vencimento"] - df["Criado em"]).dt.total_seconds() / 86400
    df = df[ant < RENOV_ANTECEDENCIA_MIN]
    df = df[~_renov_nao_renova(df)]
    col_ass = "Primeira vez que entrou na fase Contrato assinado / Finalizar"
    sub = df.dropna(subset=[col_ass]).copy()
    rows = []
    for _, r in sub.iterrows():
        venc = pd.to_datetime(r["Data de vencimento"], errors="coerce", utc=True)
        ass = pd.to_datetime(r[col_ass], errors="coerce", utc=True)
        if pd.isna(venc) or pd.isna(ass) or ass >= venc:
            continue
        dias_card = (venc - pd.to_datetime(r["Criado em"], errors="coerce", utc=True)).days
        rows.append([_im_label(r), _endereco_from_row(r),
                     f"card com {dias_card}d", _fmt_dias((venc - ass).total_seconds()/86400), "★"])
    return {
        "titulo": f"{_label_pessoa(assessora)} — Renov.: assinado no prazo com card sem prazo ★ ({len(rows)})",
        "cols": ["Imóvel", "Endereço", "Prazo do card", "Folga na assinatura", "Bônus"],
        "rows": rows,
    }


def assessora_rep_orc(df_rep: pd.DataFrame, assessora: str, ref: pd.Timestamp) -> dict:
    """Reparos · Orçamento <4h ÚTEIS. Filtro 'Selecionar o assessor'."""
    df = excluir_rascunhos(df_rep)
    df = aplicar_cutoff(df, "Criado em", ref=ref)
    nomes = _nome_assessora_alt(assessora)
    df = df[df["Selecionar o assessor"].apply(lambda v: _contem_qualquer(v, nomes))].copy()
    col_orc = "Primeira vez que entrou na fase Orçamento | Prestador"
    sub = df.dropna(subset=[col_orc]).copy()
    horas = sub.apply(lambda r: horas_uteis(r["Criado em"], r[col_orc]), axis=1)
    rows = []
    for (_, r), h in zip(sub.iterrows(), horas):
        rows.append([_im_label(r), r["Título"], _fmt_horas(h), "✓" if h <= _meta_tol(4) else "✗"])
    ok = sum(1 for r in rows if r[3] == "✓")
    return {
        "titulo": f"{_label_pessoa(assessora)} — Reparos: Orçamento <4h ({ok}/{len(sub)})",
        "cols": ["Imóvel", "Título", "Tempo", "Status"],
        "rows": _ord_pior_primeiro(rows, idx_valor=2),
    }


def assessora_rep_pos(df_rep: pd.DataFrame, assessora: str, ref: pd.Timestamp) -> dict:
    """Reparos · Pós-venda ≤7d CORRIDO. Filtro 'Selecionar o assessor'."""
    df = excluir_rascunhos(df_rep)
    df = aplicar_cutoff(df, "Criado em", ref=ref)
    nomes = _nome_assessora_alt(assessora)
    df = df[df["Selecionar o assessor"].apply(lambda v: _contem_qualquer(v, nomes))].copy()
    col_pos = "Primeira vez que entrou na fase Pós-venda"
    sub = df.dropna(subset=[col_pos]).copy()
    dias = (sub[col_pos] - sub["Criado em"]).dt.total_seconds() / 86400
    dias = dias.clip(lower=0)
    rows = []
    for (_, r), d in zip(sub.iterrows(), dias):
        rows.append([_im_label(r), r["Título"], _fmt_dias(d), "✓" if d <= 7 else "✗"])
    ok = sum(1 for r in rows if r[3] == "✓")
    return {
        "titulo": f"{_label_pessoa(assessora)} — Reparos: Pós-venda ≤7d ({ok}/{len(sub)})",
        "cols": ["Imóvel", "Título", "Dias", "Status"],
        "rows": _ord_pior_primeiro(rows, idx_valor=2),
    }


def _renov_viavel(df_renov: pd.DataFrame, assessora: str, ref: pd.Timestamp):
    """Cards da assessora com chance real de bater a meta — espelha calculate.py.
    Card criado a menos de RENOV_ANTECEDENCIA_MIN dias do vencimento sai do
    denominador (decisão da gestora, 14/08/2026): a meta já nasce inatingível.
    """
    df = excluir_rascunhos(df_renov)
    df = aplicar_cutoff(df, "Criado em", ref=ref)
    nomes = _nome_assessora_alt(assessora)
    df = df[df["Assessor (lista)"].apply(lambda v: _contem_qualquer(v, nomes))].copy()
    df = df.dropna(subset=["Data de vencimento"]).copy()
    ant = (df["Data de vencimento"] - df["Criado em"]).dt.total_seconds() / 86400
    df = df[ant >= RENOV_ANTECEDENCIA_MIN].copy()
    return df[~_renov_nao_renova(df)].copy()   # contrato que não renova sai


def assessora_ren_cont(df_renov: pd.DataFrame, assessora: str, ref: pd.Timestamp) -> dict:
    """Renovação · Contato >60d antes do vencimento.
    Mede pela ENTRADA na fase (a saída depende do proprietário responder)."""
    col_venc = "Data de vencimento"
    col_contato_in = "Primeira vez que entrou na fase Contato com proprietário"
    sub = _renov_viavel(df_renov, assessora, ref).dropna(subset=[col_contato_in]).copy()
    dias = (sub[col_venc] - sub[col_contato_in]).dt.total_seconds() / 86400
    rows = []
    for (_, r), d in zip(sub.iterrows(), dias):
        rows.append([_im_label(r), _endereco_from_row(r),
                     _fmt_dias(d, signed=True), "✓" if d > 60 else "✗"])
    ok = sum(1 for r in rows if r[3] == "✓")
    return {
        "titulo": f"{_label_pessoa(assessora)} — Renov.: Contato >60d ({ok}/{len(sub)})",
        "cols": ["Imóvel", "Endereço", "Dias", "Status"],
        "rows": _ord_pior_primeiro(rows, idx_valor=2),
    }


def assessora_ren_ass(df_renov: pd.DataFrame, assessora: str, ref: pd.Timestamp) -> dict:
    """Renovação · Assinado antes do vencimento. Diff = data_venc - data_assinatura."""
    col_assinado = "Primeira vez que entrou na fase Contrato assinado / Finalizar"
    col_venc = "Data de vencimento"
    sub = _renov_viavel(df_renov, assessora, ref).dropna(subset=[col_assinado]).copy()
    diff = (pd.to_datetime(sub[col_venc], errors="coerce", utc=True)
            - pd.to_datetime(sub[col_assinado], errors="coerce", utc=True)
            ).dt.total_seconds() / 86400
    rows = []
    for (_, r), d in zip(sub.iterrows(), diff):
        rows.append([_im_label(r), _endereco_from_row(r),
                     _fmt_dias(d, signed=True), "✓" if d > 0 else "✗"])
    ok = sum(1 for r in rows if r[3] == "✓")
    return {
        "titulo": f"{_label_pessoa(assessora)} — Renov.: Assinado antes venc ({ok}/{len(sub)})",
        "cols": ["Imóvel", "Endereço", "Diff", "Status"],
        "rows": _ord_pior_primeiro(rows, idx_valor=2),
    }


def assessora_bo(df_bo: pd.DataFrame, assessora: str, ref: pd.Timestamp) -> dict:
    """BackOffice · Pendência Assessor <24h CORRIDO. Filtro 'Responsáveis' (Card-level)."""
    df = excluir_rascunhos(df_bo)
    df = aplicar_cutoff(df, "Criado em", ref=ref)
    nomes = _nome_assessora_alt(assessora)
    df = df[df["Responsáveis"].apply(lambda v: _contem_qualquer(v, nomes))].copy()
    col_in = "Primeira vez que entrou na fase 🚩 Pendência Assessor"
    col_out = "Última vez que saiu da fase 🚩 Pendência Assessor"
    col_dur = "Tempo total na fase 🚩 Pendência Assessor (dias)"
    # Usa duration cumulativo (espelha calc_assessora_backoffice — evita inflação por reabertura).
    sub = df.dropna(subset=[col_in, col_out, col_dur]).copy()
    horas = sub.apply(lambda r: horas_uteis_fase(
        r.get(col_in), r.get("Última vez que entrou na fase 🚩 Pendência Assessor"),
        r.get(col_out), r.get(col_dur)), axis=1)
    rows = []
    for (_, r), h in zip(sub.iterrows(), horas):
        rows.append([_im_label(r), r["Título"], _fmt_horas(h), "✓" if h <= _meta_tol(24) else "✗"])
    ok = sum(1 for r in rows if r[3] == "✓")
    return {
        "titulo": f"{_label_pessoa(assessora)} — BackOffice: Pendência <24h ({ok}/{len(sub)})",
        "cols": ["Imóvel", "Título", "Tempo", "Status"],
        "rows": _ord_pior_primeiro(rows, idx_valor=2),
    }


def assessora_dirf(df_dirf: pd.DataFrame, assessora: str, ref: pd.Timestamp) -> dict:
    """DIRF/DARF · Concluído antes 29/05/2026. Filtro Ano=2025 + Responsável."""
    df = excluir_rascunhos(df_dirf)
    ano_int = pd.to_numeric(df["Ano:"], errors="coerce").astype("Int64")
    df = df[ano_int == DIRF_DARF_ANO_BASE]
    nomes = _nome_assessora_alt(assessora)
    df = df[df["Responsável"].apply(lambda v: _contem_qualquer(v, nomes))].copy()
    col_concl = "Primeira vez que entrou na fase Concluído"
    deadline = pd.Timestamp(DIRF_DARF_CUTOFF).tz_localize("UTC")
    rows = []
    for _, r in df.iterrows():
        concl = r.get(col_concl)
        if pd.notna(concl):
            data_s = pd.Timestamp(concl).strftime("%d/%m/%Y")
            status = "✓" if concl < deadline else "✗"
        else:
            data_s = "—"
            status = "✗"
        # 'Locatário' não está no pipe — usar Título como descritivo
        rows.append([_im_label(r), r["Título"], data_s, status])
    ok = sum(1 for r in rows if r[3] == "✓")
    # ordena: ✗ primeiro (pendentes), depois ✓ por data
    rows.sort(key=lambda r: (r[3] == "✓", str(r[0])))
    return {
        "titulo": f"{_label_pessoa(assessora)} — DIRF/DARF: Concluído < 29/mai ({ok}/{len(df)})",
        "cols": ["Imóvel", "Locatário", "Data", "Status"],
        "rows": rows,
    }


# ────────────────────────────────────────────────────────────────────
# MARINHO — Vistorias + Contestações (2 chaves)
# ────────────────────────────────────────────────────────────────────

def mar_laudo(df_vist: pd.DataFrame, ref: pd.Timestamp) -> dict:
    """Marinho · Laudo ≤48h CORRIDAS. Parado em produção (saída vazia) = ✗."""
    df = excluir_rascunhos(df_vist)
    df = aplicar_cutoff(df, "Criado em", ref=ref)
    col_vfim = "Vistoria finalizada em"
    # PRIMEIRA saída de "Em produção" — mesma regra da nota (calculate.primeira_saida_fase).
    col_prod_in = "Primeira vez que entrou na fase Em produção"
    col_prod_lastin = "Última vez que entrou na fase Em produção"
    col_prod_out = "Última vez que saiu da fase Em produção"
    col_prod_dur = "Tempo total na fase Em produção (dias)"
    sub = df.dropna(subset=[col_vfim]).copy()  # denominador = vistorias finalizadas
    rows = []
    for _, r in sub.iterrows():
        saida = primeira_saida_fase(r.get(col_prod_in), r.get(col_prod_lastin),
                                    r.get(col_prod_out), r.get(col_prod_dur))
        if pd.isna(saida):
            rows.append([_im_label(r), r["Título"], "em produção", "✗"])  # parado
        else:
            h = horas_corridas(r[col_vfim], saida)
            rows.append([_im_label(r), r["Título"], _fmt_horas(h),
                         "✓" if h <= 48.0 else "✗"])
    ok = sum(1 for r in rows if r[3] == "✓")
    return {
        "titulo": f"Marinho — Vistorias: Laudo <48h ({ok}/{len(sub)})",
        "cols": ["Imóvel", "Título", "Tempo", "Status"],
        "rows": _ord_pior_primeiro(rows, idx_valor=2),
    }


def mar_eficiencia(df_vist: pd.DataFrame, ref: pd.Timestamp) -> dict:
    """Marinho · Vistorias dentro do tempo padrão (eficiência).
    Reusa avaliar_eficiencia_vistoria do calculate -> mesmo verdict da nota."""
    df = excluir_rascunhos(df_vist)
    df = aplicar_cutoff(df, "Criado em", ref=ref)
    rows = []
    for _, r in df.iterrows():
        v = avaliar_eficiencia_vistoria(r)
        if v is None or v["ok"] is None:
            continue  # fora do escopo ou REVISAR (não entra no ok/tot)
        status = "✗⚠" if (v["outlier"] and not v["ok"]) else ("✓" if v["ok"] else "✗")
        rows.append([_im_label(r), f"{v['balde']} · {v['direcao']}",
                     _fmt_horas(v["horas"]), status])
    ok = sum(1 for r in rows if r[3] == "✓")
    return {
        "titulo": f"Marinho — Vistorias: dentro do tempo padrão ({ok}/{len(rows)})",
        "cols": ["Imóvel", "Tipo · Direção", "Tempo", "Status"],
        "rows": _ord_pior_primeiro(rows, idx_valor=2),
    }


def _mar_flag(df_vist, ref, coluna, titulo, chave_col, so_sim=False):
    """Drilldown dos campos SIM/NÃO das vistorias (360º e vídeo de drone)."""
    df = excluir_rascunhos(df_vist)
    df = aplicar_cutoff(df, "Criado em", ref=ref)
    val = df.get(coluna, pd.Series(dtype=object)).astype(str).str.strip().str.upper()
    sub = df[val == "SIM"] if so_sim else df[val.isin(["SIM", "NÃO", "NAO"])]
    rows = []
    for _, r in sub.iterrows():
        v = str(r.get(coluna, "")).strip().upper()
        rows.append([_im_label(r), str(r.get("Endereço do imóvel:", ""))[:60],
                     "Sim" if v == "SIM" else "Não",
                     "★" if so_sim else ("✓" if v == "SIM" else "✗")])
    ok = sum(1 for r in rows if r[3] in ("✓", "★"))
    tot = len(sub)
    return {"titulo": f"{titulo} ({ok}{'' if so_sim else '/' + str(tot)})",
            "cols": ["Imóvel", "Endereço", chave_col, "Status"],
            "rows": _ord_pior_primeiro(rows, idx_valor=2)}


def mar_360(df_vist: pd.DataFrame, ref: pd.Timestamp) -> dict:
    return _mar_flag(df_vist, ref, "Vistoria com 360º ?",
                     "Marinho — Vistorias com 360º", "360º")


def mar_drone(df_vist: pd.DataFrame, ref: pd.Timestamp) -> dict:
    return _mar_flag(df_vist, ref, "Vistoria com Vídeo de DRONE",
                     "Marinho — Vistorias com vídeo de drone ★", "Drone", so_sim=True)


def mar_cont(df_cont: pd.DataFrame, ref: pd.Timestamp) -> dict:
    """Marinho · Contestações respondidas <24h CORRIDO."""
    df = excluir_rascunhos(df_cont)
    df = aplicar_cutoff(df, "Criado em", ref=ref)
    col_concl = "Primeira vez que entrou na fase Concluído"
    sub = df.dropna(subset=[col_concl]).copy()
    horas = sub.apply(lambda r: horas_uteis(r["Criado em"], r[col_concl]), axis=1)
    horas = horas.clip(lower=0)
    rows = []
    for (_, r), h in zip(sub.iterrows(), horas):
        rows.append([_im_label(r), r["Título"], _fmt_horas(h), "✓" if h <= _meta_tol(24) else "✗"])
    ok = sum(1 for r in rows if r[3] == "✓")
    return {
        "titulo": f"Marinho — Contestações: <24h ({ok}/{len(sub)})",
        "cols": ["Imóvel", "Título", "Tempo", "Status"],
        "rows": _ord_pior_primeiro(rows, idx_valor=2),
    }


# ────────────────────────────────────────────────────────────────────
# OCTADESK — WhatsApp + Tickets (helpers + 6 chaves)
# ────────────────────────────────────────────────────────────────────

def _row_indicador(ind: dict) -> list[str]:
    """Converte um indicador {ok, tot, pct} em row formato Octadesk."""
    pct = ind.get("pct")
    pct_s = f"{pct:.1f}%" if pct is not None else "—"
    return [ind["nome"].split(" — ")[-1], f"{ind['ok']}/{ind['tot']}", pct_s]


def _wa_drilldown(df_conv: pd.DataFrame, pid: str, label_pessoa: str) -> dict:
    """Drilldown agregado de WhatsApp (2 rows)."""
    inds = _whatsapp_indicadores(df_conv, NOMES_AGENTE[pid]["whatsapp"])
    rows = [_row_indicador(ind) for ind in inds]
    return {
        "titulo": f"{label_pessoa} — WhatsApp",
        "cols": ["Indicador", "OK/Total", "%"],
        "rows": rows,
    }


def _tkt_drilldown(df_tickets: pd.DataFrame, df_aval: pd.DataFrame, pid: str,
                    label_pessoa: str, *, com_aval: bool, peso_sla: int = 4,
                    peso_aval: int = 3) -> dict:
    """Drilldown agregado de Tickets. com_aval=False para Vivianne (só SLA)."""
    nome = NOMES_AGENTE[pid]["ticket"]
    df_t = _tickets_filtrados(df_tickets, nome)
    ind_sla = _ticket_sla_ind(df_t, peso=peso_sla)
    rows = [_row_indicador(ind_sla)]
    if com_aval:
        ind_aval = _ticket_aval_ind(df_aval, nome, peso=peso_aval)
        rows.append(_row_indicador(ind_aval))
    return {
        "titulo": f"{label_pessoa} — Tickets",
        "cols": ["Indicador", "OK/Total", "%"],
        "rows": rows,
    }


def caio_wa(df_conversas: pd.DataFrame) -> dict:
    return _wa_drilldown(df_conversas, "caio", "Caio")


# ────────────────────────────────────────────────────────────────────
# Entry point — registry parcial (5 chaves de teste)
# ────────────────────────────────────────────────────────────────────

def _assessora_keys(prefix: str, pid: str, dfs: dict, ref: pd.Timestamp) -> dict:
    """Gera 12 chaves para uma assessora ('nat' ou 'gar') aplicando o pid correspondente."""
    return {
        f"{prefix}_cadm":          assessora_cadm(dfs["cont_adm"], pid, ref),
        f"{prefix}_cadm_bonus":    assessora_cadm_bonus(dfs["cont_adm"], pid, ref),
        f"{prefix}_resc_adm_ali":   assessora_resc_adm_ali(dfs["rescisao_adm"], pid, ref),
        f"{prefix}_resc_adm_concl": assessora_resc_adm_concl(dfs["rescisao_adm"], pid, ref),
        f"{prefix}_resc_adm_dist":  assessora_resc_adm_dist(dfs["rescisao_adm"], pid, ref),
        f"{prefix}_rl_prop":       assessora_rl_prop(dfs["rescisao_loc"], pid, ref,
                                                  dfs.get("distratos")),
        f"{prefix}_rl_final":      assessora_rl_final(dfs["rescisao_loc"], pid, ref,
                                                  dfs.get("distratos")),
        f"{prefix}_rep_orc":       assessora_rep_orc(dfs["reparos"], pid, ref),
        f"{prefix}_rep_pos":       assessora_rep_pos(dfs["reparos"], pid, ref),
        f"{prefix}_ren_cont":      assessora_ren_cont(dfs["renovacao"], pid, ref),
        f"{prefix}_ren_ass":       assessora_ren_ass(dfs["renovacao"], pid, ref),
        f"{prefix}_ren_salvos":    assessora_ren_salvos(dfs["renovacao"], pid, ref),
        f"{prefix}_bo":            assessora_bo(dfs["backoffice"], pid, ref),
        f"{prefix}_dirf":          assessora_dirf(dfs["dirf_darf"], pid, ref),
    }


def gerar_imoveis(dfs: dict, ref: pd.Timestamp) -> dict:
    """Retorna o dict IMOVEIS para o painel — 55 chaves cobrindo todos os indicadores."""
    df_conv = dfs.get("conversas", pd.DataFrame())
    df_tkt = dfs.get("tickets", pd.DataFrame())
    df_aval = dfs.get("aval_tickets", pd.DataFrame())
    out = {
        # Caio (8 chaves)
        "caio_inicio":       caio_inicio(dfs["comercial_locacao"], ref),
        "caio_anuncio":      caio_anuncio(dfs["comercial_locacao"], ref),
        "caio_coluna":       caio_coluna(dfs["comercial_locacao"], ref),
        "caio_bonus":        caio_bonus(dfs["comercial_locacao"], dfs["cont_locacao"], ref),
        "caio_ocupacao":     caio_ocupacao(dfs["comercial_locacao"], dfs["cont_locacao"], ref),
        "caio_docs":         caio_docs(dfs["cont_locacao"], ref),
        "caio_cadm":         caio_cadm(dfs["cont_adm"], ref),
        "caio_renov":        caio_renov(dfs["renovacao"], ref),
        # Vivianne (14 chaves Pipefy + 1 bônus)
        "vivi_cadm":         vivi_cadm(dfs["cont_adm"], ref),
        "vivi_resc_adm":     vivi_resc_adm(dfs["rescisao_adm"], ref),
        "vivi_nido":         vivi_nido(dfs["cont_locacao"], ref),
        "vivi_confec_loc":   vivi_confec_loc(dfs["cont_locacao"], ref),
        "vivi_lev_prop":     vivi_lev_prop(dfs["rescisao_loc"], ref),
        "vivi_lev_final":    vivi_lev_final(dfs["rescisao_loc"], ref),
        "vivi_ren_confec":   vivi_ren_confec(dfs["renovacao"], ref),
        "vivi_ren_final":    vivi_ren_final(dfs["renovacao"], ref),
        "vivi_cob":          vivi_cob(dfs["inadimplencia"], ref),
        "vivi_cred":         vivi_cred(dfs["inadimplencia"], ref),
        "vivi_neg":          vivi_neg(dfs["inadimplencia"], ref),
        "vivi_bo_concl":     vivi_bo_concl(dfs["backoffice"], ref),
        "vivi_bo_troca":     vivi_bo_troca(dfs["backoffice"], ref),
        "vivi_cobertura":    vivi_cobertura(),
        "vivi_bonus_inadim": vivi_bonus_inadim(),
        # Marinho (3 chaves)
        "mar_laudo":         mar_laudo(dfs["vistorias"], ref),
        "mar_eficiencia":    mar_eficiencia(dfs["vistorias"], ref),
        "mar_360":           mar_360(dfs["vistorias"], ref),
        "mar_drone":         mar_drone(dfs["vistorias"], ref),
        "mar_cont":          mar_cont(dfs["contestacoes"], ref),
        # Octadesk (6 chaves) + Vivianne Tickets (1) = 7
        "caio_wa":           _wa_drilldown(df_conv, "caio", "Caio"),
        "caio_tickets":      _tkt_drilldown(df_tkt, df_aval, "caio", "Caio",
                                            com_aval=True, peso_sla=4, peso_aval=3),
        "nat_wa":            _wa_drilldown(df_conv, "natalia", "Natália"),
        "nat_tickets":       _tkt_drilldown(df_tkt, df_aval, "natalia", "Natália",
                                            com_aval=True, peso_sla=3, peso_aval=3),
        "gar_wa":            _wa_drilldown(df_conv, "gardenia", "Gardênia"),
        "gar_tickets":       _tkt_drilldown(df_tkt, df_aval, "gardenia", "Gardênia",
                                            com_aval=True, peso_sla=3, peso_aval=3),
        "vivi_tickets":      _tkt_drilldown(df_tkt, df_aval, "vivianne", "Vivianne",
                                            com_aval=False, peso_sla=4),
    }
    # Assessoras (24 chaves: 12 Natália + 12 Gardênia)
    out.update(_assessora_keys("nat", "natalia", dfs, ref))
    out.update(_assessora_keys("gar", "gardenia", dfs, ref))
    return out
