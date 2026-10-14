"""
Inadimplência pelo `dw_trk` — substitui os 3 CSVs do Imobiliar (20/08/2026)
==========================================================================

Devolve o MESMO dict {"boletos", "proprietarios", "imoveis"} que
`extract_imobiliar()` monta a partir das CSVs, com as MESMAS colunas — para
`calcular_bonus_inadimplencia` rodar sem uma linha de mudança.

    boletos       cd_imovel · mes_ref · data_pag · valor · multa_adm · juros_adm
    imoveis       cd_imovel · id_proprietario · endereco
    proprietarios id_proprietario · dia_pag · nome

DE ONDE VEM CADA COISA
----------------------
    cd_imovel   imobiliar_boletos_encargo_adm.codigo_imovel   ('1783.0' → 1783)
    mes_ref     .competencia                                   ('2026-03' → '03/2026')
    data_pag    .data_pagamento
    multa_adm   .valor_multa_adm
    juros_adm   .valor_juros_adm
    valor       imobiliar_doc_capa.valor_documento − multa do acordo
    dia_pag     .dia_pagamento_proprietario         ← ver nota abaixo
    endereco    imobiliar_imoveis
    nome        imobiliar_proprietarios_imoveis.nome_proprietario

⚠️ O `valor` NÃO está em `boletos_encargo_adm` — está em `imobiliar_doc_capa`.
   Em 20/08/2026 eu afirmei que não existia no banco e cheguei a redigir um
   pedido de coluna nova ao Eduardo; a gestora insistiu e o campo apareceu.
   Cobertura do join medida no mesmo dia: 92 de 92 boletos, nenhum nulo ou zero.

⚠️ POR QUE `dia_pag` VEM DO BOLETO, E NÃO DA TABELA DE PROPRIETÁRIOS
   O caminho da CSV é imóvel → proprietário → dia_pag. No banco isso é ambíguo:
   `imobiliar_proprietarios_imoveis` pode ter VÁRIOS proprietários por imóvel
   (percentual_renda), e a CSV traz um só. A tabela de boletos já carrega
   `dia_pagamento_proprietario` — o dia que o próprio Imobiliar amarrou àquele
   boleto. É mais direto e não precisa escolher entre sócios.
   Para manter o contrato, sintetizamos um "proprietário" por imóvel carregando
   esse dia. Onde há mais de um dia_pag para o mesmo imóvel (troca de titular
   no meio do período), fica o do boleto mais recente — e o caso é avisado.

⚠️ REGRA R1 (multa >15% = rescisão) — situação em 13/10/2026
   Com a regra nova do acordo (ver comentário da consulta), banco e relatório
   batem em 136 de 136 boletos (27/02 a 26/08). Na R1 sobra 1 diferença:
   IM1783 04/2026 passa de 15% no relatório (17,5%) e não no banco (11,6%),
   porque a "correção acordo encargos" (taxa 326) só existe nos itens do boleto.
   Desde 13/10/2026 este extrator é a fonte de PRODUÇÃO da Inadimplência
   (flag `imobiliar_do_banco`); os CSVs ficam só como reserva se o banco falhar.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
_SANDBOX = ROOT / "trk-bd-sandbox"
if str(_SANDBOX) not in sys.path:
    sys.path.insert(0, str(_SANDBOX))


def _cd(v) -> object:
    """'1783.0' / 1783.0 / ' 1783 ' → '1783' (STRING, como a CSV entrega).

    ⚠️ Tem que ser string. O `_norm_cd` do cálculo faz int(str(v).strip()...),
    que estoura em '1783.0' e devolve None — e o boleto sairia do denominador
    EM SILÊNCIO. Se a coluna virasse float64 (basta um NaN no meio), todo
    código viraria '1783.0' e a Inadimplência inteira zeraria sem erro nenhum.
    """
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    try:
        return str(int(float(str(v).strip())))
    except (TypeError, ValueError):
        return None


def _mes_ref(v) -> object:
    """competencia '2026-03' → mes_ref '03/2026' (formato das CSVs)."""
    s = "" if v is None else str(v).strip()
    if len(s) >= 7 and s[4] == "-":
        return f"{s[5:7]}/{s[:4]}"
    return None


def extract_imobiliar_dw(*, verbose: bool = True) -> dict[str, pd.DataFrame]:
    from db_connection import query as _query  # type: ignore

    # ENCARGO VEM DE DOIS LUGARES (28/08/2026 · regra revista em 13/10/2026)
    # ─────────────────────────────────────────────────────────────────
    # 1) No próprio boleto: valor_multa_adm / valor_juros_adm.
    # 2) Num ACORDO: quando o inquilino atrasa e faz acordo, o Imobiliar põe a
    #    multa no acordo e cobra num boleto reemitido (tipo 'E'). Esse boleto
    #    pode ter OUTRA competência (ex.: IM382, acordo dos docs de 01/2026,
    #    cobrado no boleto de 03/2026 pago em 01/04).
    #
    # Ligação acordo → boleto pago: mesmo imóvel e vencimento do boleto = vencimento
    # da parcela do acordo; se nenhum boleto vence nesse dia, o primeiro pago até
    # 45 dias depois (acordo refeito). Acordo parcelado: multa dividida pelas parcelas.
    # Parcelamentos antigos (parcela vencendo mais de 90 dias depois do acordo)
    # NÃO contam: é dívida velha sendo paga, não cobrança do mês (IM876).
    # A multa do boleto e a do acordo SOMAM (IM368 07/2026: 283,41 + 613,15).
    # `valor` = valor do boleto sem a multa do acordo, como no relatório do Imobiliar.
    #
    # Unidade = boleto pago (não mais imóvel × competência): um imóvel pode pagar
    # dois boletos da mesma competência (IM1758 05/2026, 01/07 e 08/07).
    #
    # Conferido em 13/10/2026 contra o "Relatório de Boletos Quitados" de 27/08
    # (27/02 a 26/08): 136 de 136 boletos iguais; multa igual em 134. Nos outros 2
    # (IM1783 04/2026 e IM408 08/2026) falta a "correção acordo encargos" (taxa 326),
    # que só existe nos itens do boleto, e eles não vêm para o dw_trk.
    b = _query(
        """
        WITH pago AS (
            SELECT c.id_documento, g.codigo_imovel::int AS im, c.competencia,
                   c.data_vencimento::date AS venc, c.data_pagamento::date AS dp,
                   c.valor_documento AS v,
                   COALESCE(c.valor_multa_adm, 0) AS m, COALESCE(c.valor_juros_adm, 0) AS j
            FROM imobiliar_doc_capa c
            JOIN imobiliar_grupo_pag g
              ON g.codigo_grupo = c.codigo_grupo AND g.sequencia_grupo = c.sequencia_grupo_titular
            WHERE c.data_pagamento >= CURRENT_DATE - 400 AND c.cancelado IS NOT TRUE
        ),
        aim AS (
            SELECT DISTINCT da.id_acordo, g.codigo_imovel::int AS im
            FROM imobiliar_docs_acordados da
            JOIN imobiliar_doc_capa c ON c.id_documento = da.id_documento
            JOIN imobiliar_grupo_pag g
              ON g.codigo_grupo = c.codigo_grupo AND g.sequencia_grupo = c.sequencia_grupo_titular
        ),
        parc AS (
            SELECT id_acordo, venc, COUNT(*) OVER (PARTITION BY id_acordo) AS n
            FROM (SELECT DISTINCT id_acordo, data_vencimento::date AS venc
                  FROM imobiliar_acordos_parcelas) x
        ),
        ap AS (
            SELECT aim.im, a.id_acordo, pa.venc, a.valor_multa / pa.n AS multa
            FROM imobiliar_acordos a
            JOIN parc pa USING (id_acordo)
            JOIN aim USING (id_acordo)
            WHERE COALESCE(a.valor_multa, 0) > 0
              AND pa.venc - a.data_geracao::date <= 90
        ),
        casa AS (
            SELECT DISTINCT ON (ap.im, ap.id_acordo, ap.venc) ap.multa, p.id_documento
            FROM ap
            JOIN pago p ON p.im = ap.im
                       AND (p.venc = ap.venc OR p.dp BETWEEN ap.venc AND ap.venc + 45)
            ORDER BY ap.im, ap.id_acordo, ap.venc, (p.venc = ap.venc) DESC, p.competencia, p.dp
        ),
        doc AS (
            SELECT p.*, COALESCE(s.ma, 0) AS ma
            FROM pago p
            LEFT JOIN (SELECT id_documento, SUM(multa) AS ma FROM casa GROUP BY 1) s USING (id_documento)
        ),
        -- dia do repasse: o do boleto com encargo; se o imóvel não tem nenhum
        -- (só acordo), o do contrato de locação mais recente. Sem esse reserva,
        -- 26 imóveis com encargo caíam do cálculo em silêncio (medido 13/10/2026).
        dia_bol AS (
            SELECT codigo_imovel::int AS im, MAX(dia_pagamento_proprietario) AS dia_pag
            FROM imobiliar_boletos_encargo_adm
            WHERE dia_pagamento_proprietario IS NOT NULL
            GROUP BY 1
        ),
        dia_con AS (
            SELECT codigo_imovel::int AS im,
                   (ARRAY_AGG(dia_pagamento_proprietario ORDER BY codigo_contrato DESC))[1] AS dia_pag
            FROM imobiliar_contratos_loc
            WHERE dia_pagamento_proprietario IS NOT NULL
            GROUP BY 1
        ),
        dia_prop AS (
            SELECT COALESCE(b.im, c.im) AS im, COALESCE(b.dia_pag, c.dia_pag) AS dia_pag
            FROM dia_bol b FULL JOIN dia_con c ON c.im = b.im
        )
        SELECT d.im AS codigo_imovel, d.competencia, d.dp AS data_pagamento,
               d.v - d.ma AS valor_documento, d.m AS multa_doc, d.j AS juros_doc,
               d.ma AS multa_acordo, dp.dia_pag AS dia_pagamento_proprietario
        FROM doc d
        LEFT JOIN dia_prop dp ON dp.im = d.im
        """
    )

    multa_doc = pd.to_numeric(b["multa_doc"], errors="coerce").fillna(0.0)
    multa_aco = pd.to_numeric(b["multa_acordo"], errors="coerce").fillna(0.0)
    multa = multa_doc + multa_aco

    if verbose:
        n_doc = int(((multa_doc > 0) & (multa_aco == 0)).sum())
        n_aco = int(((multa_doc == 0) & (multa_aco > 0)).sum())
        ambos = int(((multa_doc > 0) & (multa_aco > 0)).sum())
        print(f"  [imobiliar-dw] encargo no boleto: {n_doc} · no acordo: {n_aco} "
              f"· nos dois: {ambos}")

    boletos = pd.DataFrame({
        "cd_imovel": b["codigo_imovel"].map(_cd),
        "mes_ref":   b["competencia"].map(_mes_ref),
        "data_pag":  pd.to_datetime(b["data_pagamento"], errors="coerce"),
        "valor":     pd.to_numeric(b["valor_documento"], errors="coerce"),
        "multa_adm": multa,
        "juros_adm": pd.to_numeric(b["juros_doc"], errors="coerce").fillna(0.0),
    })
    sem_valor = int(boletos["valor"].isna().sum())
    if verbose:
        enc = int(((boletos["multa_adm"] > 0) | (boletos["juros_adm"] > 0)).sum())
        print(f"  [imobiliar-dw] boletos: {len(boletos)} · {enc} com encargo")
        if sem_valor:
            print(f"  ⚠️  [imobiliar-dw] {sem_valor} boleto(s) SEM valor_documento — "
                  f"saem pela R1 como 'valor nulo'. Conferir o join com doc_capa.")

    # ── proprietário sintético: 1 por imóvel, carregando o dia_pag do boleto
    dia = b.assign(cd=b["codigo_imovel"].map(_cd),
                   dp=pd.to_numeric(b["dia_pagamento_proprietario"], errors="coerce"),
                   dt=pd.to_datetime(b["data_pagamento"], errors="coerce"))
    dia = dia.dropna(subset=["cd", "dp"]).sort_values("dt")
    variou = dia.groupby("cd")["dp"].nunique()
    if verbose and int((variou > 1).sum()):
        ims = ", ".join(f"IM{int(i)}" for i in variou[variou > 1].index[:10])
        print(f"  ⚠️  [imobiliar-dw] {int((variou > 1).sum())} imóvel(is) com mais de um "
              f"dia_pag no período (troca de titular?) — fica o do boleto mais "
              f"recente: {ims}")
    ult = dia.groupby("cd").last().reset_index()

    nomes = _query(
        "SELECT codigo_imovel, nome_proprietario, percentual_renda "
        "FROM imobiliar_proprietarios_imoveis"
    )
    nomes["cd"] = nomes["codigo_imovel"].map(_cd)
    nomes["pct"] = pd.to_numeric(nomes["percentual_renda"], errors="coerce").fillna(0)
    # com vários sócios, fica quem tem o maior percentual — só rótulo de drilldown
    nomes = (nomes.sort_values("pct", ascending=False)
                  .dropna(subset=["cd"]).groupby("cd").first().reset_index())

    prop = ult[["cd", "dp"]].merge(nomes[["cd", "nome_proprietario"]], on="cd", how="left")
    proprietarios = pd.DataFrame({
        # id sintético = o próprio IM, em texto (mesmo motivo do _cd)
        "id_proprietario": prop["cd"].astype(str),
        "dia_pag":         prop["dp"].astype(int),
        "nome":            prop["nome_proprietario"].fillna(""),
    })

    imv = _query(
        "SELECT codigo_imovel, logradouro, numero, complemento, bairro, cidade "
        "FROM imobiliar_imoveis"
    )
    imv["cd"] = imv["codigo_imovel"].map(_cd)

    # ⚠️ `numero` vem NUMÉRICO do banco (5.0, 104). `" ".join` só aceita str e
    # estoura com TypeError — foi o que derrubou o extrator na estreia (20/08):
    #   "sequence item 1: expected str instance, float found"
    # Converter ANTES de juntar, e limpar o ".0" que o float deixa.
    def _txt(v) -> str:
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return ""
        if isinstance(v, float) and v.is_integer():
            return str(int(v))
        return str(v).strip()

    partes = imv[["logradouro", "numero", "complemento", "bairro", "cidade"]]
    end = partes.apply(
        lambda r: " ".join(t for t in (_txt(x) for x in r) if t), axis=1)
    imoveis = pd.DataFrame({
        "cd_imovel":       imv["cd"],
        "id_proprietario": imv["cd"],   # mesmo id sintético
        "endereco":        end.str.strip(),
    }).dropna(subset=["cd_imovel"])

    if verbose:
        print(f"  [imobiliar-dw] proprietários com dia_pag: {len(proprietarios)} · "
              f"imóveis: {len(imoveis)}")
    return {"boletos": boletos, "proprietarios": proprietarios, "imoveis": imoveis}
