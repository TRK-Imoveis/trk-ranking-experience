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
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
from typing import Optional


# ─────────────────────────────────────────────────────────────────────
# CONFIGURAÇÃO
# ─────────────────────────────────────────────────────────────────────

CONFIG_DIR = Path(__file__).parent.parent / "config"
FEATURE_FLAGS = json.loads((CONFIG_DIR / "feature_flags.json").read_text())

CUTOFF_DIAS = 180
CUTOFF_CONT_ADM_CAIO_FIXO = datetime(2026, 3, 1)
DIRF_DARF_CUTOFF = datetime(2026, 5, 29)  # prorrogação oficial 2026
DIRF_DARF_ANO_BASE = 2025

NOMES_AGENTE = {
    "caio":      {"whatsapp": "Caio Rodrigues",   "ticket": "Caio Rodrigues"},
    "natalia":   {"whatsapp": "Natália Teixeira", "ticket": "Natália Teixeira"},
    "gardenia":  {"whatsapp": "Gardênia",         "ticket": "Gardênia"},
    "vivianne":  {"whatsapp": None,               "ticket": ["Vivianne Fontes", "VIVIANNE FONTES"]},  # WhatsApp EXCLUÍDO
}


# ─────────────────────────────────────────────────────────────────────
# HELPERS GERAIS
# ─────────────────────────────────────────────────────────────────────

def cutoff(dias: int = CUTOFF_DIAS) -> datetime:
    """Retorna a data limite (hoje - dias). Sempre relativa ao momento da execução."""
    return datetime.now() - timedelta(days=dias)


def excluir_rascunhos(df: pd.DataFrame) -> pd.DataFrame:
    """Remove cards onde Título, Imóvel ou Endereço contenham 'rascunho'."""
    cols_texto = [c for c in ["Título", "Imóvel", "Endereço"] if c in df.columns]
    if not cols_texto:
        return df
    mask = pd.Series([False] * len(df), index=df.index)
    for col in cols_texto:
        mask |= df[col].astype(str).str.contains("rascunho", case=False, na=False)
    return df[~mask].copy()


def horas_uteis(inicio: pd.Timestamp, fim: pd.Timestamp) -> float:
    """
    Calcula horas úteis (08-18 seg-sex) entre inicio e fim.

    Regras:
    - Se fim < inicio (negativo): retorna 0.0 (= cumprido ✓)
    - Sábado e domingo: 0 horas
    - Fora do horário comercial: descontar
    """
    if pd.isna(inicio) or pd.isna(fim):
        return float("nan")
    if fim < inicio:
        return 0.0

    # TODO Claude Code: implementar cálculo exato de horas úteis
    # Cuidado: precisa lidar com fim de semana, intervalo entre dias,
    # cruzar horários 08-18 corretamente.
    # Sugestão: iterar por dia útil entre inicio e fim, somar minutos
    # dentro de 08:00-18:00.
    raise NotImplementedError("Implementar horas_uteis com testes unitários")


def dias_uteis(inicio: pd.Timestamp, fim: pd.Timestamp) -> float:
    """Wrapper: horas úteis ÷ 10."""
    return horas_uteis(inicio, fim) / 10.0


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


def nota_processo(indicadores: list, bonus_n: int = 0) -> Optional[float]:
    """
    Calcula nota do processo (0-10).

    Fórmula base:    sum(scores) / sum(pesos) * 10
    Fórmula bônus:   (sum(scores) + bonus_n) / (sum(pesos) + bonus_n) * 10

    Indicadores sem dados (tot=0) são excluídos.
    Se todos sem dados, retorna None.
    """
    validos = [i for i in indicadores if i["tot"] > 0]
    if not validos:
        return None
    soma_scores = sum(i["score"] for i in validos)
    soma_pesos = sum(i["peso"] for i in validos)
    return round((soma_scores + bonus_n) / (soma_pesos + bonus_n) * 10, 3)


def nota_final(scores_processos: dict) -> Optional[float]:
    """Média simples das notas de processo não-nulas."""
    validas = [v for v in scores_processos.values() if v is not None]
    if not validas:
        return None
    return round(sum(validas) / len(validas), 2)


# ─────────────────────────────────────────────────────────────────────
# CAIO — COMERCIAL
# ─────────────────────────────────────────────────────────────────────

def calc_caio_comercial_locacao(df_comercial: pd.DataFrame, bonus_n: int = 0) -> dict:
    """
    Caio · Comercial Locação · 3 indicadores · peso 10 · bônus aplicado aqui.

    Indicador 1: Início <24h (peso 2.5) — Criado em → Avaliação Técnica, corrido
    Indicador 2: Anúncio <72h (peso 2.5) — Saída Aval.Téc → Publicação, corrido, fallback NIDO
    Indicador 3: Coluna correta (peso 5) — fase atual vs intervalo desocupação

    Bônus: imóvel alugado antes de anunciado (validação manual obrigatória — ver manual §4.1)
    """
    # TODO Claude Code: implementar
    # Filtrar: cutoff 180d em "Criado em", Profissional responsável contém "Caio", excluir rascunhos
    # Indicador 1: contar cards onde (Primeira vez fase Avaliação Técnica - Criado em) ≤ 24h corridas
    # Indicador 2: para cada card que saiu de Aval.Téc OU foi publicado, calcular tempo até publicação
    # Indicador 3: para cada card que passou por Conferência Final e não está em Concluído,
    #             verificar se fase atual corresponde ao intervalo de dias desocupado
    raise NotImplementedError


def calc_caio_contrato_locacao(df_comercial: pd.DataFrame, df_cont_loc: pd.DataFrame) -> dict:
    """
    Caio · Cont. Locação · 2 indicadores · peso 10.

    Indicador 1: Ocupação <30d (peso 6) — CRUZAMENTO 2 PIPES via IM
    Indicador 2: Documentação <24h úteis (peso 4) — Criado em → Entrada Confecção

    Atenção: pareamento múltiplos anúncios/boletos. Caso "alugado antes de re-anunciar"
    (anúncio posterior ao boleto) → EXCLUIR do denominador.
    """
    raise NotImplementedError


def calc_caio_contrato_adm(df_cont_adm: pd.DataFrame) -> dict:
    """
    Caio · Cont. ADM · 1 indicador · peso 10.

    Indicador: Criação→Contrato assinado-Conferir NIDO <7d corrido.
    CUTOFF FIXO: 01/03/2026 (NÃO 180d).
    """
    raise NotImplementedError


def calc_caio_renovacao(df_renov: pd.DataFrame) -> dict:
    """
    Caio · Renovação · 1 indicador EXCLUSIVO · peso 10.

    Indicador: Avaliação >90d antes vencimento — Data venc - Última saída Avaliação de mercado.
    """
    raise NotImplementedError


def calc_caio_whatsapp(df_conv: pd.DataFrame) -> dict:
    """
    Caio · WhatsApp · 2 indicadores · peso 7.
    Filtro: Responsável da conversa = "Caio Rodrigues"

    Indicador 1: Resposta ≤5min (peso 4) — coluna "Tempo de espera após atribuição"
    Indicador 2: Avaliações positivas (peso 3) — "Pesquisa de satisfação", exclui Não respondeu/Não enviado
    """
    raise NotImplementedError


def calc_caio_ticket(df_tickets: pd.DataFrame, df_aval: pd.DataFrame) -> dict:
    """
    Caio · Ticket · 2 indicadores · peso 7.
    Filtro: Responsável do ticket contém "Caio"
    Exclusões: Categoria=Cancelado/Spam, Status=Cancelado, Assunto=Tarefa

    Indicador 1: SLA ≤4h úteis (peso 4)
    Indicador 2: Avaliações positivas (peso 3) — "Bom" + "Bom com comentário"
    """
    raise NotImplementedError


# ─────────────────────────────────────────────────────────────────────
# VIVIANNE — BackOffice + Inadimplência
# ─────────────────────────────────────────────────────────────────────

def calc_vivianne_contrato_adm(df_cont_adm: pd.DataFrame) -> dict:
    """
    Vivianne · Cont. ADM · 1 indicador · peso 10.
    Indicador: Confecção <2h úteis — entrada/saída fase Confecção do contrato.
    Usa TODOS os cards (sem filtro de assessor).
    """
    raise NotImplementedError


def calc_vivianne_rescisao_adm(df_resc_adm: pd.DataFrame) -> dict:
    """
    Vivianne · Rescisão ADM · 1 indicador · peso 10.
    Indicador: Encerramento <4h corrido — entrada/saída fase Encerramento.

    ATENÇÃO: este é da Vivianne. "Repasse <12h" é das ASSESSORAS, não dela.
    """
    raise NotImplementedError


def calc_vivianne_contrato_locacao(df_cont_loc: pd.DataFrame) -> dict:
    """
    Vivianne · Cont. Locação · 2 indicadores · peso 10.

    Indicador 1: NIDO→Concluído <24h corrido (peso 5)
    Indicador 2: Confecção <2h (peso 5) — usa coluna Pipefy "Tempo total na fase Confecção (dias)" × 24
    """
    raise NotImplementedError


def calc_vivianne_rescisao_locacao(df_resc_loc: pd.DataFrame) -> dict:
    """
    Vivianne · Rescisão Loc. · 2 indicadores BackOffice · peso 10.

    Indicador 1: Levant. Taxas Prop <2h (peso 5) — coluna Pipefy
    Indicador 2: Levant. Taxas Final <2h (peso 5) — coluna Pipefy

    Vivianne NÃO tem indicadores de finalização (são das assessoras).
    """
    raise NotImplementedError


def calc_vivianne_renovacao(df_renov: pd.DataFrame) -> dict:
    """
    Vivianne · Renovação · 2 indicadores · peso 10.

    Indicador 1: Confecção <4h (peso 5) — coluna Pipefy "Tempo total na fase Confecção"
    Indicador 2: Finalização <16h úteis (peso 5)
    """
    raise NotImplementedError


def calc_vivianne_inadimplencia(df_inad: pd.DataFrame, bonus_n: int = 0) -> dict:
    """
    Vivianne · Inadimplência · 3 indicadores + bônus · peso base 4.

    Indicador 1: Cobrança <24h corrido (peso 2)
    Indicador 2: CredPago ≤15d (peso 1) — usa "Vencimento 1º Boleto:" como início (NÃO Criado em)
    Indicador 3: Negativação 7-9d (peso 1) — mesma regra de início

    Bônus: boletos em atraso recebidos antes do repasse (N — cruzamento 4 fontes).
    """
    raise NotImplementedError


def calc_vivianne_backoffice(df_bo: pd.DataFrame) -> dict:
    """
    Vivianne · BackOffice · 2 indicadores · peso 10.

    Separar cards por "Primeira vez fase ↪️ Troca de Titularidade":
    - SEM troca → Indicador 1: Concluído <24h corrido (peso 5)
    - COM troca → Indicador 2: Troca <5d úteis = 50h úteis (peso 5)
    """
    raise NotImplementedError


def calc_vivianne_ticket(df_tickets: pd.DataFrame) -> dict:
    """
    Vivianne · Ticket · 1 indicador · peso 4.
    Filtro: Responsável contém "Vivianne Fontes" ou "VIVIANNE FONTES"
    Indicador: SLA ≤4h úteis (peso 4).
    Avaliações EXCLUÍDAS (0 registros — não entra no cálculo).
    """
    raise NotImplementedError


# ─────────────────────────────────────────────────────────────────────
# NATÁLIA / GARDÊNIA — Assessoras (helpers reaproveitáveis)
# ─────────────────────────────────────────────────────────────────────

def calc_assessora_contrato_adm(df_cont_adm: pd.DataFrame, assessora: str, bonus_n: int = 0) -> dict:
    """
    Assessora · Cont. ADM · 1 indicador · peso 10 + bônus vistoria.

    Indicador: Conferência ≤2h úteis — entrada/saída fase Conferência do contrato.
    Bônus: N = cards onde "Criar Card de Vistoria Técnica" está preenchido, filtrado por Assessor (lista).

    Cards sem Assessor (lista) mas concluídos → TODOS são da Gardênia (validado).
    """
    raise NotImplementedError


def calc_assessora_rescisao_adm(df_resc_adm: pd.DataFrame, assessora: str) -> dict:
    """
    Assessora · Rescisão ADM · 2 indicadores · peso 10.

    Indicador 1: Repasse <12h úteis (peso 5) — Criado em → fase Repasse final/Distrato
    Indicador 2: Distrato assinado (peso 5) — campo preenchido em cards concluídos
    """
    raise NotImplementedError


def calc_assessora_rescisao_locacao(df_resc_loc: pd.DataFrame, assessora: str) -> dict:
    """
    Assessora · Rescisão Loc. · 2 indicadores · peso 5.

    Indicador 1: Boleto prop <24h corrido (peso 2)
        Início: "Data do recebimento das chaves:" OU fallback "Última saída Vistoria recebida"
        Fim: "Primeira vez fase Levant. Taxas Proporcionais"
    Indicador 2: Boleto final <15d corrido (peso 3)
        Início: chaves OU fallback "Última saída Agendamento de vistoria"
        Fim: "Primeira vez fase Envio do boleto final"

    NÃO usar Criado em (mistura tempo de aguardando chaves). Negativos → 0 (✓).
    """
    raise NotImplementedError


def calc_assessora_reparos(df_rep: pd.DataFrame, assessora: str) -> dict:
    """
    Assessora · Reparos · 2 indicadores · peso 10.
    Filtro: "Selecionar o assessor" contém nome.

    Indicador 1: Orçamento <4h úteis (peso 4) — Criado em → fase Orçamento|Prestador
    Indicador 2: Pós-venda ≤7d corrido (peso 6) — Criado em → fase Pós-venda
    """
    raise NotImplementedError


def calc_assessora_renovacao(df_renov: pd.DataFrame, assessora: str) -> dict:
    """
    Assessora · Renovação · 2 indicadores · peso 10.
    Filtro: "Assessor (lista)" = nome.

    Indicador 1: Contato >60d antes vencimento (peso 4) — Data venc - última saída Contato com proprietário
    Indicador 2: Assinado antes vencimento (peso 6) — Primeira vez fase Contrato assinado/Finalizar < Data venc
    """
    raise NotImplementedError


def calc_assessora_backoffice(df_bo: pd.DataFrame, assessora: str) -> dict:
    """
    Assessora · BackOffice · 1 indicador · peso 10.
    Filtro: "Responsáveis" contém nome (NÃO "Criador").
    Indicador: Pendência Assessor <24h corrido.
    """
    raise NotImplementedError


def calc_assessora_dirf_darf(df_dirf: pd.DataFrame, assessora: str) -> dict:
    """
    Assessora · DIRF/DARF · 1 indicador · peso 10.
    Filtros: "Ano:" = 2025 + "Responsáveis" contém nome.
    Indicador: Concluído < 29/05/2026 (PRORROGAÇÃO OFICIAL — não usar 01/05).
    Denominador: TODOS os cards do ano-base da assessora (concluídos ou não).
    """
    raise NotImplementedError


def calc_assessora_whatsapp(df_conv: pd.DataFrame, assessora: str) -> dict:
    """
    Assessora · WhatsApp · 2 indicadores · peso 7.
    Filtro: Responsável da conversa = nome exato.
    """
    raise NotImplementedError


def calc_assessora_ticket(df_tickets: pd.DataFrame, df_aval: pd.DataFrame, assessora: str) -> dict:
    """
    Assessora · Ticket · 2 indicadores · peso 6.
    Filtro: Responsável do ticket contém nome.
    """
    raise NotImplementedError


# ─────────────────────────────────────────────────────────────────────
# MARINHO — Vistorias + Contestações
# ─────────────────────────────────────────────────────────────────────

def calc_marinho_vistorias(df_vist: pd.DataFrame) -> dict:
    """
    Marinho · Vistorias · 2 ou 3 indicadores conforme feature flag.

    Indicador 1: Laudo <24h úteis
        - Início: "Vistoria finalizada em" (NÃO "Data da Vistoria")
        - Fim: "Última saída fase Em produção"
        - Negativos → 0 (✓)
        - Peso: 4 se Produtividade ativa, 10 se Produtividade desativada (10ª Ed)

    Indicador 2 (CONDICIONAL — feature flag): Produtividade ≥32 m²/h
        - Fórmula: Área útil M² ÷ horas corridas entre vistoria iniciada/finalizada
        - Horas CORRIDAS (não úteis)
        - Excluir cards com horas_vist ≤ 0
        - Incluir vistorias de conferência de reparo
        - Peso: 6 (quando ativa)

    Indicador 3: Contestações <24h corrido — PROCESSO SEPARADO
        - Mas exibe consolidado no painel "Vistorias" (Marinho tem 1 só coluna)
        - Peso 10
    """
    indicadores = []
    produtividade_ativa = FEATURE_FLAGS.get("marinho_produtividade_ativa", False)

    # Indicador Laudo
    peso_laudo = 4 if produtividade_ativa else 10
    # TODO Claude Code: cálculo do Laudo
    # ind_laudo = score_indicador(ok=..., tot=..., peso=peso_laudo)
    # ind_laudo["nome"] = "Laudos entregues ≤24h após vistoria"
    # indicadores.append(ind_laudo)

    # Indicador Produtividade (condicional)
    if produtividade_ativa:
        # TODO: cálculo da Produtividade m²/h
        pass

    raise NotImplementedError


def calc_marinho_contestacoes(df_cont: pd.DataFrame) -> dict:
    """
    Marinho · Contestações · 1 indicador · peso 10 · PROCESSO SEPARADO.

    Indicador: Respondida <24h corrido — Criado em → Primeira vez Concluído.
    Denominador: cards que chegaram a Concluído.

    OBS: este processo gera nota independente. Nota final Marinho = média entre
    nota Vistorias e nota Contestações. No painel, ambas aparecem consolidadas
    sob a coluna "Vistorias" (Marinho tem 1 só coluna na tabela do ranking).
    """
    raise NotImplementedError


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
