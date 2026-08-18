"""
TRK Experience — Pipeline de Cálculo de Ranking
================================================

Este módulo aplica as regras do manual_v4.md sobre DataFrames extraídos
do Pipefy/Octadesk e retorna a estrutura PESSOAS / IMOVEIS / PROC_RICH
que alimenta o painel.

ARQUITETURA:
    extract_*.py → DataFrames com nomes de coluna idênticos aos XLSX atuais
                ↓
    calculate.py → aplica regras do manual, retorna scores por indicador
                ↓
    validate.py  → compara com baselines.json
                ↓
    run.py       → orquestra tudo, salva dados/atual.json

CONVENÇÕES:
    - Toda função `calc_<colaborador>_<processo>()` retorna:
        {"score": float, "indicadores": [{"nome", "ok", "tot", "pct", "peso", "score"}]}
    - Score de cada indicador = (ok / tot) * peso
    - Nota do processo = sum(scores) / sum(pesos) * 10
    - Nota final do colaborador = média simples das notas de processo não-nulas
    - Bônus: (score_base + N) / (peso_base + N) * 10

CRÍTICO — releia o manual antes de mexer:
    - Cutoff 180d rolando, exceto Caio Cont.ADM (01/03/2026) e DIRF/DARF (29/05/2026)
    - Horas úteis: 08-18 seg-sex
    - Timestamps negativos = 0h (✓), não excluir
    - Rascunhos: excluir cards com "rascunho" em qualquer campo de texto
    - Tickets: excluir Categoria=Cancelado/Spam, Status=Cancelado, Assunto=Tarefa
"""

import json
import re
import zoneinfo
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
from typing import Optional

TZ_BSB = zoneinfo.ZoneInfo("America/Sao_Paulo")


# ─────────────────────────────────────────────────────────────────────
# CONFIGURAÇÃO
# ─────────────────────────────────────────────────────────────────────

CONFIG_DIR = Path(__file__).resolve().parent / "config"
FEATURE_FLAGS = json.loads((CONFIG_DIR / "feature_flags.json").read_text(encoding="utf-8"))

CUTOFF_DIAS = 180
CUTOFF_CONT_ADM_CAIO_FIXO = datetime(2026, 3, 1)
DIRF_DARF_CUTOFF = datetime(2026, 5, 29)  # prorrogação oficial 2026
DIRF_DARF_ANO_BASE = 2025

# ─────────────────────────────────────────────────────────────────────
# MARGEM DE TOLERÂNCIA EM INDICADORES DE HORAS
# (correção pós-fechamento 11ª Ed — aprovada pela gestora em 27/05/2026)
#
# Motivação: um card que estoura a meta por poucos minutos (ex.: IM1598 com
# 24,05h na meta de 24h — atraso de ~3 min) era penalizado igual a um caso de
# 30h. A tolerância (~2% da meta) absorve ruído operacional de minutos.
#
# Regra: aplica-se SOMENTE a indicadores cuja meta é em HORAS (corridas OU úteis).
# A tolerância está na MESMA unidade do tempo medido (se h é útil, a margem é útil).
# NÃO se aplica a metas em dias, %, minutos ou razão (m²/h) — ver _meta_tol.
# Chave do dict = meta em horas; valor = margem em horas.
TOLERANCIAS = {
    2:  5 / 60,    # +5 min
    4:  10 / 60,   # +10 min
    12: 14 / 60,   # +14 min
    16: 19 / 60,   # +19 min
    24: 30 / 60,   # +30 min
    72: 86 / 60,   # +86 min
}


def _meta_tol(meta_h: float) -> float:
    """Retorna a meta de horas acrescida da margem de tolerância aprovada.

    Usar nos testes do tipo `h <= meta` → `h <= _meta_tol(meta)`, onde `h` é o
    tempo medido em horas (mesma unidade — corrida ou útil — da meta).
    Metas sem entrada em TOLERANCIAS retornam a própria meta (margem 0).
    """
    return meta_h + TOLERANCIAS.get(meta_h, 0.0)

NOMES_AGENTE = {
    "caio":      {"whatsapp": "Caio Rodrigues",   "ticket": "Caio Rodrigues"},
    "natalia":   {"whatsapp": "Natália Teixeira", "ticket": "Natália Teixeira"},
    "gardenia":  {"whatsapp": "Gardênia",         "ticket": "Gardênia"},
    "vivianne":  {"whatsapp": None,               "ticket": ["Vivianne Fontes", "VIVIANNE FONTES"]},  # WhatsApp EXCLUÍDO
}


# ─────────────────────────────────────────────────────────────────────
# HELPERS GERAIS
# ─────────────────────────────────────────────────────────────────────

def cutoff(dias: int = CUTOFF_DIAS, ref: Optional[datetime] = None) -> pd.Timestamp:
    """
    Retorna o cutoff (ref - dias) como Timestamp tz-aware UTC.
    `ref` permite reproducibilidade contra baseline (Maio/2026 etc).
    Default: agora em UTC.
    """
    base = pd.Timestamp(ref) if ref is not None else pd.Timestamp.utcnow()
    if base.tzinfo is None:
        base = base.tz_localize("UTC")
    return base - pd.Timedelta(days=dias)


def aplicar_cutoff(df: pd.DataFrame, coluna: str, *, dias: int = CUTOFF_DIAS,
                   ref: Optional[datetime] = None, data_fixa: Optional[datetime] = None) -> pd.DataFrame:
    """
    Filtra df mantendo apenas linhas onde `coluna >= cutoff`.
    Se `data_fixa` fornecida, usa-a como cutoff (ex: Caio Cont.ADM = 01/03/2026).
    """
    if data_fixa is not None:
        limit = pd.Timestamp(data_fixa)
        if limit.tzinfo is None:
            limit = limit.tz_localize("UTC")
    else:
        limit = cutoff(dias=dias, ref=ref)
    if coluna not in df.columns:
        return df.iloc[0:0].copy()
    col = pd.to_datetime(df[coluna], errors="coerce", utc=True)
    return df[col >= limit].copy()


def excluir_rascunhos(df: pd.DataFrame) -> pd.DataFrame:
    """Remove cards onde Título, Imóvel ou Endereço contenham 'rascunho' (case insensitive)."""
    cols_texto = [c for c in ["Título", "Imóvel", "Endereço"] if c in df.columns]
    if not cols_texto:
        return df
    mask = pd.Series([False] * len(df), index=df.index)
    for col in cols_texto:
        mask |= df[col].astype(str).str.contains("rascunho", case=False, na=False)
    return df[~mask].copy()


# ─────────────────────────────────────────────────────────────────────
# Helpers — assignees, IMs, fases
# ─────────────────────────────────────────────────────────────────────

def _as_list(v) -> list[str]:
    """Normaliza valor de assignee_select para list[str], lidando com None/string/lista."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return []
    if isinstance(v, list):
        return [str(x).strip() for x in v if x]
    s = str(v).strip()
    if not s:
        return []
    # tenta JSON
    if s.startswith("["):
        try:
            arr = json.loads(s)
            return [str(x).strip() for x in arr if x]
        except json.JSONDecodeError:
            pass
    return [s]


def contem_assignee(valor, nome: str) -> bool:
    """
    True se `nome` (case-insensitive, ignorando acentos básicos) aparece em algum item de `valor`.
    `valor` pode ser lista, string ou JSON-string.
    """
    target = nome.lower()
    for it in _as_list(valor):
        if target in it.lower():
            return True
    return False


def filtrar_por_assignee(df: pd.DataFrame, coluna: str, nome: str) -> pd.DataFrame:
    """Mantém linhas onde `coluna` contém `nome` (caso-insensível) em algum dos assignees."""
    if coluna not in df.columns:
        return df.iloc[0:0].copy()
    mask = df[coluna].apply(lambda v: contem_assignee(v, nome))
    return df[mask].copy()


IM_REGEX = __import__("re").compile(r"IM\s*(\d+)", __import__("re").IGNORECASE)


def extrair_im(texto) -> Optional[int]:
    """Extrai 'IM 123' ou 'IM123' de uma string. Retorna int ou None."""
    if texto is None or (isinstance(texto, float) and pd.isna(texto)):
        return None
    # se for lista (connector), tenta cada item
    if isinstance(texto, list):
        for t in texto:
            n = extrair_im(t)
            if n is not None:
                return n
        return None
    s = str(texto)
    # JSON-string de connector vira lista
    if s.startswith("["):
        try:
            return extrair_im(json.loads(s))
        except json.JSONDecodeError:
            pass
    m = IM_REGEX.search(s)
    return int(m.group(1)) if m else None


def _to_bsb_naive(dt) -> Optional[pd.Timestamp]:
    """
    Converte para Brasília naive. Se já naive, assume está em horário de Brasília.
    Retorna None se input for NaT/None.
    """
    if dt is None or pd.isna(dt):
        return None
    ts = pd.Timestamp(dt)
    if ts.tzinfo is None:
        return ts
    return ts.tz_convert(TZ_BSB).tz_localize(None)


def horas_uteis(inicio, fim) -> float:
    """
    Horas úteis (08:00–18:00, seg-sex) entre inicio e fim, em horário de Brasília.

    Regras (manual §3.3):
    - NaT/None em qualquer lado → NaN.
    - fim <= inicio (negativo ou zero) → 0.0 (= cumprido ✓).
    - Sábado e domingo: 0 horas.
    - Fora de 08-18: descontado.
    - 1 dia útil = 10 horas úteis.
    """
    a = _to_bsb_naive(inicio)
    b = _to_bsb_naive(fim)
    if a is None or b is None:
        return float("nan")
    if b <= a:
        return 0.0

    BS, BE = 8, 18  # 8h–18h
    total_seconds = 0.0
    dia = a.normalize()  # 00:00 do dia de início
    fim_dia = b.normalize()
    while dia <= fim_dia:
        if dia.weekday() < 5:  # 0=seg ... 4=sex
            day_start = dia.replace(hour=BS)
            day_end = dia.replace(hour=BE)
            window_start = max(a, day_start)
            window_end = min(b, day_end)
            if window_end > window_start:
                total_seconds += (window_end - window_start).total_seconds()
        dia = dia + timedelta(days=1)
    return total_seconds / 3600.0


def dias_uteis(inicio: pd.Timestamp, fim: pd.Timestamp) -> float:
    """Wrapper: horas úteis ÷ 10."""
    return horas_uteis(inicio, fim) / 10.0


def horas_uteis_fase(first_in, last_in, last_out, dur_dias) -> float:
    """
    Horas úteis (08-18h, seg-sex) que um card passou DENTRO de uma fase,
    robusto a reaberturas (card que entra, sai e volta à MESMA fase).

    Por que existe (correção do bug latente da 11ª, fechado na 12ª):
    o Pipefy reporta o histórico AGREGADO por fase — firstTimeIn, lastTimeIn,
    lastTimeOut e `duration` (CORRIDO cumulativo) — e não cada passagem
    individual. Usar horas_uteis(firstTimeIn, lastTimeOut) conta o tempo em que
    o card esteve em OUTRAS fases entre idas e vindas, superestimando
    grosseiramente (ex.: IM1471 — janela 173h vs 1,7h reais na fase). Já o
    `duration` é CORRIDO, então não serve direto para metas em horas ÚTEIS.

    Reconstrução com os campos agregados (dentro de UMA visita o card é contínuo
    na fase, logo ocupa um intervalo de relógio exato):
      • 1 visita (last_in == first_in): horas_uteis(first_in, last_out) — EXATO.
      • 2 visitas: última visita [last_in, last_out] é exata; o restante do
        `duration` é o corrido da 1ª visita, que começou em first_in e ocupou
        [first_in, first_in + restante] — EXATO.
      • 3+ visitas: as visitas intermediárias não têm timestamp; aproxima-se o
        bloco anterior à última como contíguo a partir de first_in. Aproximação
        documentada — usa só o `duration` REAL na fase, nunca a janela inteira.

    NaN se faltarem first_in/last_out. Sem dur_dias → fallback p/ janela simples.
    """
    if first_in is None or pd.isna(first_in) or last_out is None or pd.isna(last_out):
        return float("nan")
    # Sem duration não há como reconstruir → janela simples (comportamento antigo).
    if dur_dias is None or pd.isna(dur_dias):
        return horas_uteis(first_in, last_out)
    fin = pd.Timestamp(first_in)
    lout = pd.Timestamp(last_out)
    # Visita única: nunca reabriu → a janela [first_in, last_out] é exata.
    if (last_in is None or pd.isna(last_in)
            or abs((pd.Timestamp(last_in) - fin).total_seconds()) <= 1):
        return horas_uteis(fin, lout)
    # Reaberto: última visita exata + bloco anterior contíguo a partir de first_in.
    lin = pd.Timestamp(last_in)
    total_sec = float(dur_dias) * 86400.0
    ultima_sec = max(0.0, (lout - lin).total_seconds())
    anterior_sec = max(0.0, total_sec - ultima_sec)
    util_ultima = horas_uteis(lin, lout)
    util_anterior = horas_uteis(fin, fin + pd.Timedelta(seconds=anterior_sec))
    return util_ultima + util_anterior


def primeira_saida_fase(first_in, last_in, last_out, dur_dias):
    """
    PRIMEIRA saída de uma fase — imune à "passagem-fantasma" do Pipefy.

    Por que existe (auditoria de 05/08/2026):
    quando o card é encerrado, o Pipefy o ARRASTA pelas fases, gravando entradas
    e saídas de segundos em cada uma. Isso empurra `lastTimeOut` para a data do
    fechamento e destrói qualquer medida de ciclo — chegou a produzir intervalos
    NEGATIVOS que a regra de "negativo → 0" transformava em ✓ falso (IM737), e
    ciclos de 17 segundos (IM1353). No Marinho, 5 laudos entregues no prazo
    apareciam como ✗.

    Regra (validada no dw_trk — bate 100% nos cards reabertos):
      • visita única (last_in == first_in) → `last_out` é EXATO, usar direto;
      • reaberto → a última visita ocupa [last_in, last_out]; o restante do
        `duration` é o corrido das visitas anteriores, que começaram em
        first_in. Logo: 1ª saída ≈ first_in + (duration − última visita).
      • guarda final: a primeira saída NUNCA pode ser posterior à última.

    ⚠️ NÃO usar a coluna "Última vez que saiu da fase X" como fim de ciclo sem
    passar por aqui. Ela continua válida para RECORTE de período (onde o que se
    quer é justamente "atividade recente").
    """
    if first_in is None or pd.isna(first_in) or last_out is None or pd.isna(last_out):
        return pd.NaT
    fin = pd.Timestamp(first_in)
    lout = pd.Timestamp(last_out)
    # Visita única: nunca reabriu → a saída registrada é a primeira e é exata.
    if (last_in is None or pd.isna(last_in)
            or abs((pd.Timestamp(last_in) - fin).total_seconds()) <= 1):
        return lout
    # Reaberto sem duration → não há como reconstruir; mantém o comportamento antigo.
    if dur_dias is None or pd.isna(dur_dias):
        return lout
    lin = pd.Timestamp(last_in)
    total_sec = float(dur_dias) * 86400.0
    ultima_sec = max(0.0, (lout - lin).total_seconds())
    anterior_sec = max(0.0, total_sec - ultima_sec)
    candidata = fin + pd.Timedelta(seconds=anterior_sec)
    return min(candidata, lout)


def horas_corridas(inicio: pd.Timestamp, fim: pd.Timestamp) -> float:
    """Diferença em horas corridas. Negativo → 0."""
    if pd.isna(inicio) or pd.isna(fim):
        return float("nan")
    delta = (fim - inicio).total_seconds() / 3600
    return max(delta, 0.0)


def dias_corridos(inicio: pd.Timestamp, fim: pd.Timestamp) -> float:
    """Diferença em dias corridos. Negativo → 0."""
    return horas_corridas(inicio, fim) / 24.0


def score_indicador(ok: int, tot: int, peso: float) -> dict:
    """Retorna estrutura padrão de um indicador."""
    pct = round(100 * ok / tot, 1) if tot > 0 else None
    score = round((ok / tot) * peso, 3) if tot > 0 else None
    return {"ok": ok, "tot": tot, "pct": pct, "peso": peso, "score": score}


# Bônus de CONTAGEM (13ª Ed, decisão da gestora 13/08/2026).
# Vale só para os bônus que NÃO têm denominador natural:
#   Caio · Comercial      — imóvel alugado antes de ser anunciado
#   Natália/Gardênia      — vistoria de entrada realizada
# Os que TÊM denominador viraram indicadores com peso próprio:
#   Vivianne · Inadimplência — Cobrança antes do repasse (47/113)
#   Natália/Gardênia         — Distrato assinado (2/8)
BONUS_POR_UNIDADE = 0.25
BONUS_TETO = 1.5


def nota_processo(indicadores: list, bonus_n: int = 0) -> Optional[float]:
    """
    Calcula nota do processo (0-10).

    Fórmula:  sum(scores) / sum(pesos) * 10  +  min(bonus_n * 0,25 ; 1,5)

    ⚠️ MUDANÇA DA 13ª EDIÇÃO — POR QUE O BÔNUS SAIU DO DENOMINADOR
    --------------------------------------------------------------
    Até 13/08/2026 a fórmula era (scores + N) / (pesos + N) × 10, ou seja, cada
    ponto extra entrava como um indicador virtual de peso 1 com 100% de acerto.
    Quando N ficava grande em relação ao peso do processo, a nota convergia para
    10 e escondia o desempenho real:

      Vivianne · Inadimplência : N=47 contra peso 4 → o bônus carregava 92% do
        processo. Nota real 6,46 · exibida 9,72. Corrigimos a data do repasse
        (que errava em 67,5%) e a nota andou 0,01 — prova de que nenhuma
        correção de dado movia aquela nota.
      Natália · Cont. ADM      : 0/8 no único indicador, e o painel mostrava 3,33.

    Agora o bônus é ACRÉSCIMO COM TETO: soma depois da nota, no máximo +1,5.
    A nota do processo volta a ser visível e o extra continua premiado.

    Indicadores sem dados (tot=0) são excluídos. Se todos sem dados, retorna None.
    """
    validos = [i for i in indicadores if i["tot"] > 0]
    if not validos:
        return None
    soma_scores = sum(i["score"] for i in validos)
    soma_pesos = sum(i["peso"] for i in validos)
    base = soma_scores / soma_pesos * 10
    extra = min(bonus_n * BONUS_POR_UNIDADE, BONUS_TETO) if bonus_n else 0.0
    return round(min(10.0, base + extra), 3)


def nota_final(scores_processos: dict) -> Optional[float]:
    """Média simples das notas de processo não-nulas."""
    validas = [v for v in scores_processos.values() if v is not None]
    if not validas:
        return None
    return round(sum(validas) / len(validas), 2)


# ─────────────────────────────────────────────────────────────────────
# CAIO — COMERCIAL
# ─────────────────────────────────────────────────────────────────────

def _now_ref(ref: Optional[datetime] = None) -> pd.Timestamp:
    """Retorna timestamp tz-aware usado como 'hoje'. UTC."""
    base = pd.Timestamp(ref) if ref is not None else pd.Timestamp.utcnow()
    if base.tzinfo is None:
        base = base.tz_localize("UTC")
    return base


def _expected_phase_desocupacao(days: float) -> Optional[str]:
    """Mapa de intervalo de dias desocupado → fase esperada (manual §4.1)."""
    if days < 0 or pd.isna(days):
        return None
    if days <= 5:
        return "Conferência Final"
    if days <= 29:
        return "15 dias desocupado"
    if days <= 59:
        return "30 Dias desocupado"
    if days <= 89:
        return "60 Dias desocupado"
    if days <= 179:
        return "90 Dias desocupado"
    return "180 Dias desocupado"


def calc_caio_comercial_locacao(df_comercial: pd.DataFrame, bonus_n: int = 0,
                                ref: Optional[datetime] = None) -> dict:
    """
    Caio · Comercial Locação · 3 indicadores · peso 10 · bônus aplicado aqui.

    Indicador 1: Início <24h ÚTEIS (peso 2.5) — Criado em → Primeira vez Avaliação Técnica
    Indicador 2: Anúncio <72h (peso 2.5) — Última saída Aval.Téc OU Cadastro/NIDO → Publicação
    Indicador 3: Coluna correta (peso 5) — fase atual vs intervalo desocupação

    Bônus: imóvel alugado antes de anunciado — passado como bonus_n já calculado.
    """
    # Filtros: cutoff 180d em Criado em, Caio em Profissional responsável, sem rascunho
    df = excluir_rascunhos(df_comercial)
    df = aplicar_cutoff(df, "Criado em", ref=ref)
    df = filtrar_por_assignee(df, "Profissional responsável", "Caio")

    # ─── Indicador 1: Início <24h ÚTEIS (Criado → Avaliação Técnica) ───
    col_avt_in = "Primeira vez que entrou na fase Avaliação Técnica"
    df1 = df.dropna(subset=[col_avt_in])  # denominator = cards que entraram em Aval.Téc
    # HORAS ÚTEIS (decisão da gestora, 12/08/2026): metas curtas em horas
    # corridas empurravam gente a trabalhar fora do expediente por medo do
    # ranking. Medida em horas úteis (08-18h, seg-sex), quem entrega segunda
    # de manhã é medido igual a quem entrega quinta à tarde.
    delta_h = pd.Series([horas_uteis(i, f) for i, f in
                         zip(df1["Criado em"], df1[col_avt_in])], index=df1.index)
    ind1 = score_indicador(int((delta_h <= _meta_tol(24)).sum()), len(df1), 2.5)
    ind1["nome"] = "Comercial — Início processo <24h"

    # ─── Indicador 2: Anúncio <72h ÚTEIS (saída Aval.Téc OU NIDO → Publicação) ───
    col_avt_out = "Última vez que saiu da fase Avaliação Técnica"
    col_nido_out = "Última vez que saiu da fase Cadastro / Reativação no NIDO"
    col_pub = "Data publicação Anúncio"
    # Liberação = saída AvalTec; fallback = saída Cadastro/NIDO
    liberacao = df[col_avt_out].where(df[col_avt_out].notna(), df[col_nido_out])
    # Denominador: cards que saíram da Aval.Téc OU foram publicados
    mask_den = liberacao.notna() | df[col_pub].notna()
    df2 = df[mask_den].copy()
    lib2 = liberacao[mask_den]
    pub2 = df2[col_pub]
    # Numerador: (publicação - liberação) ≤ 72h ÚTEIS. Se liberação ou publicação ausente → falha.
    delta_h2 = pd.Series([horas_uteis(i, f) for i, f in zip(lib2, pub2)], index=df2.index)
    ok2 = int((delta_h2 <= _meta_tol(72)).sum())
    ind2 = score_indicador(ok2, len(df2), 2.5)
    ind2["nome"] = "Comercial — Anúncio publicado <72h"

    # ─── Indicador 3: Coluna correta ───
    col_cf_in = "Primeira vez que entrou na fase Conferência Final"
    now = _now_ref(ref)
    # Denominador: passou por Conferência Final E não está em Concluído
    mask3 = df[col_cf_in].notna() & (df["Fase atual"] != "Concluído")
    df3 = df[mask3].copy()
    dias_desocup = (now - df3[col_pub]).dt.total_seconds() / 86400.0
    expected = dias_desocup.apply(_expected_phase_desocupacao)
    ok3 = int((df3["Fase atual"] == expected).sum())
    ind3 = score_indicador(ok3, len(df3), 5)
    ind3["nome"] = "Comercial — Card na coluna correta"

    indicadores = [ind1, ind2, ind3]
    return {
        "nota": nota_processo(indicadores, bonus_n=bonus_n),
        "indicadores": indicadores,
    }


def calc_caio_contrato_locacao(df_comercial: pd.DataFrame, df_cont_loc: pd.DataFrame,
                               ref: Optional[datetime] = None) -> dict:
    """
    Caio · Cont. Locação · 2 indicadores · peso 10.

    Indicador 4: Ocupação <30d (peso 6) — Data pub Anúncio (Comercial) → 1º Boleto (Cont.Loc),
        cruzamento via IM. Pareamento: para cada 1º Boleto, parear com anúncio anterior + próximo.
        Excluir 'alugado antes de re-anunciar' (anúncio posterior ao boleto).
    Indicador 5: Documentação <24h úteis (peso 4) — Criado em → Entrada Confecção do contrato de locação.
    """
    com = excluir_rascunhos(df_comercial)
    com = aplicar_cutoff(com, "Criado em", ref=ref)
    com = filtrar_por_assignee(com, "Profissional responsável", "Caio")

    cl = excluir_rascunhos(df_cont_loc)
    cl = aplicar_cutoff(cl, "Criado em", ref=ref)

    # ── Indicador 4: Ocupação <30d (cross-pipe) ──
    col_pub = "Data publicação Anúncio"
    col_boleto = "Primeira vez que entrou na fase 1º Boleto"
    pub_por_im: dict[int, list[pd.Timestamp]] = {}
    for im_val, pub in com[["IM", col_pub]].dropna(subset=[col_pub]).itertuples(index=False):
        if pd.isna(im_val):
            continue
        pub_por_im.setdefault(int(im_val), []).append(pd.Timestamp(pub))

    bol_por_im: dict[int, list[pd.Timestamp]] = {}
    for imovel_val, bol in cl[["Imóvel", col_boleto]].itertuples(index=False):
        if pd.isna(bol):
            continue
        im = extrair_im(imovel_val)
        if im is None:
            continue
        bol_por_im.setdefault(im, []).append(pd.Timestamp(bol))

    ims_comum = sorted(set(pub_por_im) & set(bol_por_im))
    ok4, tot4 = 0, 0
    for im in ims_comum:
        pubs = sorted(pub_por_im[im])
        for bol in sorted(bol_por_im[im]):
            # parear com publicação ANTERIOR mais próxima
            anteriores = [p for p in pubs if p <= bol]
            posteriores = [p for p in pubs if p > bol]
            if not anteriores:
                if posteriores:
                    continue  # "alugado antes de re-anunciar" → EXCLUIR
                continue      # sem anúncio no período → não medível
            pub_mais_proxima = anteriores[-1]
            dias = (bol - pub_mais_proxima).total_seconds() / 86400.0
            dias = max(dias, 0.0)  # negativos = 0 (✓)
            tot4 += 1
            if dias <= 30:
                ok4 += 1
    ind4 = score_indicador(ok4, tot4, 6)
    ind4["nome"] = "Cont. Locação — Ocupação <30d"

    # ── Indicador 5: Documentação <24h úteis ──
    col_conf_in = "Primeira vez que entrou na fase Confecção do contrato de locação"
    cl5 = cl.dropna(subset=[col_conf_in])
    horas = cl5.apply(lambda r: horas_uteis(r["Criado em"], r[col_conf_in]), axis=1)
    ok5 = int((horas <= _meta_tol(24)).sum())
    ind5 = score_indicador(ok5, len(cl5), 4)
    ind5["nome"] = "Cont. Locação — Documentação <24h"

    indicadores = [ind4, ind5]
    return {"nota": nota_processo(indicadores), "indicadores": indicadores}


def calc_caio_contrato_adm(df_cont_adm: pd.DataFrame,
                           ref: Optional[datetime] = None) -> dict:
    """
    Caio · Cont. ADM · 1 indicador · peso 10.

    Indicador 6: Criação → Primeira vez fase 'Contrato assinado - Conferir Nido' <7d corrido.
    Cutoff FIXO 01/03/2026. Pipe compartilhado — sem filtro pessoal (Caio responde pela ponta comercial).
    """
    df = excluir_rascunhos(df_cont_adm)
    df = aplicar_cutoff(df, "Criado em", data_fixa=CUTOFF_CONT_ADM_CAIO_FIXO)

    col_nido = "Primeira vez que entrou na fase Contrato assinado - Conferir Nido"
    df6 = df.dropna(subset=[col_nido]).copy()
    dias = (df6[col_nido] - df6["Criado em"]).dt.total_seconds() / 86400.0
    dias = dias.clip(lower=0)
    ok6 = int((dias < 7).sum())
    ind6 = score_indicador(ok6, len(df6), 10)
    ind6["nome"] = "Cont. ADM — Criação→NIDO <7d"

    return {"nota": nota_processo([ind6]), "indicadores": [ind6]}


def calc_caio_renovacao(df_renov: pd.DataFrame,
                       ref: Optional[datetime] = None) -> dict:
    """
    Caio · Renovação · 1 indicador EXCLUSIVO · peso 10.

    Indicador 7: Avaliação >90d antes vencimento — Data de vencimento − Última saída Avaliação de mercado.
    Sem filtro pessoal (Caio responde pelo lado comercial da renovação).
    """
    df = excluir_rascunhos(df_renov)
    df = aplicar_cutoff(df, "Criado em", ref=ref)

    col_aval_out = "Última vez que saiu da fase Avaliação de mercado"
    col_venc = "Data de vencimento"
    df7 = df.dropna(subset=[col_aval_out, col_venc]).copy()
    dias = (df7[col_venc] - df7[col_aval_out]).dt.total_seconds() / 86400.0
    ok7 = int((dias > 90).sum())
    ind7 = score_indicador(ok7, len(df7), 10)
    ind7["nome"] = "Renovação — Avaliação >90d"

    return {"nota": nota_processo([ind7]), "indicadores": [ind7]}


# ─────────────────────────────────────────────────────────────────────
# OCTADESK — helpers compartilhados (WhatsApp + Tickets)
# ─────────────────────────────────────────────────────────────────────

WA_POS = {"Satisfeito", "Muito satisfeito"}
WA_EXC = {"Não respondeu", "Não enviado"}
TKT_AVAL_POS = {"Bom", "Bom com comentário"}
TKT_AVAL_EXC = {"Não respondeu", "Não enviado"}

COL_WA_RESP   = "Responsável da conversa"
COL_WA_TEMPO  = "Tempo de espera após atribuição"
COL_WA_SAT    = "Pesquisa de satisfação"

COL_TKT_CAT    = "Categoria de assunto do ticket"
COL_TKT_STATUS = "Status do ticket"
COL_TKT_ASSUNTO = "Assunto do ticket"
COL_TKT_RESP   = "Responsável do ticket"
COL_TKT_IN     = "Data de entrada"
COL_TKT_RESP_T = "Data da primeira resposta"
COL_AVAL_RESP  = "Responsável do ticket"
COL_AVAL_TIPO  = "Tipo de avaliação"


def _parse_hms(s) -> Optional[float]:
    """'H:MM:SS' → minutos (float). None se inválido/NaN."""
    if not isinstance(s, str):
        return None
    parts = s.split(":")
    if len(parts) != 3:
        return None
    try:
        h, m, ss = int(parts[0]), int(parts[1]), int(parts[2])
        return h * 60 + m + ss / 60.0
    except ValueError:
        return None


def _match_nome(serie: pd.Series, nome) -> pd.Series:
    """
    Mask booleana de match EXATO (case-insensitive), aceitando str ou lista de variantes.

    Match exato evita falsos positivos quando o sistema externo (Octadesk) tem
    homônimos parciais — por exemplo, "Caio Rodrigues" não deve casar com algum
    futuro "Caio Silva". Para Vivianne, a lista contempla "Vivianne Fontes" e
    "VIVIANNE FONTES" (variantes confirmadas em snapshots históricos).
    """
    s = serie.astype(str).str.strip().str.upper()
    if isinstance(nome, list):
        targets = {n.strip().upper() for n in nome}
        return s.isin(targets)
    return s == nome.strip().upper()


def _whatsapp_indicadores(df_conv: pd.DataFrame, nome_responsavel,
                           peso_resposta: int = 4, peso_aval: int = 3) -> list[dict]:
    """Retorna 2 indicadores de WhatsApp para um responsável."""
    if df_conv is None or len(df_conv) == 0 or COL_WA_RESP not in df_conv.columns:
        return []
    df = df_conv[_match_nome(df_conv[COL_WA_RESP], nome_responsavel)].copy()

    # Ind 1: Resposta ≤5min
    tempo_min = df[COL_WA_TEMPO].apply(_parse_hms) if COL_WA_TEMPO in df.columns else pd.Series(dtype=float)
    val = tempo_min.dropna()
    ok1 = int((val <= 5).sum())
    ind1 = score_indicador(ok1, len(val), peso_resposta)
    ind1["nome"] = "WhatsApp — Resposta ≤5min"

    # Ind 2: Avaliações positivas
    if COL_WA_SAT in df.columns:
        sat = df[COL_WA_SAT].astype(str)
        denom = sat[~sat.isin(WA_EXC) & sat.notna() & (sat != "nan")]
        ok2 = int(denom.isin(WA_POS).sum())
    else:
        ok2, denom = 0, []
    ind2 = score_indicador(ok2, len(denom), peso_aval)
    ind2["nome"] = "WhatsApp — Avaliações positivas"

    return [ind1, ind2]


def _tickets_filtrados(df_tickets: pd.DataFrame, nome_responsavel) -> pd.DataFrame:
    """Aplica exclusões obrigatórias (manual §3.8) + filtro por responsável."""
    if df_tickets is None or len(df_tickets) == 0:
        return df_tickets if df_tickets is not None else pd.DataFrame()
    df = df_tickets.copy()
    # Exclusões
    if COL_TKT_CAT in df.columns:
        df = df[df[COL_TKT_CAT].astype(str) != "Cancelado / Spam"]
    if COL_TKT_STATUS in df.columns:
        df = df[df[COL_TKT_STATUS].astype(str) != "Cancelado"]
    if COL_TKT_ASSUNTO in df.columns:
        df = df[df[COL_TKT_ASSUNTO].astype(str).str.lower() != "tarefa"]
    # Filtro responsável
    if COL_TKT_RESP in df.columns:
        df = df[_match_nome(df[COL_TKT_RESP], nome_responsavel)]
    else:
        df = df.iloc[0:0]
    return df.copy()


def _ticket_sla_ind(df_filtrado: pd.DataFrame, peso: int) -> dict:
    """SLA ≤4h úteis (Data de entrada → Data da primeira resposta)."""
    if len(df_filtrado) == 0 or COL_TKT_IN not in df_filtrado.columns or COL_TKT_RESP_T not in df_filtrado.columns:
        ind = score_indicador(0, 0, peso)
    else:
        sub = df_filtrado.dropna(subset=[COL_TKT_IN, COL_TKT_RESP_T]).copy()
        h = sub.apply(lambda r: horas_uteis(r[COL_TKT_IN], r[COL_TKT_RESP_T]), axis=1) if len(sub) else pd.Series(dtype=float)
        ok = int((h <= _meta_tol(4)).sum()) if len(sub) else 0
        ind = score_indicador(ok, len(sub), peso)
    ind["nome"] = "Tickets — SLA <4h úteis"
    return ind


def _ticket_aval_ind(df_aval: pd.DataFrame, nome_responsavel, peso: int) -> dict:
    """Avaliações positivas — "Bom" + "Bom com comentário"."""
    if df_aval is None or len(df_aval) == 0 or COL_AVAL_RESP not in df_aval.columns:
        ind = score_indicador(0, 0, peso)
    else:
        df = df_aval[_match_nome(df_aval[COL_AVAL_RESP], nome_responsavel)].copy()
        tipos = df[COL_AVAL_TIPO].astype(str) if COL_AVAL_TIPO in df.columns else pd.Series(dtype=str)
        denom = tipos[~tipos.isin(TKT_AVAL_EXC) & tipos.notna() & (tipos != "nan")]
        ok = int(denom.isin(TKT_AVAL_POS).sum())
        ind = score_indicador(ok, len(denom), peso)
    ind["nome"] = "Tickets — Avaliações positivas"
    return ind


# ─────────────────────────────────────────────────────────────────────
# CAIO — Octadesk
# ─────────────────────────────────────────────────────────────────────

def calc_caio_whatsapp(df_conv: pd.DataFrame) -> dict:
    """
    Caio · WhatsApp · 2 indicadores · peso 7.
    Filtro: Responsável da conversa = "Caio Rodrigues"
    """
    if df_conv is None or len(df_conv) == 0:
        return {"nota": None, "indicadores": []}
    indicadores = _whatsapp_indicadores(df_conv, NOMES_AGENTE["caio"]["whatsapp"],
                                         peso_resposta=6, peso_aval=4)
    return {"nota": nota_processo(indicadores), "indicadores": indicadores}


def calc_caio_ticket(df_tickets: pd.DataFrame, df_aval: pd.DataFrame) -> dict:
    """
    Caio · Ticket · 2 indicadores · peso 7.
    Filtro: Responsável do ticket contém "Caio"
    Exclusões: Categoria=Cancelado/Spam, Status=Cancelado, Assunto=Tarefa
    """
    if (df_tickets is None or len(df_tickets) == 0) and (df_aval is None or len(df_aval) == 0):
        return {"nota": None, "indicadores": []}
    nome = NOMES_AGENTE["caio"]["ticket"]
    df_t = _tickets_filtrados(df_tickets, nome)
    ind1 = _ticket_sla_ind(df_t, peso=6)      # 4:3 normalizado p/ somar 10
    ind2 = _ticket_aval_ind(df_aval, nome, peso=4)
    return {"nota": nota_processo([ind1, ind2]), "indicadores": [ind1, ind2]}


# ─────────────────────────────────────────────────────────────────────
# VIVIANNE — BackOffice + Inadimplência
# ─────────────────────────────────────────────────────────────────────

def calc_vivianne_contrato_adm(df_cont_adm: pd.DataFrame,
                               ref: Optional[datetime] = None) -> dict:
    """Vivianne · Cont. ADM · Confecção <2h úteis (peso 10)."""
    df = excluir_rascunhos(df_cont_adm)
    df = aplicar_cutoff(df, "Criado em", ref=ref)
    col_in = "Primeira vez que entrou na fase Confecção do contrato"
    col_lastin = "Última vez que entrou na fase Confecção do contrato"
    col_out = "Última vez que saiu da fase Confecção do contrato"
    col_dur = "Tempo total na fase Confecção do contrato (dias)"
    sub = df.dropna(subset=[col_in, col_out]).copy()
    # horas_uteis_fase: robusto a reabertura (12ª Ed). Visita única → idêntico
    # ao antigo horas_uteis(in, out); reaberto → usa o duration real na fase.
    horas = sub.apply(
        lambda r: horas_uteis_fase(r[col_in], r.get(col_lastin), r[col_out], r.get(col_dur)),
        axis=1,
    )
    ok = int((horas <= _meta_tol(2)).sum())
    ind = score_indicador(ok, len(sub), 10)
    ind["nome"] = "Cont. ADM — Confecção <2h"
    return {"nota": nota_processo([ind]), "indicadores": [ind]}


def calc_vivianne_rescisao_adm(df_resc_adm: pd.DataFrame,
                               ref: Optional[datetime] = None) -> dict:
    """Vivianne · Rescisão ADM · Encerramento ≤4h ÚTEIS na fase (peso 10)."""
    # Usa duration cumulativo (Pipefy phases_history.duration). lastTimeOut-firstTimeIn
    # inflaria o tempo quando o card sai e volta para Encerramento (pendência financeira etc.).
    df = excluir_rascunhos(df_resc_adm)
    df = aplicar_cutoff(df, "Criado em", ref=ref)
    col_in = "Primeira vez que entrou na fase Encerramento"
    col_out = "Última vez que saiu da fase Encerramento"
    col_dur = "Tempo total na fase Encerramento (dias)"
    # HORAS ÚTEIS (decisão da gestora, 12/08/2026): metas curtas em horas
    # corridas empurravam gente a trabalhar fora do expediente por medo do
    # ranking. Medida em horas úteis (08-18h, seg-sex), quem entrega segunda
    # de manhã é medido igual a quem entrega quinta à tarde.
    col_lastin = "Última vez que entrou na fase Encerramento"
    sub = df.dropna(subset=[col_in, col_out, col_dur]).copy()
    horas = sub.apply(lambda r: horas_uteis_fase(
        r[col_in], r.get(col_lastin), r[col_out], r.get(col_dur)), axis=1)
    ok = int((horas <= _meta_tol(4)).sum())
    ind = score_indicador(ok, len(sub), 10)
    ind["nome"] = "Rescisão ADM — Encerramento <4h"
    return {"nota": nota_processo([ind]), "indicadores": [ind]}


def calc_vivianne_contrato_locacao(df_cont_loc: pd.DataFrame,
                                   ref: Optional[datetime] = None) -> dict:
    """
    Vivianne · Cont. Locação · 2 indicadores · peso 10.
    3a: NIDO→Concluído <24h ÚTEIS (peso 5)
    3b: Confecção <2h ÚTEIS dentro da fase (peso 5)
    """
    df = excluir_rascunhos(df_cont_loc)
    df = aplicar_cutoff(df, "Criado em", ref=ref)

    # 3a: NIDO→Concluído <24h ÚTEIS
    col_nido = "Primeira vez que entrou na fase Fechamento NIDO"
    col_concl = "Primeira vez que entrou na fase Concluído"
    sub_a = df.dropna(subset=[col_nido, col_concl]).copy()
    # HORAS ÚTEIS (decisão da gestora, 12/08/2026): metas curtas em horas
    # corridas empurravam gente a trabalhar fora do expediente por medo do
    # ranking. Medida em horas úteis (08-18h, seg-sex), quem entrega segunda
    # de manhã é medido igual a quem entrega quinta à tarde.
    horas_a = sub_a.apply(lambda r: horas_uteis(r[col_nido], r[col_concl]), axis=1)
    ok_a = int((horas_a <= _meta_tol(24)).sum())
    ind_a = score_indicador(ok_a, len(sub_a), 5)
    ind_a["nome"] = "Cont. Locação — NIDO→Concluído <24h"

    # 3b: Confecção <2h em horas ÚTEIS dentro da fase (era corrido até 12/08/2026)
    F_CL = "Confecção do contrato de locação"
    col_tempo_conf = f"Tempo total na fase {F_CL} (dias)"
    sub_b = df.dropna(subset=[col_tempo_conf]).copy()
    horas_b = sub_b.apply(lambda r: horas_uteis_fase(
        r.get(f"Primeira vez que entrou na fase {F_CL}"),
        r.get(f"Última vez que entrou na fase {F_CL}"),
        r.get(f"Última vez que saiu da fase {F_CL}"), r.get(col_tempo_conf)), axis=1)
    ok_b = int((horas_b <= _meta_tol(2)).sum())
    ind_b = score_indicador(ok_b, len(sub_b), 5)
    ind_b["nome"] = "Cont. Locação — Confecção <2h"

    indicadores = [ind_a, ind_b]
    return {"nota": nota_processo(indicadores), "indicadores": indicadores}


def calc_vivianne_rescisao_locacao(df_resc_loc: pd.DataFrame,
                                   ref: Optional[datetime] = None) -> dict:
    """
    Vivianne · Rescisão Loc. · 2 indicadores BackOffice · peso 10.
    4a: Levant. Taxas Proporcionais ≤2h ÚTEIS dentro da fase (peso 5)
    4b: Levantamento de taxas ≤2h ÚTEIS dentro da fase (peso 5)
    """
    df = excluir_rascunhos(df_resc_loc)
    df = aplicar_cutoff(df, "Criado em", ref=ref)

    col_prop = "Tempo total na fase Levant. Taxas Proporcionais (dias)"
    col_final = "Tempo total na fase Levantamento de taxas (dias)"

    # HORAS ÚTEIS (decisão da gestora, 12/08/2026): metas curtas em horas
    # corridas empurravam gente a trabalhar fora do expediente por medo do
    # ranking. Medida em horas úteis (08-18h, seg-sex), quem entrega segunda
    # de manhã é medido igual a quem entrega quinta à tarde.
    F_P = "Levant. Taxas Proporcionais"
    sub_a = df.dropna(subset=[col_prop]).copy()
    horas_a = sub_a.apply(lambda r: horas_uteis_fase(
        r.get(f"Primeira vez que entrou na fase {F_P}"),
        r.get(f"Última vez que entrou na fase {F_P}"),
        r.get(f"Última vez que saiu da fase {F_P}"), r.get(col_prop)), axis=1)
    ok_a = int((horas_a <= _meta_tol(2)).sum())
    ind_a = score_indicador(ok_a, len(sub_a), 5)
    ind_a["nome"] = "Rescisão Loc. — Levant. Taxas Prop <2h"

    F_F = "Levantamento de taxas"
    sub_b = df.dropna(subset=[col_final]).copy()
    horas_b = sub_b.apply(lambda r: horas_uteis_fase(
        r.get(f"Primeira vez que entrou na fase {F_F}"),
        r.get(f"Última vez que entrou na fase {F_F}"),
        r.get(f"Última vez que saiu da fase {F_F}"), r.get(col_final)), axis=1)
    ok_b = int((horas_b <= _meta_tol(2)).sum())
    ind_b = score_indicador(ok_b, len(sub_b), 5)
    ind_b["nome"] = "Rescisão Loc. — Levant. Taxas Final <2h"

    indicadores = [ind_a, ind_b]
    return {"nota": nota_processo(indicadores), "indicadores": indicadores}


def calc_vivianne_renovacao(df_renov: pd.DataFrame,
                            ref: Optional[datetime] = None) -> dict:
    """
    Vivianne · Renovação · 2 indicadores · peso 10.
    5: Confecção <4h CORRIDO (Pipefy col tempo × 24) (peso 5)
    6: Finalização <16h ÚTEIS — entrada Contrato assinado/Finalizar → entrada Processo concluído (peso 5)
    """
    df = excluir_rascunhos(df_renov)
    df = aplicar_cutoff(df, "Criado em", ref=ref)

    col_tempo_conf = "Tempo total na fase Confecção do contrato (dias)"
    # HORAS ÚTEIS (decisão da gestora, 12/08/2026): metas curtas em horas
    # corridas empurravam gente a trabalhar fora do expediente por medo do
    # ranking. Medida em horas úteis (08-18h, seg-sex), quem entrega segunda
    # de manhã é medido igual a quem entrega quinta à tarde.
    F_C = "Confecção do contrato"
    sub_5 = df.dropna(subset=[col_tempo_conf]).copy()
    horas_5 = sub_5.apply(lambda r: horas_uteis_fase(
        r.get(f"Primeira vez que entrou na fase {F_C}"),
        r.get(f"Última vez que entrou na fase {F_C}"),
        r.get(f"Última vez que saiu da fase {F_C}"), r.get(col_tempo_conf)), axis=1)
    ok_5 = int((horas_5 <= _meta_tol(4)).sum())
    ind_5 = score_indicador(ok_5, len(sub_5), 5)
    ind_5["nome"] = "Renovação — Confecção <4h"

    col_fin_in = "Primeira vez que entrou na fase Contrato assinado / Finalizar"
    col_proc_concl = "Primeira vez que entrou na fase Processo concluído"
    sub_6 = df.dropna(subset=[col_fin_in, col_proc_concl]).copy()
    horas_6 = sub_6.apply(lambda r: horas_uteis(r[col_fin_in], r[col_proc_concl]), axis=1)
    ok_6 = int((horas_6 <= _meta_tol(16)).sum())
    ind_6 = score_indicador(ok_6, len(sub_6), 5)
    ind_6["nome"] = "Renovação — Finalização <16h"

    indicadores = [ind_5, ind_6]
    return {"nota": nota_processo(indicadores), "indicadores": indicadores}


def calc_vivianne_inadimplencia(df_inad: pd.DataFrame, bonus_n: int = 0,
                                ref: Optional[datetime] = None,
                                bonus_tot: int = 0, cobrados: int = 0) -> dict:
    """
    Vivianne · Inadimplência · 4 indicadores · peso total 10.

    ⚠️ 13ª ED (13/08/2026): "Cobrança antes do repasse" DEIXOU DE SER BÔNUS e
    virou indicador com o MAIOR peso do processo (decisão da gestora). Ele já
    tinha numerador E denominador calculados (47 de 113) — era um indicador
    vestido de bônus. Como bônus ele carregava 92% do peso e travava a nota
    em 9,7, escondendo que a Negativação está em 1/17.

    7:  Cobrança ≤8h ÚTEIS — VELOCIDADE de abrir o card (peso 2)
    8:  CredPago ≤15d corrido (peso 1,25)
    9:  Negativação 7-9d corrido (peso 1,25)
    10: Cobrança dos boletos em atraso — COBERTURA (cobrados / bonus_tot) (peso 2,5)
    11: Recebido antes do repasse — RESULTADO (bonus_n / cobrados) (peso 3) ← maior

    ⚠️ POR QUE 10 E 11 SÃO SEPARADOS (decisão da gestora, 13/08/2026)
    ----------------------------------------------------------------
    Até aqui existia um indicador só, "Cobrança antes do repasse" = 47/113, que
    misturava duas coisas de responsabilidade diferente:
      • ABRIR a cobrança é 100% da Vivianne;
      • o locatário PAGAR antes do repasse não é.
    Um boleto cobrado no dia certo em que o locatário só pagou depois do repasse
    contava igual a um boleto que ela nem viu. Agora:
      10 mede se ela viu e agiu     → 64/113
      11 mede o resultado do que cobrou → 47/64

    Bônus N: boletos em atraso recebidos antes do repasse — passado como bonus_n.
    """
    df = excluir_rascunhos(df_inad)
    df = aplicar_cutoff(df, "Criado em", ref=ref)

    # 7: Cobrança ≤8h ÚTEIS
    col_cob = "Primeira vez que entrou na fase Cobrança (inicial)"  # nome no manual / fields_map (com parênteses)
    sub_7 = df.dropna(subset=[col_cob]).copy()
    # HORAS ÚTEIS (decisão da gestora, 12/08/2026): metas curtas em horas
    # corridas empurravam gente a trabalhar fora do expediente por medo do
    # ranking. Medida em horas úteis (08-18h, seg-sex), quem entrega segunda
    # de manhã é medido igual a quem entrega quinta à tarde.
    # ⚠️ META REAPERTADA junto com a conversão: em horas úteis, 24h aprovaria
    # 96,6% dos cards e o indicador deixaria de discriminar. 8h úteis = "no
    # mesmo dia útil", que preserva a urgência original sem exigir madrugada.
    horas_7 = sub_7.apply(lambda r: horas_uteis(r["Criado em"], r[col_cob]), axis=1)
    ok_7 = int((horas_7 <= _meta_tol(8)).sum())
    ind_7 = score_indicador(ok_7, len(sub_7), 2)
    ind_7["nome"] = "Inadimplência — Cobrança <8h úteis"

    # 8: CredPago ≤15d corrido a partir de Vencimento 1º Boleto:
    col_venc = "Vencimento 1º Boleto:"
    col_credpago = "Primeira vez que entrou na fase CredPago: Acionar"
    sub_8 = df.dropna(subset=[col_venc, col_credpago]).copy()
    dias_8 = (sub_8[col_credpago] - sub_8[col_venc]).dt.total_seconds() / 86400
    dias_8 = dias_8.clip(lower=0)
    ok_8 = int((dias_8 <= 15).sum())
    ind_8 = score_indicador(ok_8, len(sub_8), 1.25)
    ind_8["nome"] = "Inadimplência — CredPago ≤15d"

    # 9: Negativação 7-9d corrido a partir de Vencimento 1º Boleto:
    col_neg = "Primeira vez que entrou na fase Negativação (No 8º dia de atraso)"
    sub_9 = df.dropna(subset=[col_venc, col_neg]).copy()
    dias_9 = (sub_9[col_neg] - sub_9[col_venc]).dt.total_seconds() / 86400
    ok_9 = int(((dias_9 >= 7) & (dias_9 <= 9)).sum())
    ind_9 = score_indicador(ok_9, len(sub_9), 1.25)
    ind_9["nome"] = "Inadimplência — Negativação 7-9d"

    # 10: COBERTURA — dos boletos em atraso, em quantos ela abriu cobrança
    ind_10 = score_indicador(int(cobrados), int(bonus_tot), 2.5)
    ind_10["nome"] = "Inadimplência — Cobrança dos boletos em atraso"

    # 11: RESULTADO — dos que ela cobrou, quantos entraram antes do repasse
    ind_11 = score_indicador(int(bonus_n), int(cobrados), 3)
    ind_11["nome"] = "Inadimplência — Recebido antes do repasse"

    indicadores = [ind_7, ind_8, ind_9, ind_10, ind_11]
    return {"nota": nota_processo(indicadores), "indicadores": indicadores}


def calc_vivianne_backoffice(df_bo: pd.DataFrame,
                             ref: Optional[datetime] = None) -> dict:
    """
    Vivianne · BackOffice · 2 indicadores · peso 10.
    Separar cards por 'Primeira vez fase ↪️ Troca de Titularidade':
    - SEM troca → Indicador 10: Concluído <24h ÚTEIS (peso 5)
    - COM troca → Indicador 11: Troca <5d úteis = 50h úteis (peso 5)
    """
    df = excluir_rascunhos(df_bo)
    df = aplicar_cutoff(df, "Criado em", ref=ref)

    col_troca = "Primeira vez que entrou na fase ↪️ Troca de Titularidade"
    col_concl = "Primeira vez que entrou na fase Concluído"

    com_troca = df[df[col_troca].notna()].copy()
    sem_troca = df[df[col_troca].isna()].copy()

    # 10: SEM troca, Concluído <24h ÚTEIS
    sub_10 = sem_troca.dropna(subset=[col_concl]).copy()
    # HORAS ÚTEIS (decisão da gestora, 12/08/2026): metas curtas em horas
    # corridas empurravam gente a trabalhar fora do expediente por medo do
    # ranking. Medida em horas úteis (08-18h, seg-sex), quem entrega segunda
    # de manhã é medido igual a quem entrega quinta à tarde.
    horas_10 = sub_10.apply(lambda r: horas_uteis(r["Criado em"], r[col_concl]), axis=1)
    ok_10 = int((horas_10 <= _meta_tol(24)).sum())
    ind_10 = score_indicador(ok_10, len(sub_10), 5)
    ind_10["nome"] = "BackOffice — Concluído <24h"

    # 11: COM troca, Concluído <50h úteis (= 5d úteis)
    sub_11 = com_troca.dropna(subset=[col_concl]).copy()
    horas_11 = sub_11.apply(lambda r: horas_uteis(r["Criado em"], r[col_concl]), axis=1)
    ok_11 = int((horas_11 <= 50).sum())
    ind_11 = score_indicador(ok_11, len(sub_11), 5)
    ind_11["nome"] = "BackOffice — Troca Titularidade <5d"

    indicadores = [ind_10, ind_11]
    return {"nota": nota_processo(indicadores), "indicadores": indicadores}


def calc_vivianne_ticket(df_tickets: pd.DataFrame) -> dict:
    """
    Vivianne · Ticket · 1 indicador · peso 10.
    Filtro: Responsável contém "Vivianne Fontes" ou "VIVIANNE FONTES"
    Indicador: SLA ≤4h úteis (peso 10).
    Avaliações EXCLUÍDAS (manual: 0 registros — não entra no cálculo).

    ⚠️ Peso 10 e não 4 (13/08/2026): como é o ÚNICO indicador do processo, a nota
    é idêntica nos dois casos (a fórmula normaliza pela soma dos pesos). Mas era
    o último processo do ranking que não somava 10, e peso baixo é justamente o
    que amplifica distorção se um bônus for criado aqui no futuro.
    """
    if df_tickets is None or len(df_tickets) == 0:
        return {"nota": None, "indicadores": []}
    nome = NOMES_AGENTE["vivianne"]["ticket"]
    df_t = _tickets_filtrados(df_tickets, nome)
    ind1 = _ticket_sla_ind(df_t, peso=10)
    return {"nota": nota_processo([ind1]), "indicadores": [ind1]}


# ─────────────────────────────────────────────────────────────────────
# NATÁLIA / GARDÊNIA — Assessoras (helpers reaproveitáveis)
# ─────────────────────────────────────────────────────────────────────

def _nome_assessora(assessora: str) -> str:
    """Converte chave interna → nome usado para filtro de assignee/select."""
    return {"natalia": "Natália", "gardenia": "Gardênia"}.get(assessora, assessora)


def _nome_assessora_alt(assessora: str) -> list[str]:
    """Variantes para casar em campos do tipo select (texto plano), evita falhar por acento."""
    if assessora == "natalia":
        return ["Natália", "Natalia"]
    if assessora == "gardenia":
        return ["Gardênia", "Gardenia"]
    return [assessora]


def _contem_qualquer(valor, nomes: list[str]) -> bool:
    for n in nomes:
        if contem_assignee(valor, n):
            return True
    return False


def calc_assessora_contrato_adm(df_cont_adm: pd.DataFrame, assessora: str, bonus_n: int = 0,
                                ref: Optional[datetime] = None) -> dict:
    """
    Assessora · Cont. ADM · 1 indicador · peso 10 + bônus vistoria de entrada.
    Indicador 1: Conferência ≤2h úteis — entrada/saída fase Conferência do contrato.
    Bônus N: cards onde 'Criar Card de Vistoria Técnica' está preenchido, filtrado por Assessor (lista).
    """
    df = excluir_rascunhos(df_cont_adm)
    df = aplicar_cutoff(df, "Criado em", ref=ref)

    nomes = _nome_assessora_alt(assessora)
    mask = df["Assessor (lista)"].apply(lambda v: _contem_qualquer(v, nomes))
    # Manual §4.3: cards sem Assessor (lista) mas concluídos → atribuídos à Gardênia.
    if assessora == "gardenia":
        sem_assessor = df["Assessor (lista)"].apply(lambda v: not _as_list(v))
        concluido = df["Primeira vez que entrou na fase Concluído"].notna()
        mask = mask | (sem_assessor & concluido)
    df_assess = df[mask].copy()

    col_in = "Primeira vez que entrou na fase Conferência do contrato"
    col_lastin = "Última vez que entrou na fase Conferência do contrato"
    col_out = "Última vez que saiu da fase Conferência do contrato"
    col_dur = "Tempo total na fase Conferência do contrato (dias)"
    sub = df_assess.dropna(subset=[col_in, col_out]).copy()
    # horas_uteis_fase: robusto a reabertura (12ª Ed) — ver calc_vivianne_contrato_adm.
    horas = sub.apply(
        lambda r: horas_uteis_fase(r[col_in], r.get(col_lastin), r[col_out], r.get(col_dur)),
        axis=1,
    )
    ok = int((horas <= _meta_tol(2)).sum())
    ind = score_indicador(ok, len(sub), 10)
    ind["nome"] = "Cont. ADM — Conferência ≤2h"

    return {"nota": nota_processo([ind], bonus_n=bonus_n), "indicadores": [ind]}


# Cards com ciclo NEGATIVO na Conclusão da Rescisão ADM (passagem-fantasma).
# Contam ✗ e ficam aqui para conferência manual da gestora.
_RESC_ADM_FANTASMA: list = []


def calc_assessora_rescisao_adm(df_resc_adm: pd.DataFrame, assessora: str,
                                ref: Optional[datetime] = None) -> dict:
    """
    Assessora · Rescisão ADM · 2 indicadores + bônus · peso 10.

    ESTRUTURA NOVA — fechada com a gestora em 05/08/2026, valida a partir da 13ª Ed.
    Substitui a antiga (Repasse <12h peso 5 + Distrato assinado peso 5).
    O indicador "Repasse <12h" foi REMOVIDO — não reincluir.

    RECORTE: "Última vez que saiu da fase Caixa de entrada" nos últimos 180 dias
      (NÃO "Criado em"). Decisão da gestora: mantém no recorte cards reabertos,
      como o IM477, cuja 1ª saída da Caixa é de nov/2025 mas voltou a andar em jul/2026.

    Indicador 1 — Alinhamento com o proprietário ≤24h (peso 4)
      Medida: SOMA do tempo dentro da fase ("Tempo total na fase ... (dias)" × 24).
      Meta 24h ÚTEIS + 30 min de tolerância. Denominador: tempo na fase > 0.

    Indicador 2 — Conclusão da rescisão ≤10 dias (peso 6)
      PRIMEIRA saída da Caixa de entrada → PRIMEIRA saída do Repasse final.
      Ambas via primeira_saida_fase() — a coluna "Última vez que saiu" é
      contaminada pela passagem-fantasma do fechamento (ver auditoria 05/08/2026).
      Meta 10 dias corridos, SEM tolerância (tolerância só vale p/ metas em horas).
      Denominador: cards que ENTRARAM no Repasse final.
        entrou e não saiu = ✗ · nunca entrou = fora do denominador.

    Bônus — Distrato assinado: N = cards com o campo = "Sim" ("Não" não conta).

    Filtro: 'Assessor (lista)' contém nome (texto limpo no select).
    """
    df = excluir_rascunhos(df_resc_adm)
    nomes = _nome_assessora_alt(assessora)
    df = df[df["Assessor (lista)"].apply(lambda v: _contem_qualquer(v, nomes))].copy()
    # Recorte pela ÚLTIMA saída da Caixa de entrada (não por "Criado em").
    df = aplicar_cutoff(df, "Última vez que saiu da fase Caixa de entrada", ref=ref)

    F_ALI = "Alinhamento com o proprietário"
    F_REP = "Repasse final / Distrato (FINANCEIRO)"
    F_CX = "Caixa de entrada"

    # ── Indicador 1: Alinhamento ≤24h (tempo DENTRO da fase, imune a reabertura)
    col_ali_dur = f"Tempo total na fase {F_ALI} (dias)"
    if col_ali_dur in df.columns:
        # horas ÚTEIS dentro da fase (decisão da gestora, 12/08/2026)
        horas_ali = df.apply(lambda r: horas_uteis_fase(
            r.get(f"Primeira vez que entrou na fase {F_ALI}"),
            r.get(f"Última vez que entrou na fase {F_ALI}"),
            r.get(f"Última vez que saiu da fase {F_ALI}"),
            r.get(col_ali_dur)), axis=1)
    else:  # fase ainda não registrada em fields_map.json
        horas_ali = pd.Series(dtype="float64", index=df.index)
    sub_1 = df[horas_ali.notna() & (horas_ali > 0)]
    h1 = horas_ali.loc[sub_1.index]
    ok_1 = int((h1 <= _meta_tol(24)).sum())
    ind_1 = score_indicador(ok_1, len(sub_1), 3)
    ind_1["nome"] = "Rescisão ADM — Alinhamento ≤24h"

    # ── Indicador 2: Conclusão ≤10 dias (primeira saída → primeira saída)
    col_rep_in = f"Primeira vez que entrou na fase {F_REP}"
    sub_2 = df.dropna(subset=[col_rep_in]).copy()
    ok_2 = 0
    for _, r in sub_2.iterrows():
        inicio = primeira_saida_fase(r.get(f"Primeira vez que entrou na fase {F_CX}"),
                                     r.get(f"Última vez que entrou na fase {F_CX}"),
                                     r.get(f"Última vez que saiu da fase {F_CX}"),
                                     r.get(f"Tempo total na fase {F_CX} (dias)"))
        fim = primeira_saida_fase(r.get(col_rep_in),
                                  r.get(f"Última vez que entrou na fase {F_REP}"),
                                  r.get(f"Última vez que saiu da fase {F_REP}"),
                                  r.get(f"Tempo total na fase {F_REP} (dias)"))
        if pd.isna(inicio) or pd.isna(fim):
            continue  # ainda na fase Repasse (ou sem saída da Caixa) → ✗
        # ⚠️ NÃO usar dias_corridos() aqui: ele zera negativos, e negativo neste
        # indicador NÃO é erro de digitação — é a passagem-fantasma. O card foi
        # arrastado pelas fases no fechamento e registrou entrada no Repasse
        # ANTES de sair da Caixa de entrada. Exemplo: IM1353, que ficou parado
        # na Caixa de 02/12/2025 a 14/05/2026 (5 meses e meio) e era premiado
        # com ✓ pela regra "negativo → 0". Decisão da gestora em 13/08/2026:
        # ciclo negativo conta ✗ (mesmo tratamento dado ao IM1827).
        dias = (pd.Timestamp(fim) - pd.Timestamp(inicio)).total_seconds() / 86400
        if 0 <= dias <= 10:
            ok_2 += 1
        elif dias < 0:
            _RESC_ADM_FANTASMA.append(
                (assessora, str(r.get("Título") or r.get("Titulo") or ""), round(dias, 2)))
    ind_2 = score_indicador(ok_2, len(sub_2), 4)
    ind_2["nome"] = "Rescisão ADM — Conclusão ≤10 dias"

    # ── Indicador 3: Distrato assinado (peso 3) — era BÔNUS até 12/08/2026
    # 13ª Ed: virou indicador porque tem denominador natural. Como bônus ele
    # inflava a nota sem medir nada: Gardênia 3,50 aparecia 4,58.
    #
    # ⚠️ DENOMINADOR = CARDS CONCLUÍDOS (decisão da gestora, 13/08/2026), que é a
    # regra escrita nas instruções do Project. NÃO usar "cards com o campo
    # respondido": o campo está vazio em 11 dos 16 cards, e naquele desenho a
    # Natália tirava 2/2 = 100% justamente por ter só dois respondidos — deixar
    # em branco melhorava a nota. Card concluído sem distrato assinado é ✗,
    # esteja o campo em "Não" ou em branco.
    val = df.get("Termo de Distrato assinado", pd.Series(dtype=object)).astype(str).str.strip().str.lower()
    col_concl = f"Primeira vez que entrou na fase Concluído"
    concluidos = df.dropna(subset=[col_concl]) if col_concl in df.columns else df.iloc[0:0]
    dist_ok = int((val.reindex(concluidos.index) == "sim").sum())
    ind_3 = score_indicador(dist_ok, len(concluidos), 3)
    ind_3["nome"] = "Rescisão ADM — Distrato assinado"

    nota = nota_processo([ind_1, ind_2, ind_3])
    return {"nota": nota, "indicadores": [ind_1, ind_2, ind_3], "bonus_n": dist_ok}


# Cards com levantamento registrado ANTES da entrega das chaves.
# Saem do denominador e ficam aqui para conferência manual.
_RESC_LOC_NEGATIVOS: list = []


def calc_assessora_rescisao_locacao(df_resc_loc: pd.DataFrame, assessora: str,
                                    ref: Optional[datetime] = None,
                                    distratos: Optional[dict] = None) -> dict:
    """
    Assessora · Rescisão Loc. · 2 indicadores · peso 5.

    REGRA DE INÍCIO — REDESENHADA NA 13ª ED (decisão da gestora 13/08/2026)
    ----------------------------------------------------------------------
    A contagem começa quando as chaves são ENTREGUES. Ordem de prioridade:

      1ª) `data_distrato` do Imobiliar (tabela imobiliar_contratos_loc, cruzada
          pelo IM) — o campo "Encerramento". É a data que alimenta o cálculo do
          boleto final, então a equipe tem incentivo real de preenchê-la certo.
          ⚠️ NÃO usar o campo "Chaves" (`dataentrega`) do Imobiliar: aquele é
          quando a assessora SENTOU para registrar. Se recebe hoje e cadastra
          amanhã, traz amanhã — e o indicador viraria circular.
      2ª) `Data do recebimento das chaves:` (campo digitado no Pipefy)
      3ª) `Primeira vez que entrou na fase CHAVES RECEBIDAS`
      4ª) Fallback antigo, específico por indicador:
            Boleto prop  → `Última vez que saiu da fase Vistoria recebida`
            Boleto final → `Última vez que saiu da fase Agendamento de vistoria`

    POR QUE 48h E NÃO 24h NO BOLETO PROP
    ------------------------------------
    `data_distrato` é um DATE — não tem hora. A meta continua sendo "responder
    em 24h", mas medida a partir da meia-noite da data de entrega ela vira
    "até o fim do dia seguinte" = 48h. Recebeu na sexta, tem até segunda? Não:
    sexta + 48h cai no domingo, então precisa sair até domingo — ou seja, na
    prática precisa passar na sexta ou no sábado. É exatamente o que a gestora
    pediu em 13/08/2026.

    NEGATIVOS
    ---------
    Levantamento registrado ANTES da entrega das chaves não é atraso nem
    acerto: é inconsistência de cadastro. Sai do denominador e vai para
    `_RESC_LOC_NEGATIVOS` para conferência manual (IM344 e IM1742 hoje).

    Filtro: 'Assessor (lista)' contém nome (validado contra baseline 10ª).
    """
    df = excluir_rascunhos(df_resc_loc)
    df = aplicar_cutoff(df, "Criado em", ref=ref)
    nomes = _nome_assessora_alt(assessora)
    df = df[df["Assessor (lista)"].apply(lambda v: _contem_qualquer(v, nomes))].copy()

    chaves_campo = df["Data do recebimento das chaves:"]
    chaves_fase = df.get("Primeira vez que entrou na fase CHAVES RECEBIDAS",
                          pd.Series(pd.NaT, index=df.index))
    sai_vist = df["Última vez que saiu da fase Vistoria recebida"]
    sai_agend = df["Última vez que saiu da fase Agendamento de vistoria"]

    # 1ª prioridade: data_distrato do Imobiliar (meia-noite de Brasília, em UTC)
    distratos = distratos or {}
    def _distrato(r) -> pd.Timestamp:
        im = extrair_im(r.get("Imóvel")) or extrair_im(r.get("Título"))
        return distratos.get(im, pd.NaT) if im is not None else pd.NaT
    chaves_imob = (df.apply(_distrato, axis=1) if len(df)
                   else pd.Series(pd.NaT, index=df.index))
    chaves_imob = pd.to_datetime(chaves_imob, errors="coerce", utc=True)

    chaves_efetivas = chaves_imob.where(chaves_imob.notna(), chaves_campo)
    chaves_efetivas = chaves_efetivas.where(chaves_efetivas.notna(), chaves_fase)
    inicio_prop = chaves_efetivas.where(chaves_efetivas.notna(), sai_vist)
    inicio_final = chaves_efetivas.where(chaves_efetivas.notna(), sai_agend)
    col_lev_prop = "Primeira vez que entrou na fase Levant. Taxas Proporcionais"
    col_env_bol = "Primeira vez que entrou na fase Envio do boleto final"

    def _registrar_negativos(df_sub, delta, unidade):
        for idx in delta[delta < 0].index:
            _RESC_LOC_NEGATIVOS.append((assessora, unidade,
                                        str(df_sub.at[idx, "Título"]),
                                        round(float(delta[idx]), 2)))

    # 4: Boleto prop ≤48h (= "até o dia seguinte à entrega das chaves")
    mask_4 = inicio_prop.notna() & df[col_lev_prop].notna()
    sub_4 = df[mask_4].copy()
    horas_4 = (df.loc[mask_4, col_lev_prop] - inicio_prop[mask_4]).dt.total_seconds() / 3600
    _registrar_negativos(sub_4, horas_4, "Boleto prop (h)")
    val_4 = horas_4[horas_4 >= 0]           # negativo sai do denominador
    # 48h SEM tolerância: os 48h já SÃO a folga (meta de 24h medida a partir
    # da meia-noite da data de entrega). Somar margem seria contar duas vezes.
    ok_4 = int((val_4 <= 48).sum())
    ind_4 = score_indicador(ok_4, len(val_4), 4)
    ind_4["nome"] = "Rescisão Loc. — Boleto prop <48h"

    # 5: Boleto final <15d
    mask_5 = inicio_final.notna() & df[col_env_bol].notna()
    sub_5 = df[mask_5].copy()
    dias_5 = (df.loc[mask_5, col_env_bol] - inicio_final[mask_5]).dt.total_seconds() / 86400
    _registrar_negativos(sub_5, dias_5, "Boleto final (d)")
    val_5 = dias_5[dias_5 >= 0]
    ok_5 = int((val_5 <= 15).sum())
    ind_5 = score_indicador(ok_5, len(val_5), 6)
    ind_5["nome"] = "Rescisão Loc. — Boleto final <15d"

    indicadores = [ind_4, ind_5]
    return {"nota": nota_processo(indicadores), "indicadores": indicadores}


def calc_assessora_reparos(df_rep: pd.DataFrame, assessora: str,
                           ref: Optional[datetime] = None) -> dict:
    """
    Assessora · Reparos · 2 indicadores · peso 10.
    Filtro: 'Selecionar o assessor' contém nome.
    6: Orçamento <4h úteis (Criado em → entrada Orçamento|Prestador) (peso 4).
    7: Pós-venda ≤7d corrido (Criado em → entrada Pós-venda) (peso 6).
    """
    df = excluir_rascunhos(df_rep)
    df = aplicar_cutoff(df, "Criado em", ref=ref)
    nomes = _nome_assessora_alt(assessora)
    df = df[df["Selecionar o assessor"].apply(lambda v: _contem_qualquer(v, nomes))].copy()

    col_orc = "Primeira vez que entrou na fase Orçamento | Prestador"
    sub_6 = df.dropna(subset=[col_orc]).copy()
    horas_6 = sub_6.apply(lambda r: horas_uteis(r["Criado em"], r[col_orc]), axis=1)
    ok_6 = int((horas_6 <= _meta_tol(4)).sum())
    ind_6 = score_indicador(ok_6, len(sub_6), 4)
    ind_6["nome"] = "Reparos — Orçamento <4h"

    col_pos = "Primeira vez que entrou na fase Pós-venda"
    sub_7 = df.dropna(subset=[col_pos]).copy()
    dias_7 = (sub_7[col_pos] - sub_7["Criado em"]).dt.total_seconds() / 86400
    dias_7 = dias_7.clip(lower=0)
    ok_7 = int((dias_7 <= 7).sum())
    ind_7 = score_indicador(ok_7, len(sub_7), 6)
    ind_7["nome"] = "Reparos — Pós-venda ≤7d"

    indicadores = [ind_6, ind_7]
    return {"nota": nota_processo(indicadores), "indicadores": indicadores}


# Campo que decide se o contrato renova. São DOIS no Pipefy e eles se
# contradizem: no IM1592 o select diz "Sim" e o radio diz "Não" (a gestora
# confirmou que não houve renovação). O select guarda a intenção do início e
# não é atualizado quando a renovação cai depois.
# Decisão da gestora em 14/08/2026: vale o RADIO.
RENOV_CAMPO_RENOVA = "O contrato será renovado?"      # radio_vertical — oficial
RENOV_CAMPO_RENOVA_LEGADO = "Contrato será renovado?"  # select — não usar


def _renov_nao_renova(df: pd.DataFrame) -> pd.Series:
    """True nos cards marcados explicitamente como NÃO renovados.
    Campo vazio NÃO é tratado como "não renova" — só o "Não" explícito conta.
    """
    col = df.get(RENOV_CAMPO_RENOVA)
    if col is None:
        return pd.Series(False, index=df.index)
    return col.astype(str).str.strip().str.lower().isin(["não", "nao"])


# Antecedência mínima da renovação: meta de contato E critério de viabilidade
# do card. Card criado a menos disso do vencimento sai do denominador da
# assessora (decisão da gestora, 14/08/2026) e conta no indicador de abertura.
RENOV_ANTECEDENCIA_MIN = 60


def calc_assessora_renovacao(df_renov: pd.DataFrame, assessora: str,
                             ref: Optional[datetime] = None) -> dict:
    """
    Assessora · Renovação · 2 indicadores · peso 10.
    Filtro: 'Assessor (lista)' contém nome.
    8: Contato >60d antes vencimento — ENTRADA na fase Contato com proprietário (peso 4).
    9: Assinado antes vencimento (Primeira vez Contrato assinado/Finalizar < Data venc) (peso 6).

    ⚠️ DUAS CORREÇÕES DE 14/08/2026 (contestação da Gardênia, validada no banco)
    ---------------------------------------------------------------------------
    (1) ENTRADA na fase, não a última SAÍDA.
        Sair da fase depende do PROPRIETÁRIO responder, não da assessora agir.
        Caso IM126: entrou 29/04, ela enviou 07/05, e o card ficou parado até
        02/07 — 64 dias de espera contados contra ela. Medido pela saída dava
        57 dias (✗); pela entrada dá 121 (✓). Mesmo padrão em IM131, IM74, IM1778.
        ⚠️ Isso SUBSTITUI a instrução antiga do Project ("usar Última vez que SAIU").

    (2) CARD ABERTO TARDE SAI DO DENOMINADOR.
        Se o card nasce a menos de 60 dias do vencimento, a meta "contatar mais de
        60 dias antes" é matematicamente inatingível no instante da criação.
        Não é desempenho da assessora — quem abre os cards é outro setor.
        Casos reais: IM73/IM107/IM32 criados 5 dias DEPOIS do vencimento;
        IM395 com 1 dia; IM168 com 8; IM115 com 9.
        Medido em 14/08: 19 dos 34 cards (56%) estavam nessa situação.
        O contrapeso é o indicador de ABERTURA (ver calc_renovacao_abertura),
        para o gargalo aparecer no painel em vez de sumir.
    """
    df = excluir_rascunhos(df_renov)
    df = aplicar_cutoff(df, "Criado em", ref=ref)
    nomes = _nome_assessora_alt(assessora)
    df = df[df["Assessor (lista)"].apply(lambda v: _contem_qualquer(v, nomes))].copy()

    col_venc = "Data de vencimento"
    col_contato_in = "Primeira vez que entrou na fase Contato com proprietário"
    col_assinado = "Primeira vez que entrou na fase Contrato assinado / Finalizar"

    # Correção (2): fora do denominador os cards que já nasceram sem chance.
    df = df.dropna(subset=[col_venc]).copy()
    antecedencia = (df[col_venc] - df["Criado em"]).dt.total_seconds() / 86400
    df_viavel = df[antecedencia >= RENOV_ANTECEDENCIA_MIN].copy()

    # Correção (3), 14/08/2026: contrato que NÃO vai renovar sai do denominador.
    # Não há renovação a contatar nem a assinar. Usa o campo RADIO (o select
    # legado guarda a intenção inicial e não é atualizado — ver IM1592).
    df_viavel = df_viavel[~_renov_nao_renova(df_viavel)].copy()

    # 8: Contato >60d — correção (1): pela ENTRADA na fase
    sub_8 = df_viavel.dropna(subset=[col_contato_in]).copy()
    dias_8 = (sub_8[col_venc] - sub_8[col_contato_in]).dt.total_seconds() / 86400
    ok_8 = int((dias_8 > RENOV_ANTECEDENCIA_MIN).sum())
    ind_8 = score_indicador(ok_8, len(sub_8), 4)
    ind_8["nome"] = "Renovação — Contato >60d"

    # 9: Assinado antes do vencimento (mesmo denominador viável)
    # to_datetime(utc=True) nos dois lados: quando o recorte fica vazio, uma das
    # colunas pode vir tz-naive e a comparação estoura (pandas não compara
    # naive com aware). Aconteceu no teste com denominador zerado.
    sub_9 = df_viavel.dropna(subset=[col_assinado]).copy()
    _ass = pd.to_datetime(sub_9[col_assinado], errors="coerce", utc=True)
    _ven = pd.to_datetime(sub_9[col_venc], errors="coerce", utc=True)
    ok_9 = int((_ass < _ven).sum())
    ind_9 = score_indicador(ok_9, len(sub_9), 6)
    ind_9["nome"] = "Renovação — Assinado antes vencimento"

    # ── BÔNUS DE RECUPERAÇÃO (14/08/2026) ──────────────────────────────
    # Card que nasceu SEM PRAZO (menos de 60 dias do vencimento) mas que a
    # assessora conseguiu levar à assinatura ANTES do vencimento.
    #
    # Ao tirar os cards abertos tarde do denominador, a exclusão levava junto os
    # que ela SALVOU. Caso real: 1617/2 (SAUS Q6 BL K Sala 601) — card criado em
    # 29/07 para vencimento 31/08 (33 dias) e assinado em 10/08, com 21 dias de
    # folga. Mérito que a regra apagava.
    #
    # ⚠️ Por que bônus e não denominador: recolocar esses cards no indicador
    # traria de volta também os que ninguém salvou. Medido em 14/08, o
    # denominador "correto" (excluir só card criado após o vencimento) daria
    # Natália 4/8 e Gardênia 4/7 — as duas cairiam. O bônus premia o salvamento
    # sem cobrar o que nasceu inviável.
    fora_do_prazo = df[antecedencia < RENOV_ANTECEDENCIA_MIN]
    fora_do_prazo = fora_do_prazo[~_renov_nao_renova(fora_do_prazo)]
    salvos = fora_do_prazo.dropna(subset=[col_assinado])
    if len(salvos):
        _a = pd.to_datetime(salvos[col_assinado], errors="coerce", utc=True)
        _v = pd.to_datetime(salvos[col_venc], errors="coerce", utc=True)
        bonus_recup = int((_a < _v).sum())
    else:
        bonus_recup = 0

    indicadores = [ind_8, ind_9]
    return {"nota": nota_processo(indicadores, bonus_n=bonus_recup),
            "indicadores": indicadores, "bonus_n": bonus_recup}


def calc_renovacao_abertura(df_renov: pd.DataFrame,
                            ref: Optional[datetime] = None) -> dict:
    """
    Renovação · ABERTURA DO CARD — indicador de quem abre o processo (14/08/2026).

    Mede: cards de renovação criados com MAIS de 60 dias de antecedência do
    vencimento do contrato.

    ⚠️ NÃO ENTRA NO RANKING (decisão da gestora, 14/08/2026): quem abre os cards
    de renovação é a própria gestora, que não é avaliada. É DIAGNÓSTICO — sai no
    console do `run.py` para ela acompanhar a própria rotina de abertura.

    Medido em 14/08/2026: 57 de 76 cards com +60d. A abertura é em LOTE e alguns
    lotes saem tarde: 03/06 abriu 4 cards, os 4 com contrato já vencido;
    26/03 abriu 11, sendo 5 com menos de 60 dias (o pior com 6).
    """
    df = excluir_rascunhos(df_renov)
    df = aplicar_cutoff(df, "Criado em", ref=ref)
    col_venc = "Data de vencimento"
    sub = df.dropna(subset=[col_venc]).copy()
    antecedencia = (sub[col_venc] - sub["Criado em"]).dt.total_seconds() / 86400
    ok = int((antecedencia >= RENOV_ANTECEDENCIA_MIN).sum())
    ind = score_indicador(ok, len(sub), 10)
    ind["nome"] = "Renovação — Card aberto com +60d"

    # Divergência entre os dois campos de "vai renovar?" — enquanto os dois
    # existirem no Pipefy, qualquer regra lê o campo errado em algum card.
    def _norm(c):
        v = df.get(c)
        return (v.astype(str).str.strip().str.lower() if v is not None
                else pd.Series(dtype=object, index=df.index))
    radio, select = _norm(RENOV_CAMPO_RENOVA), _norm(RENOV_CAMPO_RENOVA_LEGADO)
    ambos = radio.isin(["sim", "não", "nao"]) & select.isin(["sim", "não", "nao"])
    divergem = int((ambos & (radio != select)).sum())

    return {"nota": nota_processo([ind]), "indicadores": [ind],
            "atrasados": int(len(sub) - ok),
            "nao_renovam": int(_renov_nao_renova(df).sum()),
            "campos_divergentes": divergem}


def calc_assessora_backoffice(df_bo: pd.DataFrame, assessora: str,
                              ref: Optional[datetime] = None) -> dict:
    """
    Assessora · BackOffice · 1 indicador · peso 10.
    Filtro: 'Responsável' contém nome (NÃO 'Criador').
    10: Pendência Assessor ≤24h ÚTEIS dentro da fase 🚩 Pendência Assessor.
    """
    df = excluir_rascunhos(df_bo)
    df = aplicar_cutoff(df, "Criado em", ref=ref)
    nomes = _nome_assessora_alt(assessora)
    # Filtro por `Responsáveis` (card.assignees Card-level — bate com export XLSX),
    # NÃO pelo field-form `Responsável` (que tem só Vivianne na maioria dos cards).
    df = df[df["Responsáveis"].apply(lambda v: _contem_qualquer(v, nomes))].copy()

    col_in = "Primeira vez que entrou na fase 🚩 Pendência Assessor"
    col_out = "Última vez que saiu da fase 🚩 Pendência Assessor"
    col_dur = "Tempo total na fase 🚩 Pendência Assessor (dias)"
    # Usa duration cumulativo (Pipefy phases_history.duration). lastTimeOut-firstTimeIn
    # inflaria o tempo quando o card sai e volta para a fase (reaberturas).
    # HORAS ÚTEIS (decisão da gestora, 12/08/2026): metas curtas em horas
    # corridas empurravam gente a trabalhar fora do expediente por medo do
    # ranking. Medida em horas úteis (08-18h, seg-sex), quem entrega segunda
    # de manhã é medido igual a quem entrega quinta à tarde.
    col_lastin = "Última vez que entrou na fase 🚩 Pendência Assessor"
    sub = df.dropna(subset=[col_in, col_out, col_dur]).copy()
    horas = sub.apply(lambda r: horas_uteis_fase(
        r[col_in], r.get(col_lastin), r[col_out], r.get(col_dur)), axis=1)
    ok = int((horas <= _meta_tol(24)).sum())
    ind = score_indicador(ok, len(sub), 10)
    ind["nome"] = "BackOffice — Pendência <24h"

    return {"nota": nota_processo([ind]), "indicadores": [ind]}


def calc_assessora_dirf_darf(df_dirf: pd.DataFrame, assessora: str,
                             ref: Optional[datetime] = None) -> dict:
    """
    Assessora · DIRF/DARF · 1 indicador · peso 10.
    Filtros: Ano: = '2025' + 'Responsável' contém nome.
    11: Concluído antes 29/05/2026 (PRORROGAÇÃO OFICIAL).
    Denominador: TODOS os cards do ano-base da assessora (concluídos ou não).
    """
    df = excluir_rascunhos(df_dirf)
    # Filtro Ano = 2025  (campo number — pode vir como float 2025.0)
    ano_int = pd.to_numeric(df["Ano:"], errors="coerce").astype("Int64")
    df = df[ano_int == DIRF_DARF_ANO_BASE]
    nomes = _nome_assessora_alt(assessora)
    df = df[df["Responsável"].apply(lambda v: _contem_qualquer(v, nomes))].copy()

    col_concl = "Primeira vez que entrou na fase Concluído"
    deadline = pd.Timestamp(DIRF_DARF_CUTOFF).tz_localize("UTC")
    ok = int(((df[col_concl].notna()) & (df[col_concl] < deadline)).sum())
    ind = score_indicador(ok, len(df), 10)
    ind["nome"] = "DIRF/DARF — Concluído antes 29/05"

    return {"nota": nota_processo([ind]), "indicadores": [ind]}


def calc_assessora_whatsapp(df_conv: pd.DataFrame, assessora: str) -> dict:
    """
    Assessora · WhatsApp · 2 indicadores · peso 7.
    Filtro: Responsável da conversa = nome exato (Natália Teixeira / Gardênia).
    """
    if df_conv is None or len(df_conv) == 0:
        return {"nota": None, "indicadores": []}
    nome = NOMES_AGENTE[assessora]["whatsapp"]
    indicadores = _whatsapp_indicadores(df_conv, nome, peso_resposta=6, peso_aval=4)
    return {"nota": nota_processo(indicadores), "indicadores": indicadores}


def calc_assessora_ticket(df_tickets: pd.DataFrame, df_aval: pd.DataFrame, assessora: str) -> dict:
    """
    Assessora · Ticket · 2 indicadores · peso 6.
    Filtro: Responsável do ticket contém nome (Natália / Gardênia).
    Exclusões: Categoria=Cancelado/Spam, Status=Cancelado, Assunto=Tarefa.
    """
    if (df_tickets is None or len(df_tickets) == 0) and (df_aval is None or len(df_aval) == 0):
        return {"nota": None, "indicadores": []}
    nome = NOMES_AGENTE[assessora]["ticket"]
    df_t = _tickets_filtrados(df_tickets, nome)
    ind1 = _ticket_sla_ind(df_t, peso=5)      # 3:3 normalizado p/ somar 10
    ind2 = _ticket_aval_ind(df_aval, nome, peso=5)
    return {"nota": nota_processo([ind1, ind2]), "indicadores": [ind1, ind2]}


# ─────────────────────────────────────────────────────────────────────
# EFICIÊNCIA DA VISTORIA (Marinho) — config + classificador COMPARTILHADOS
# Usados por calculate.py (nota) E imoveis_builder.py (drilldown) para
# garantir simetria total — uma única fonte de verdade (Armadilha 1).
# ─────────────────────────────────────────────────────────────────────
META_LAUDO_CORRIDO = 48.0          # horas corridas (Laudo)
TOL_EFIC = 0.15                    # tolerância da eficiência (15%)
FATOR_OUTLIER_EFIC = 2.0           # > 2x teto -> revisão manual (nunca auto-exclui)
DIR_EFIC_PONTUAVEIS = {"Entrada", "Saída"}  # Conferência/Proprietário excluídos

# Teto em horas ÚTEIS por (balde, direção) — calibrado pela gestora, 12ª Ed.
LOOKUP_EFIC = {
    "Kit/Sala/Loja":     {"Entrada": 4,  "Saída": 2},
    "Apto padrão":       {"Entrada": 8,  "Saída": 4},
    "Apto Super Quadra": {"Entrada": 8,  "Saída": 6},
    "Casa Lago":         {"Entrada": 32, "Saída": 20},
    "Comercial grande":  {"Entrada": 7,  "Saída": 4},
}
# Override persistente IM -> balde (casos confirmados manualmente).
OVERRIDE_IM_BALDE = {"1817": "Casa Lago"}  # COND RESIDENCIAL SANTA MÔNICA


def _primeiro_tipo_vistoria(v):
    """'Saída, Conferência' -> 'Saída'. Limpa e pega o 1º rótulo do multi-select."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    return str(v).split(",")[0].strip()


def classificar_balde_vistoria(endereco, im=None, area=None):
    """Classifica o imóvel no balde da tabela TRK pelo ENDEREÇO (mais confiável
    que o campo 'Tipo do Imóvel'). REVISAR = não classificou -> entra na revisão."""
    e = ("" if endereco is None else str(endereco)).upper()
    if im is not None and not (isinstance(im, float) and pd.isna(im)):
        chave = str(int(im)) if isinstance(im, float) else str(im).strip()
        if chave in OVERRIDE_IM_BALDE:
            return OVERRIDE_IM_BALDE[chave]
    if "SANTA MÔNICA" in e or "SANTA MONICA" in e:
        return "Casa Lago"
    if re.search(r"\b(SQS|SQN|SQSW|SQNW)\b", e):
        return "Apto Super Quadra"
    if re.search(r"(SHIS|\bQI\s*\d|\bQL\s*\d|LAGO)", e):
        return "Casa Lago"
    if re.search(r"(SALA|LOJA|\bKIT\b)", e):
        try:
            if area is not None and not pd.isna(area) and float(area) >= 120:
                return "Comercial grande"
        except (TypeError, ValueError):
            pass
        return "Kit/Sala/Loja"
    if re.search(r"(APARTAMENTO|\bAPTO\b|\bAPT\b|\bAP\b)", e):
        return "Apto padrão"
    return "REVISAR"


def avaliar_eficiencia_vistoria(row):
    """Verdict de UMA vistoria (Series). Retorna dict {direcao, balde, horas, teto,
    ok, outlier} ou None se fora do escopo (Conferência/Proprietário/sem timestamp).
    Função única usada na NOTA e no DRILLDOWN -> simetria garantida."""
    direcao = _primeiro_tipo_vistoria(row.get("Tipo de vistoria"))
    if direcao not in DIR_EFIC_PONTUAVEIS:
        return None
    ci = "vistoria iniciada em" if "vistoria iniciada em" in row.index else "vistoria iniciada em "
    ini, fim = row.get(ci), row.get("Vistoria finalizada em")
    if pd.isna(ini) or pd.isna(fim):
        return None
    balde = classificar_balde_vistoria(
        row.get("Endereço do imóvel:"), row.get("IM"), row.get("Área útil M²"))
    h = horas_uteis(ini, fim)
    if balde == "REVISAR" or balde not in LOOKUP_EFIC:
        return {"direcao": direcao, "balde": "REVISAR", "horas": h,
                "teto": None, "ok": None, "outlier": True}
    teto = LOOKUP_EFIC[balde][direcao]
    ok = h <= teto * (1 + TOL_EFIC)
    outlier = h is not None and h > teto * FATOR_OUTLIER_EFIC
    return {"direcao": direcao, "balde": balde, "horas": h, "teto": teto,
            "ok": ok, "outlier": outlier}


# ─────────────────────────────────────────────────────────────────────
# MARINHO — Vistorias + Contestações
# ─────────────────────────────────────────────────────────────────────

def calc_marinho_vistorias(df_vist: pd.DataFrame, ref: Optional[datetime] = None) -> dict:
    """
    Marinho — Vistorias (2 indicadores quando marinho_eficiencia_ativa):
      • Laudo ≤48h CORRIDAS (peso 4): Vistoria finalizada em → Última saída de
        Em produção. Card parado em Em produção (saída vazia) = ✗ (regra educativa).
      • Eficiência (peso 6): tempo útil iniciada→finalizada vs teto do balde
        (tabela TRK), tolerância 15%. Conferência/Proprietário fora. Outliers
        (>2x teto) são LISTADOS para revisão manual, nunca auto-excluídos.

    Com o flag desligado, mantém o comportamento anterior (Laudo 24h úteis peso 10).
    """
    df = excluir_rascunhos(df_vist)
    df = aplicar_cutoff(df, "Criado em", ref=ref)
    indicadores = []

    col_vfim = "Vistoria finalizada em"
    col_prod_in = "Primeira vez que entrou na fase Em produção"
    col_prod_lastin = "Última vez que entrou na fase Em produção"
    col_prod_out = "Última vez que saiu da fase Em produção"
    col_prod_dur = "Tempo total na fase Em produção (dias)"

    if not FEATURE_FLAGS.get("marinho_eficiencia_ativa", False):
        # ---- comportamento anterior (compat) ----
        produtividade_ativa = FEATURE_FLAGS.get("marinho_produtividade_ativa", False)
        peso_laudo = 4 if produtividade_ativa else 10
        sub_l = df.dropna(subset=[col_vfim, col_prod_out]).copy()
        horas_l = sub_l.apply(lambda r: horas_uteis(r[col_vfim], r[col_prod_out]), axis=1)
        ok_l = int((horas_l <= _meta_tol(24)).sum())
        ind_l = score_indicador(ok_l, len(sub_l), peso_laudo)
        ind_l["nome"] = "Laudos entregues ≤24h após vistoria"
        indicadores.append(ind_l)
        if produtividade_ativa:
            col_vini = "vistoria iniciada em"
            if col_vini not in df.columns:
                col_vini = "vistoria iniciada em "
            sub_p = df.dropna(subset=[col_vini, col_vfim, "Área útil M²"]).copy()
            horas_p = (sub_p[col_vfim] - sub_p[col_vini]).dt.total_seconds() / 3600
            sub_p = sub_p[horas_p > 0].copy()
            m2h = sub_p["Área útil M²"].astype(float) / ((sub_p[col_vfim] - sub_p[col_vini]).dt.total_seconds() / 3600)
            ok_p = int((m2h >= 32).sum())
            ind_p = score_indicador(ok_p, len(sub_p), 6)
            ind_p["nome"] = "Vistorias — Produtividade ≥32 m²/h"
            indicadores.append(ind_p)
        return {"nota": nota_processo(indicadores), "indicadores": indicadores}

    # ---- desenho novo (eficiência ativa) ----
    # LAUDO 48h corridas, parado em produção = ✗, peso 4.
    # Fim do ciclo pela PRIMEIRA saída de "Em produção" (auditoria 05/08/2026):
    # a coluna "Última vez que saiu" é contaminada pela passagem-fantasma do
    # fechamento e marcava 5 laudos entregues no prazo como ✗.
    sub_l = df.dropna(subset=[col_vfim]).copy()  # denominador = vistorias finalizadas
    def _laudo_ok(r):
        saida = primeira_saida_fase(r.get(col_prod_in), r.get(col_prod_lastin),
                                    r.get(col_prod_out), r.get(col_prod_dur))
        if pd.isna(saida):
            return False  # parado em produção -> atraso ✗
        return horas_corridas(r[col_vfim], saida) <= META_LAUDO_CORRIDO
    ok_l = int(sub_l.apply(_laudo_ok, axis=1).sum()) if len(sub_l) else 0
    ind_l = score_indicador(ok_l, len(sub_l), 3)
    ind_l["nome"] = "Laudos entregues ≤48h após vistoria"
    indicadores.append(ind_l)

    # EFICIÊNCIA peso 6.
    verdicts = []
    for _, r in df.iterrows():
        v = avaliar_eficiencia_vistoria(r)
        if v is not None:
            v["im"] = r.get("IM"); v["end"] = r.get("Endereço do imóvel:")
            verdicts.append(v)
    scoraveis = [v for v in verdicts if v["ok"] is not None]
    ok_e = sum(1 for v in scoraveis if v["ok"])
    ind_e = score_indicador(ok_e, len(scoraveis), 5)
    ind_e["nome"] = "Vistorias dentro do tempo padrão"
    indicadores.append(ind_e)

    # 360º peso 2 — esperado em TODA vistoria (decisão da gestora, 14/08/2026).
    # Denominador = cards com o campo preenchido (SIM ou NÃO). O campo virou
    # OBRIGATÓRIO no Pipefy, então quem não preencher não entra — e a partir da
    # obrigatoriedade isso equivale a "todas as vistorias".
    # ⚠️ Enquanto houver cards antigos sem o campo, o denominador fica pequeno
    # (13 de 91 em 14/08) e a nota oscila muito. Reavaliar quando encorpar.
    col_360 = "Vistoria com 360º ?"
    v360 = df.get(col_360, pd.Series(dtype=object)).astype(str).str.strip().str.upper()
    sub_360 = df[v360.isin(["SIM", "NÃO", "NAO"])]
    ok_360 = int((v360.reindex(sub_360.index) == "SIM").sum())
    ind_360 = score_indicador(ok_360, len(sub_360), 2)
    ind_360["nome"] = "Vistorias com 360º"
    indicadores.append(ind_360)

    # ALERTA de revisão manual (outliers + não classificados) na rodada.
    revisar = [v for v in verdicts if v["outlier"] or v["ok"] is None]
    if revisar:
        print("\n⚠️  MARINHO — VISTORIAS PARA REVISÃO MANUAL "
              "(outliers > 2x teto ou não classificadas):")
        for v in sorted(revisar, key=lambda x: (x["horas"] is None, -(x["horas"] or 0))):
            motivo = "não classificada (fora do cálculo)" if v["ok"] is None else "outlier — conta ✗"
            h = "—" if v["horas"] is None else f"{v['horas']:.1f}h"
            print(f"   IM{v.get('im')}  {v['direcao']}  {v['balde']}  {h}  "
                  f"teto={v['teto']}  → {motivo}  | {str(v.get('end'))[:55]}")
        print("   (avalie caso a caso antes de finalizar o painel)\n")

    # PONTO EXTRA — vídeo de drone (decisão da gestora, 14/08/2026).
    # É entrega além do combinado, não obrigação: entra como bônus de CONTAGEM
    # (+0,25 por vídeo, teto +1,5), igual aos bônus do Caio e das assessoras.
    col_drone = "Vistoria com Vídeo de DRONE"
    drone = df.get(col_drone, pd.Series(dtype=object)).astype(str).str.strip().str.upper()
    bonus_drone = int((drone == "SIM").sum())

    return {"nota": nota_processo(indicadores, bonus_n=bonus_drone),
            "indicadores": indicadores, "bonus_n": bonus_drone}


def calc_marinho_contestacoes(df_cont: pd.DataFrame, ref: Optional[datetime] = None) -> dict:
    """
    Marinho · Contestações · 1 indicador · peso 10 · PROCESSO SEPARADO.
    Respondida ≤24h ÚTEIS: Criado em → Primeira vez fase Concluído.
    Denominador: cards que chegaram a Concluído.
    """
    df = excluir_rascunhos(df_cont)
    df = aplicar_cutoff(df, "Criado em", ref=ref)

    col_concl = "Primeira vez que entrou na fase Concluído"
    sub = df.dropna(subset=[col_concl]).copy()
    # HORAS ÚTEIS (decisão da gestora, 12/08/2026): metas curtas em horas
    # corridas empurravam gente a trabalhar fora do expediente por medo do
    # ranking. Medida em horas úteis (08-18h, seg-sex), quem entrega segunda
    # de manhã é medido igual a quem entrega quinta à tarde.
    horas = sub.apply(lambda r: horas_uteis(r["Criado em"], r[col_concl]), axis=1)
    ok = int((horas <= _meta_tol(24)).sum())
    ind = score_indicador(ok, len(sub), 10)
    ind["nome"] = "Contestações respondidas <24h"
    return {"nota": nota_processo([ind]), "indicadores": [ind]}


# ─────────────────────────────────────────────────────────────────────
# ORQUESTRAÇÃO POR COLABORADOR
# ─────────────────────────────────────────────────────────────────────

def calcular_caio(dataframes: dict, bonus_imovel_alugado: int) -> dict:
    """Retorna estrutura completa do Caio para o painel."""
    com_loc = calc_caio_comercial_locacao(dataframes["comercial"], bonus_imovel_alugado)
    cont_loc = calc_caio_contrato_locacao(dataframes["comercial"], dataframes["cont_loc"])
    cont_adm = calc_caio_contrato_adm(dataframes["cont_adm"])
    renov = calc_caio_renovacao(dataframes["renov"])
    wa = calc_caio_whatsapp(dataframes["conversas"])
    tkt = calc_caio_ticket(dataframes["tickets"], dataframes["aval_tickets"])

    scores = {
        "Com. Locação": com_loc["nota"],
        "Cont. Locação": cont_loc["nota"],
        "Cont. ADM": cont_adm["nota"],
        "Renovação": renov["nota"],
        "WhatsApp": wa["nota"],
        "Ticket": tkt["nota"],
    }

    return {
        "id": "caio",
        "nome": "Caio Rodrigues Lima",
        "cargo": "Comercial",
        "nota": nota_final(scores),
        "scores": scores,
        "detalhes": com_loc["indicadores"] + cont_loc["indicadores"] + cont_adm["indicadores"]
                  + renov["indicadores"] + wa["indicadores"] + tkt["indicadores"],
        "bonus_proc": "Com. Locação",
        "bonus": bonus_imovel_alugado,
    }


def calcular_vivianne(dataframes: dict, bonus_boletos: int) -> dict:
    """TODO Claude Code: análogo a calcular_caio para Vivianne."""
    raise NotImplementedError


def calcular_assessora(assessora: str, dataframes: dict, bonus_vistoria: int) -> dict:
    """TODO Claude Code: análogo para Natália/Gardênia."""
    raise NotImplementedError


def calcular_marinho(dataframes: dict) -> dict:
    """TODO Claude Code: estrutura especial — 2 processos, 1 coluna no painel."""
    vist = calc_marinho_vistorias(dataframes["vistorias"])
    cont = calc_marinho_contestacoes(dataframes["contestacoes"])

    nota_marinho = nota_final({"vistorias": vist["nota"], "contestacoes": cont["nota"]})

    return {
        "id": "marinho",
        "nome": "Albérico Marinho",
        "cargo": "Vistoriador",
        "nota": nota_marinho,
        "scores": {"Vistorias": nota_marinho},  # exibição: 1 coluna apenas
        "detalhes": vist["indicadores"] + cont["indicadores"],
    }


# ─────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────

def calcular_ranking(dataframes: dict, bonus: dict) -> list:
    """
    Calcula o ranking completo dos 5 colaboradores.

    Args:
        dataframes: dict com todos os DataFrames extraídos das APIs
        bonus: dict com os valores N de bônus já calculados
            - "caio_imovel_alugado": int
            - "vivianne_boletos": int
            - "natalia_vistoria": int
            - "gardenia_vistoria": int

    Returns:
        Lista de 5 dicts (PESSOAS), ordenada por nota decrescente.
    """
    pessoas = [
        calcular_caio(dataframes, bonus["caio_imovel_alugado"]),
        calcular_vivianne(dataframes, bonus["vivianne_boletos"]),
        calcular_assessora("natalia", dataframes, bonus["natalia_vistoria"]),
        calcular_assessora("gardenia", dataframes, bonus["gardenia_vistoria"]),
        calcular_marinho(dataframes),
    ]
    pessoas.sort(key=lambda p: p["nota"] or 0, reverse=True)
    for pos, p in enumerate(pessoas, 1):
        p["pos"] = pos
    return pessoas


if __name__ == "__main__":
    # Para testes: rodar com dados mock ou cache local
    print("Use run.py para execução completa.")
