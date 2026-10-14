"""
Octadesk pelo `dw_trk` — conversas de WhatsApp (18/08/2026)
==========================================================

Devolve um DataFrame com EXATAMENTE as 3 colunas que `calculate._whatsapp_indicadores`
espera do XLSX (`Total_de_conversas-*.xlsx`), para que nada em calculate.py mude:

    'Responsável da conversa'          ← octadesk_chats.agent_name
    'Tempo de espera após atribuição'  ← agent_first_message_date − assigned_to_agent_date
    'Pesquisa de satisfação'           ← survey_response, traduzido

Mesma filosofia do `extract_dw.py`: o extrator se adapta ao contrato, a regra
não muda. É o que permite rodar as duas fontes em paralelo sem duplicar lógica.

POR QUE ISSO É MELHOR QUE O XLSX
--------------------------------
O XLSX traz a espera já formatada em 'H:MM:SS' e o cálculo precisa parsear a
string de volta. Aqui a espera vem de dois timestamps crus — sem ida e volta de
formatação, e sem depender de a gestora exportar o arquivo a cada edição.
Ainda assim a coluna é devolvida como 'H:MM:SS', para o contrato ficar idêntico.

CONFERÊNCIA CONTRA O PAINEL (18/08/2026, recorte de 180 dias)
-------------------------------------------------------------
    Resposta ≤5min          XLSX          banco
      Natália            1699/2011     1698/2005
      Gardênia           1789/2205     1806/2231
      Caio               1220/2270     1231/2260

    Avaliações positivas    XLSX          banco
      Natália              252/256       254/258
      Gardênia             285/298       286/299
      Caio                 154/158       158/162

Diferença abaixo de 1% em todos — defasagem de recorte, não de regra.

⚠️ TRADUÇÃO DA PESQUISA: o banco guarda o código em inglês e NÃO distingue
"Satisfeito" de "Muito satisfeito" (só tem `satisfied`). Como os dois entram no
numerador do indicador, a nota não muda. Mas se algum dia alguém quiser separar
os dois níveis, o dado não existe aqui.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
_SANDBOX = ROOT / "trk-bd-sandbox"
if str(_SANDBOX) not in sys.path:
    sys.path.insert(0, str(_SANDBOX))

COL_RESP = "Responsável da conversa"
COL_TEMPO = "Tempo de espera após atribuição"
COL_SAT = "Pesquisa de satisfação"
COL_CRIADO = "Criado em"   # data da conversa — usada no corte Natália → Tauise

# survey_response do banco → rótulo do XLSX. `not_sent`/`not_answered` são
# justamente os dois que a regra manda EXCLUIR do denominador (WA_EXC).
TRADUCAO_PESQUISA = {
    "satisfied": "Satisfeito",
    "very_satisfied": "Muito satisfeito",
    "unsatisfied": "Insatisfeito",
    "very_unsatisfied": "Muito insatisfeito",
    "not_answered": "Não respondeu",
    "not_sent": "Não enviado",
}


def _hms(td: pd.Timedelta) -> object:
    """Timedelta → 'H:MM:SS', o formato que `calculate._parse_hms` lê."""
    if pd.isna(td):
        return None
    total = int(td.total_seconds())
    return f"{total // 3600}:{(total % 3600) // 60:02d}:{total % 60:02d}"


def extract_conversas_dw(*, dias: int = 180, verbose: bool = True) -> pd.DataFrame:
    """Conversas de WhatsApp do `dw_trk`, no contrato do XLSX."""
    from db_connection import query as _query  # type: ignore

    df = _query(
        """
        SELECT agent_name, assigned_to_agent_date, agent_first_message_date,
               survey_response, created_at
        FROM octadesk_chats
        WHERE created_at >= now() - make_interval(days => %s)
        """,
        (dias,),
    )
    if verbose:
        print(f"  [octadesk-dw] octadesk_chats: {len(df)} conversas nos últimos {dias}d")

    ini = pd.to_datetime(df["assigned_to_agent_date"], errors="coerce", utc=True)
    fim = pd.to_datetime(df["agent_first_message_date"], errors="coerce", utc=True)
    espera = fim - ini

    # ESPERA NEGATIVA — DECISÃO DA GESTORA, 20/08/2026: fica NEUTRO.
    # A primeira mensagem do agente veio ANTES da atribuição: ele pegou uma
    # conversa que ainda não era dele, atendeu, e só depois o sistema registrou
    # a atribuição (transferência ou atribuição manual tardia).
    # Medido nos 180 dias: Gardênia 29 casos (1h57 antes, em média), Caio 16
    # (2h07), Natália 14 (1h04) — não é corrida de milissegundos, é fluxo real.
    # Nesses casos NÃO EXISTE "espera após a atribuição" para medir: o relógio
    # começou depois de a pessoa já estar atendendo.
    #   • fora do denominador (EM VIGOR) → não conta a favor nem contra
    #   • contar ✓ → trataria como resposta instantânea; +1pp para a Gardênia
    #   • contar ✗ → puniria quem atendeu antes da hora; descartado
    # A gestora escolheu o neutro: é o único que não inventa um número.
    # ⚠️ Não confundir com os timestamps invertidos das vistorias, que são ERRO
    # de digitação (ver FUSO_campos_manuais_18-08-2026.md). Aqui o dado está
    # certo — o que não existe é a medida.
    negativos = int((espera < pd.Timedelta(0)).sum())
    espera = espera.mask(espera < pd.Timedelta(0))
    if verbose and negativos:
        print(f"  [octadesk-dw] {negativos} conversa(s) com espera negativa "
              f"(1ª mensagem antes da atribuição) — fora do denominador")

    out = pd.DataFrame({
        COL_RESP: df["agent_name"],
        COL_TEMPO: espera.map(_hms),
        COL_SAT: df["survey_response"].map(
            lambda v: TRADUCAO_PESQUISA.get(str(v).strip().lower(), v)),
        COL_CRIADO: pd.to_datetime(df["created_at"], errors="coerce", utc=True),
    })
    if verbose:
        validos = out[COL_TEMPO].notna().sum()
        print(f"  [octadesk-dw] {validos} com tempo de espera válido")
    return out


# ═════════════════════════════════════════════════════════════════════
# TICKETS pelo `dw_trk` (13/10/2026)
# ═════════════════════════════════════════════════════════════════════
# Contrato do XLSX `Tickets totais-*.xlsx` que `calculate._tickets_filtrados`
# e `_ticket_sla_ind` usam:
#   'Número do ticket'                ← octadesk_tickets.number
#   'Data de entrada'                 ← created_at (horário de Brasília, sem fuso, como no XLSX)
#   'Data da primeira resposta'       ← 1ª interação de quem NÃO é o solicitante com texto
#                                       ou com mudança de status (como o Octadesk calcula)
#   'Responsável do ticket'           ← assigned_name
#   'Status do ticket'                ← status_name
#   'Categoria de assunto do ticket'  ← último topicGroupName no histórico do ticket
#   'Assunto do ticket'               ← último topicName no histórico do ticket
#
# A coluna octadesk_tickets.categoria_assunto chega vazia, mas a categoria e o
# assunto ESTÃO no banco: cada mudança fica em octadesk_tickets_interacoes.
# properties_changes (topicGroupName / topicName). Assim as 3 exclusões do
# manual (Cancelado/Spam, status Cancelado, assunto Tarefa) valem iguais ao XLSX.
#
# CONFERÊNCIA (13/10/2026, mesmo período do XLSX de 29/09 — 21/03 a 26/09):
#   primeira resposta igual ao XLSX (±2 min) em 99,1% dos tickets válidos;
#   categoria e assunto iguais em 97%.
#   SLA <4h úteis   XLSX          banco
#     Vivianne      302/446       290/432
#     Natália       233/314       238/314
#     Gardênia      148/257       151/258
#     Tauise          9/41         12/41
#     Caio          981/2672      946/2587
# As AVALIAÇÕES de ticket não estão no banco: continuam no XLSX de avaliações.
COL_TKT_NUM = "Número do ticket"
COL_TKT_IN = "Data de entrada"
COL_TKT_RESP_T = "Data da primeira resposta"
COL_TKT_RESP = "Responsável do ticket"
COL_TKT_STATUS = "Status do ticket"
COL_TKT_CAT = "Categoria de assunto do ticket"
COL_TKT_ASSUNTO = "Assunto do ticket"


def extract_tickets_dw(*, dias: int = 180, verbose: bool = True) -> pd.DataFrame:
    """Tickets do Octadesk pelo `dw_trk`, no contrato do XLSX."""
    from db_connection import query as _query  # type: ignore

    df = _query(
        """
        SELECT t.number,
               (t.created_at AT TIME ZONE 'America/Sao_Paulo') AS entrada,
               (SELECT min(i.created_at) AT TIME ZONE 'America/Sao_Paulo'
                  FROM octadesk_tickets_interacoes i
                 WHERE i.ticket_number = t.number
                   AND COALESCE(i.author_email, '') <> COALESCE(t.requester_email, '')
                   AND (NULLIF(btrim(regexp_replace(COALESCE(i.content, ''), '<[^>]+>', '', 'g')), '') IS NOT NULL
                        OR i.properties_changes::text LIKE '%%"status"%%')) AS primeira_resposta,
               t.assigned_name, t.status_name,
               (SELECT i.properties_changes->>'topicGroupName' FROM octadesk_tickets_interacoes i
                 WHERE i.ticket_number = t.number AND i.properties_changes::text LIKE '%%topicGroupName%%'
                 ORDER BY i.created_at DESC LIMIT 1) AS categoria,
               (SELECT i.properties_changes->>'topicName' FROM octadesk_tickets_interacoes i
                 WHERE i.ticket_number = t.number AND i.properties_changes::text LIKE '%%"topicName"%%'
                 ORDER BY i.created_at DESC LIMIT 1) AS assunto
        FROM octadesk_tickets t
        WHERE t.created_at >= now() - make_interval(days => %s)
        """,
        (dias,),
    )
    out = pd.DataFrame({
        COL_TKT_NUM: df["number"],
        COL_TKT_IN: pd.to_datetime(df["entrada"], errors="coerce"),
        COL_TKT_RESP_T: pd.to_datetime(df["primeira_resposta"], errors="coerce"),
        COL_TKT_RESP: df["assigned_name"],
        COL_TKT_STATUS: df["status_name"],
        COL_TKT_CAT: df["categoria"],
        COL_TKT_ASSUNTO: df["assunto"],
    })
    if verbose:
        print(f"  [octadesk-dw] octadesk_tickets: {len(out)} tickets nos últimos {dias}d · "
              f"{int(out[COL_TKT_RESP_T].notna().sum())} com primeira resposta · "
              f"{int(out[COL_TKT_CAT].notna().sum())} com categoria")
    return out
