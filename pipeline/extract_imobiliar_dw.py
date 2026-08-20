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
    valor       imobiliar_doc_capa.valor_documento  (join por id_documento)
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

⚠️ ESTE EXTRATOR NÃO RESOLVE A REGRA R1
   R1 separa multa de atraso (≤15% do valor) de multa de rescisão (>15%).
   Pelos números da CSV, 2 boletos passam de 15% (IM1783, competências 04 e 05,
   logo após o distrato de 08/04/2026). Pelos números do BANCO, nenhum passa —
   as duas fontes dividem `valor` e `multa` de forma diferente e a soma bate
   (ver claude/INADIMPLENCIA_migracao_e_regra_R1_18-08-2026.md).
   Isso é DE PROPÓSITO: o painel-sombra existe para mostrar essa divergência
   na tela, boleto a boleto, em vez de a decisão ser tomada no escuro.
   A nota da Inadimplência no espelho vai ficar diferente da de produção.
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

    b = _query(
        """
        SELECT b.codigo_imovel, b.competencia, b.data_pagamento,
               b.valor_multa_adm, b.valor_juros_adm, b.dia_pagamento_proprietario,
               c.valor_documento
        FROM imobiliar_boletos_encargo_adm b
        LEFT JOIN imobiliar_doc_capa c ON c.id_documento = b.id_documento
        """
    )
    boletos = pd.DataFrame({
        "cd_imovel": b["codigo_imovel"].map(_cd),
        "mes_ref":   b["competencia"].map(_mes_ref),
        "data_pag":  pd.to_datetime(b["data_pagamento"], errors="coerce"),
        "valor":     pd.to_numeric(b["valor_documento"], errors="coerce"),
        "multa_adm": pd.to_numeric(b["valor_multa_adm"], errors="coerce").fillna(0.0),
        "juros_adm": pd.to_numeric(b["valor_juros_adm"], errors="coerce").fillna(0.0),
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
