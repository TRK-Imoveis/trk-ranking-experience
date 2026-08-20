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
    })
    if verbose:
        validos = out[COL_TEMPO].notna().sum()
        print(f"  [octadesk-dw] {validos} com tempo de espera válido")
    return out
