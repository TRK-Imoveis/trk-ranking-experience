"""
TRK Experience — Orquestrador principal
=======================================

Roda o pipeline completo:
  1. Extrai os 12 pipes do Pipefy (usa cache em dados/raw/ se disponível).
  2. Carrega XLSX do Octadesk de dados/octadesk/ (LOCAL — quando API entrar, troca o módulo).
  3. Carrega CSVs do Imobiliar de dados/csv/ + calcula N do bônus Inadimplência (LOCAL).
  4. Calcula ranking dos 5 colaboradores via funções calc_* de calculate.py.
  5. Gera docs/dados/atual.json no formato PESSOAS / IMOVEIS / PROC_RICH.
  6. (Opcional) `--validate` compara contra baselines.json.

CLI:
    python pipeline/run.py                    # snapshot completo
    python pipeline/run.py --validate         # roda só a validação
    python pipeline/run.py --no-cache         # força re-extract dos pipes
    python pipeline/run.py --ref 2026-05-14   # data de referência (ISO)
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from calculate import (
    calc_caio_comercial_locacao, calc_caio_contrato_locacao, calc_caio_contrato_adm, calc_caio_renovacao,
    calc_caio_whatsapp, calc_caio_ticket,
    calc_vivianne_contrato_adm, calc_vivianne_rescisao_adm, calc_vivianne_contrato_locacao,
    calc_vivianne_rescisao_locacao, calc_vivianne_renovacao, calc_vivianne_inadimplencia,
    calc_vivianne_backoffice, calc_vivianne_ticket,
    calc_assessora_contrato_adm, calc_assessora_rescisao_adm, calc_assessora_rescisao_locacao,
    calc_assessora_reparos, calc_assessora_renovacao, calc_assessora_backoffice, calc_assessora_dirf_darf,
    calc_assessora_whatsapp, calc_assessora_ticket,
    calc_marinho_vistorias, calc_marinho_contestacoes,
    nota_final,
)
from pipeline.extract_pipefy import extract_pipe
from pipeline.extract_octadesk import extract_octadesk
from pipeline.extract_imobiliar import (extract_imobiliar, calcular_bonus_inadimplencia,
                                        carregar_distratos, carregar_repasses)
from pipeline.imoveis_builder import gerar_imoveis
from pipeline.procrich_builder import gerar_proc_rich, _meta_from_nome

OUT_DIR = ROOT / "docs" / "dados"
OUT_JSON = OUT_DIR / "atual.json"

NOMES = {
    "caio":     ("Caio Rodrigues Lima", "Comercial"),
    "vivianne": ("Vivianne Fontes",      "BackOffice · Inadimplência"),
    "marinho":  ("Albérico Marinho",     "Vistoriador"),
    "natalia":  ("Natália Teixeira",     "Assessora"),
    "gardenia": ("Gardênia",             "Assessora"),
}

# Encurtadores para pontosFort/Aten
SHORT = {
    "Comercial": "Comercial", "Cont. Locação": "Cont.Loc", "Cont. ADM": "Cont.ADM",
    "Rescisão ADM": "RescADM", "Rescisão Loc.": "RescLoc", "Reparos": "Reparos",
    "Renovação": "Renov", "Inadimplência": "Inad", "BackOffice": "BO",
    "DIRF/DARF": "DIRF", "WhatsApp": "WA", "Ticket": "Tkt", "Tickets": "Tkts",
    "Vistorias": "Vist", "Contestações": "Cont", "Laudos": "Laudos",
}


# ────────────────────────────────────────────────────────────────────
# Carregamento de DataFrames
# ────────────────────────────────────────────────────────────────────

def carregar_dataframes(*, use_cache: bool = True, verbose: bool = True,
                        fonte: str = "api") -> dict[str, pd.DataFrame]:
    """Retorna dict com todos os DFs (Pipefy + Octadesk + Imobiliar).

    fonte="api"   → extract_pipefy (produção)
    fonte="banco" → extract_dw (dw_trk, painel-sombra de ?fonte=banco)

    O `extract_dw` devolve o MESMO contrato de colunas do `extract_pipefy`, então
    nada em calculate.py/imoveis_builder.py muda. É por isso que o painel-sombra
    NÃO é um projeto duplicado: mesma regra, mesmo código, só o extrator troca.
    Duplicar o projeto significaria manter duas cópias do calculate.py — e na
    primeira regra alterada em só um lado, a comparação viraria ruído.
    """
    pipes = [
        "comercial_locacao", "cont_locacao", "cont_adm", "rescisao_adm", "rescisao_loc",
        "reparos", "renovacao", "inadimplencia", "backoffice", "dirf_darf",
        "vistorias", "contestacoes",
    ]
    if fonte == "banco":
        from pipeline.extract_dw import extract_pipe as _extract  # import tardio: só quem usa precisa do psycopg2
        if verbose:
            print("\n[fonte] dw_trk (painel-sombra) — extract_dw")
    else:
        _extract = extract_pipe
    dfs = {k: _extract(k, use_cache=use_cache, verbose=verbose) for k in pipes}

    if verbose:
        print("\n[octadesk] carregando arquivos locais…")
    oct_ = extract_octadesk(verbose=verbose)
    dfs.update(oct_)  # adiciona conversas, tickets, aval_tickets

    # PAINEL-SOMBRA: WhatsApp do banco (18/08/2026).
    # Só as CONVERSAS migram por enquanto. Os TICKETS continuam no XLSX nas duas
    # fontes porque duas das três exclusões obrigatórias não são reproduzíveis
    # no dw_trk hoje: `categoria_assunto` chega 100% nula (mata a exclusão
    # "Cancelado / Spam") e o assunto "Tarefa" não está em `summary`. Sem elas o
    # denominador infla ~40% e a nota cai por falta de dado, não por desempenho.
    # Ver claude/OCTADESK_no_dw_18-08-2026.md.
    # WHATSAPP MIGRADO (20/08/2026) — vale para as DUAS fontes, não só o sombra.
    # Controlado por config/feature_flags.json::whatsapp_do_banco.
    # Se o banco falhar, cai de volta no XLSX e AVISA — nunca publica em silêncio
    # com fonte diferente da esperada.
    from calculate import FEATURE_FLAGS
    if FEATURE_FLAGS.get("whatsapp_do_banco", False) or fonte == "banco":
        try:
            from pipeline.extract_octadesk_dw import extract_conversas_dw
            if verbose:
                print("[octadesk] conversas: lendo do dw_trk (XLSX não é mais usado aqui)…")
            dfs["conversas"] = extract_conversas_dw(verbose=verbose)
        except Exception as exc:
            print(f"⚠️  [octadesk] CAIU DE VOLTA no XLSX — os 6 indicadores de WhatsApp "
                  f"desta rodada vieram do arquivo, não do banco. "
                  f"{exc.__class__.__name__}: {exc}")
            import traceback; traceback.print_exc()

    if verbose:
        print("\n[imobiliar] carregando CSVs locais…")
    imob = extract_imobiliar(verbose=verbose)
    dfs["imobiliar"] = imob   # guarda os 3 sub-DFs sob "imobiliar"

    # INADIMPLÊNCIA DO BANCO — só no painel-sombra (20/08/2026).
    # Substitui os 3 CSVs por imobiliar_boletos_encargo_adm + doc_capa.
    # NÃO vai para produção ainda: a regra R1 (multa >15% = rescisão) dá
    # resultado diferente nas duas fontes, e o espelho existe para mostrar
    # essa divergência na tela antes de a gestora decidir qual vale.
    # Ver claude/INADIMPLENCIA_migracao_e_regra_R1_18-08-2026.md
    if fonte == "banco":
        try:
            from pipeline.extract_imobiliar_dw import extract_imobiliar_dw
            if verbose:
                print("[imobiliar] trocando os CSVs pelo dw_trk (painel-sombra)…")
            dfs["imobiliar"] = extract_imobiliar_dw(verbose=verbose)
        except Exception as exc:
            print(f"⚠️  [imobiliar] CAIU DE VOLTA nos CSVs na Inadimplência — "
                  f"{exc.__class__.__name__}: {exc}")
            import traceback; traceback.print_exc()
    # data_distrato = entrega efetiva das chaves (Rescisão Loc., 13ª Ed)
    dfs["distratos"] = carregar_distratos(verbose=verbose)
    # data real do repasse ao proprietário ("Pagto Prop") p/ a regra R3 do bônus
    dfs["repasses"] = carregar_repasses(verbose=verbose)
    return dfs


# ────────────────────────────────────────────────────────────────────
# Pontos fortes / atenção
# ────────────────────────────────────────────────────────────────────

def _curto(nome_ind: str) -> str:
    """Encurta 'Comercial — Início processo <24h' → 'Comercial Início'."""
    parte = nome_ind.split("—")[0].strip() if "—" in nome_ind else nome_ind
    return SHORT.get(parte, parte)[:14]


def pontos_fort_aten(indicadores: list[dict]) -> tuple[list[str], list[str]]:
    """Top 4 maiores pct (fortes) e top 4 menores pct (atenção). Ignora bônus."""
    validos = [i for i in indicadores if i.get("pct") is not None and "★" not in i["nome"]]
    if not validos:
        return [], []
    ord_desc = sorted(validos, key=lambda i: i["pct"], reverse=True)
    ord_asc = sorted(validos, key=lambda i: i["pct"])
    fort = [f"{_curto(i['nome'])}: {i['pct']:.1f}%" for i in ord_desc[:4]]
    aten = [f"{_curto(i['nome'])}: {i['pct']:.1f}%" for i in ord_asc[:4]]
    return fort, aten


# ────────────────────────────────────────────────────────────────────
# Cálculo por colaborador (devolve dict no formato PESSOAS)
# ────────────────────────────────────────────────────────────────────

def _safe(fn, *args, **kwargs) -> dict:
    """Chama uma função calc_*; converte NotImplementedError em resultado vazio."""
    try:
        return fn(*args, **kwargs)
    except NotImplementedError as e:
        print(f"  [skip] {fn.__name__}: {e}")
        return {"nota": None, "indicadores": []}


def calc_caio(dfs: dict, bonus_n: int, ref: pd.Timestamp) -> dict:
    com  = calc_caio_comercial_locacao(dfs["comercial_locacao"], bonus_n=bonus_n, ref=ref)
    cl   = calc_caio_contrato_locacao(dfs["comercial_locacao"], dfs["cont_locacao"], ref=ref)
    cadm = calc_caio_contrato_adm(dfs["cont_adm"], ref=ref)
    ren  = calc_caio_renovacao(dfs["renovacao"], ref=ref)
    wa   = _safe(calc_caio_whatsapp, dfs["conversas"])
    tkt  = _safe(calc_caio_ticket, dfs["tickets"], dfs["aval_tickets"])
    scores = {
        "Com. Locação": com["nota"], "Cont. Locação": cl["nota"], "Cont. ADM": cadm["nota"],
        "Renovação": ren["nota"], "WhatsApp": wa["nota"], "Ticket": tkt["nota"],
    }
    detalhes = (com["indicadores"] + cl["indicadores"] + cadm["indicadores"]
                + ren["indicadores"] + wa["indicadores"] + tkt["indicadores"])
    return _montar_pessoa("caio", scores, detalhes, bonus_n, "Com. Locação")


def calc_vivianne(dfs: dict, bonus_n: int, ref: pd.Timestamp) -> dict:
    cadm = calc_vivianne_contrato_adm(dfs["cont_adm"], ref=ref)
    radm = calc_vivianne_rescisao_adm(dfs["rescisao_adm"], ref=ref)
    cloc = calc_vivianne_contrato_locacao(dfs["cont_locacao"], ref=ref)
    rloc = calc_vivianne_rescisao_locacao(dfs["rescisao_loc"], ref=ref)
    ren  = calc_vivianne_renovacao(dfs["renovacao"], ref=ref)
    ina  = calc_vivianne_inadimplencia(dfs["inadimplencia"], bonus_n=bonus_n, ref=ref,
                                       bonus_tot=dfs.get("_bonus_viv_tot", 0),
                                       cobrados=dfs.get("_bonus_viv_cobrados", 0))
    bo   = calc_vivianne_backoffice(dfs["backoffice"], ref=ref)
    tkt  = _safe(calc_vivianne_ticket, dfs["tickets"])
    scores = {
        "Cont. ADM": cadm["nota"], "Rescisão ADM": radm["nota"], "Cont. Locação": cloc["nota"],
        "Rescisão Loc.": rloc["nota"], "Renovação": ren["nota"], "Inadimplência": ina["nota"],
        "BackOffice": bo["nota"], "Ticket": tkt["nota"],
    }
    detalhes = (cadm["indicadores"] + radm["indicadores"] + cloc["indicadores"] + rloc["indicadores"]
                + ren["indicadores"] + ina["indicadores"] + bo["indicadores"] + tkt["indicadores"])
    # 13ª Ed: a Vivianne não tem mais BÔNUS — "Cobrança antes do repasse" virou
    # indicador com peso 4. Sem ★ na linha dela.
    return _montar_pessoa("vivianne", scores, detalhes, 0, None)


def _listar_revisoes() -> None:
    """Cards que o cálculo marcou para conferência manual (13ª Ed)."""
    import calculate as _C
    fant = getattr(_C, "_RESC_ADM_FANTASMA", [])
    if fant:
        print(f"\n[revisar] Rescisão ADM — {len(fant)} card(s) com ciclo NEGATIVO "
              f"(passagem-fantasma, contam ✗):")
        for quem, titulo, d in fant:
            print(f"   {quem:9} {titulo[:58]:58} {d:>9.1f}d")
    neg = getattr(_C, "_RESC_LOC_NEGATIVOS", [])
    if neg:
        print(f"\n[revisar] Rescisão Loc. — {len(neg)} card(s) com levantamento ANTES "
              f"da entrega das chaves (fora do denominador):")
        for quem, unidade, titulo, v in neg:
            print(f"   {quem:9} {unidade:16} {titulo[:44]:44} {v:>9.1f}")


def calc_assessora(pid: str, dfs: dict, bonus_n: int, ref: pd.Timestamp) -> dict:
    cadm = calc_assessora_contrato_adm(dfs["cont_adm"], pid, bonus_n=bonus_n, ref=ref)
    radm = calc_assessora_rescisao_adm(dfs["rescisao_adm"], pid, ref=ref)
    rloc = calc_assessora_rescisao_locacao(dfs["rescisao_loc"], pid, ref=ref,
                                           distratos=dfs.get("distratos"))
    rep  = calc_assessora_reparos(dfs["reparos"], pid, ref=ref)
    ren  = calc_assessora_renovacao(dfs["renovacao"], pid, ref=ref)
    bo   = calc_assessora_backoffice(dfs["backoffice"], pid, ref=ref)
    dirf = calc_assessora_dirf_darf(dfs["dirf_darf"], pid, ref=ref)
    wa   = _safe(calc_assessora_whatsapp, dfs["conversas"], pid)
    tkt  = _safe(calc_assessora_ticket, dfs["tickets"], dfs["aval_tickets"], pid)
    scores = {
        "Cont. ADM": cadm["nota"], "Rescisão ADM": radm["nota"], "Rescisão Loc.": rloc["nota"],
        "Reparos": rep["nota"], "Renovação": ren["nota"], "BackOffice": bo["nota"],
        "DIRF/DARF": dirf["nota"], "WhatsApp": wa["nota"], "Ticket": tkt["nota"],
    }
    detalhes = (cadm["indicadores"] + radm["indicadores"] + rloc["indicadores"] + rep["indicadores"]
                + ren["indicadores"] + bo["indicadores"] + dirf["indicadores"]
                + wa["indicadores"] + tkt["indicadores"])
    return _montar_pessoa(pid, scores, detalhes, {
        "Cont. ADM": bonus_n,                       # vistoria de entrada realizada
        "Renovação": ren.get("bonus_n", 0),         # assinado no prazo com card sem prazo
    })


def calc_marinho(dfs: dict, ref: pd.Timestamp) -> dict:
    vist = calc_marinho_vistorias(dfs["vistorias"], ref=ref)
    cont = calc_marinho_contestacoes(dfs["contestacoes"], ref=ref)
    # Marinho: 2 processos separados, nota final = média
    nota = nota_final({"v": vist["nota"], "c": cont["nota"]})
    scores = {"Vistorias": nota}   # painel mostra 1 coluna só
    detalhes = vist["indicadores"] + cont["indicadores"]
    p = _montar_pessoa("marinho", scores, detalhes,
                       bonus_n=vist.get("bonus_n", 0), bonus_proc="Vistorias")
    p["nota"] = nota
    return p


def _montar_pessoa(pid: str, scores: dict, detalhes: list, bonus_n,
                   bonus_proc: Optional[str] = None) -> dict:
    """bonus_n aceita int (um processo só, via bonus_proc) OU dict
    {processo: N} quando a pessoa tem bônus em mais de um processo.

    ⚠️ 14/08/2026: Natália e Gardênia passaram a ter DOIS bônus — vistoria de
    entrada no Cont. ADM e recuperação na Renovação. Antes o painel guardava um
    número e um nome de processo, então o ★ só aparecia numa coluna e o Resumo
    Executivo somava errado. `bonus_por_proc` é a fonte de verdade; `bonus` e
    `bonus_proc` continuam preenchidos (total e processo de maior N) só para o
    JS legado não quebrar.
    """
    if isinstance(bonus_n, dict):
        bonus_por_proc = {k: int(v) for k, v in bonus_n.items() if v}
    else:
        bonus_por_proc = {bonus_proc: int(bonus_n)} if (bonus_proc and bonus_n) else {}
    bonus_total = sum(bonus_por_proc.values())
    proc_principal = (max(bonus_por_proc, key=bonus_por_proc.get)
                      if bonus_por_proc else None)
    nome, cargo = NOMES[pid]
    nota = nota_final(scores)
    # Enriquece cada item de detalhes[] com o campo 'meta' (single source of truth:
    # META_MAP definido em procrich_builder._meta_from_nome). Usado pelo drawer e
    # pelo painel de processo no HTML.
    for d in detalhes:
        d["meta"] = _meta_from_nome(d["nome"])
    fort, aten = pontos_fort_aten(detalhes)
    # 13 colunas-padrão do painel (preserva chaves nulas para alinhar visualmente)
    cols_padrao = ["Cont. ADM", "Rescisão ADM", "Com. Locação", "Cont. Locação", "Rescisão Loc.",
                   "Reparos", "Renovação", "Inadimplência", "Vistorias", "BackOffice",
                   "DIRF/DARF", "WhatsApp", "Ticket"]
    scores_full = {c: scores.get(c) for c in cols_padrao}
    return {
        "id": pid, "nome": nome, "cargo": cargo,
        "nota": nota, "bonus": bonus_total, "bonus_proc": proc_principal,
        "bonus_por_proc": bonus_por_proc,
        "inds": len(detalhes),
        "pts": round(sum((d.get("peso") or 0) for d in detalhes), 1),
        "scores": scores_full,
        "detalhes": detalhes,
        "pontosFort": fort, "pontosAten": aten,
    }


# ────────────────────────────────────────────────────────────────────
# Build atual.json
# ────────────────────────────────────────────────────────────────────

def build_atual(dfs: dict, *, ref: pd.Timestamp, bonus_n_vivianne: int,
                verbose: bool = True) -> dict:
    # Bônus de assessora/Caio: derivados do Pipefy (já estão sendo aplicados nas funções).
    # Por enquanto usamos os mesmos valores empíricos da 10ª Ed para Caio/Natália/Gardênia
    # — calc_assessora_contrato_adm aplica bonus_n no nota_processo; o N efetivo da edição
    # atual deveria vir do cruzamento de Pipefy (campo "Criar Card de Vistoria Técnica").
    # TODO: contar dinamicamente N a partir do df_cont_adm filtrado por Assessor.
    bonus_caio = _contar_bonus_caio(dfs, ref=ref)
    bonus_natalia = _contar_bonus_assessora(dfs, "natalia", ref=ref)
    bonus_gardenia = _contar_bonus_assessora(dfs, "gardenia", ref=ref)

    if verbose:
        print(f"\n[bonus] caio_imovel_alugado={bonus_caio}  vivianne_boletos={bonus_n_vivianne}  "
              f"natalia_vistoria={bonus_natalia}  gardenia_vistoria={bonus_gardenia}")

    import calculate as _C   # listas de revisão manual acumulam por chamada
    _C._RESC_ADM_FANTASMA.clear()
    _C._RESC_LOC_NEGATIVOS.clear()

    pessoas = [
        calc_caio(dfs, bonus_caio, ref),
        calc_vivianne(dfs, bonus_n_vivianne, ref),
        calc_assessora("natalia", dfs, bonus_natalia, ref),
        calc_assessora("gardenia", dfs, bonus_gardenia, ref),
        calc_marinho(dfs, ref),
    ]
    pessoas.sort(key=lambda p: (p["nota"] or 0), reverse=True)
    for pos, p in enumerate(pessoas, 1):
        p["pos"] = pos

    if verbose:
        _listar_revisoes()
        try:
            from calculate import calc_renovacao_abertura
            ab = calc_renovacao_abertura(dfs["renovacao"], ref=ref)
            i = ab["indicadores"][0]
            print(f"\n[diagnóstico] Renovação — cards abertos com +60d do vencimento: "
                  f"{i['ok']}/{i['tot']} ({i['pct']}%) · {ab['atrasados']} abertos tarde")
            print("   (não entra no ranking — quem abre é a gestora, que não é avaliada)")
            print(f"[diagnóstico] Renovação — marcados 'não renova' (fora do denominador): "
                  f"{ab['nao_renovam']}")
            if ab["campos_divergentes"]:
                print(f"   ⚠ {ab['campos_divergentes']} card(s) com os DOIS campos de "
                      f"'vai renovar?' preenchidos e DISCORDANDO — vale aposentar o select")
        except Exception as exc:
            print(f"[diagnóstico] abertura de renovação indisponível: {exc}")

    return {
        "_meta": {
            "geradoEm": datetime.utcnow().isoformat() + "Z",
            "ref": ref.isoformat(),
            # De onde vieram os dados do Pipefy nesta rodada + quando o ETL
            # carregou o banco pela última vez. O painel-sombra (?fonte=banco)
            # mostra essa hora na tela: sem ela não dá para distinguir
            # "o banco calculou diferente" de "o banco está com dado de quinta".
            "fonte": dfs.get("_fonte", "api"),
            "etl_ultima_carga": dfs.get("_etl_ultima_carga"),
            "octadesk_disponivel": bool(len(dfs.get("conversas", pd.DataFrame()))) or
                                    bool(len(dfs.get("tickets", pd.DataFrame()))),
            "imobiliar_disponivel": bool(len(dfs.get("imobiliar", {}).get("boletos", pd.DataFrame()))),
        },
        "PESSOAS": pessoas,
        "IMOVEIS": gerar_imoveis(dfs, ref),
        "PROC_RICH": gerar_proc_rich(pessoas),
        # Baseline dos deltas = ÚLTIMA EDIÇÃO FECHADA. Atualizar a cada fechamento.
        # 13/08/2026: estava com as notas da 10ª Ed (caio 5,34 · vivianne 5,01 ·
        # marinho 3,91 · natalia 4,02 · gardenia 4,10) — as setinhas do painel
        # comparavam contra a edição errada há duas edições.
        # Agora: 12ª Edição, fechada em 18/06/2026.
        #
        # ⚠️ A régua mudou em 13/08/2026 (horas úteis, datas do banco, redesenho do
        # bônus). O delta contra a 12ª mistura mudança de desempenho com mudança de
        # critério. A partir do fechamento da 13ª isso se resolve sozinho.
        #
        # A chave mantém o nome "BASELINE_9" por compatibilidade com o JS do
        # docs/index.html (lida em ~10 pontos). Renomear continua pendência cosmética.
        "BASELINE_9": {"vivianne": 6.25, "natalia": 4.92, "gardenia": 4.64,
                       "caio": 4.62, "marinho": 3.90},
    }


def _contar_bonus_caio(dfs: dict, ref: Optional[pd.Timestamp] = None,
                        validated_ims: Optional[set[int]] = None) -> int:
    """
    Bônus Caio · imóveis alugados ANTES de serem anunciados (manual v4 §4.1).

    Critério (validado 8ª/10ª Ed):
      1. Existe card no pipe Cont.Locação com "Primeira vez fase 1º Boleto" preenchida.
      2. NENHUM card do Comercial Caio para esse IM tem "Data publicação Anúncio" preenchida.

    ⚠️ O pipe Comercial só mostra cards do recorte 180d. IMs com anúncio anterior NÃO
       aparecem mas TAMBÉM não são elegíveis ao bônus. Por isso a função LOGA candidatos
       para validação manual e retorna 0 (ou len(candidates ∩ validated_ims) se passado).
    """
    from calculate import excluir_rascunhos, filtrar_por_assignee, extrair_im

    df_cl = dfs.get("cont_locacao", pd.DataFrame())
    df_com = dfs.get("comercial_locacao", pd.DataFrame())
    if len(df_cl) == 0 or len(df_com) == 0:
        return 0

    col_boleto = "Primeira vez que entrou na fase 1º Boleto"
    if col_boleto not in df_cl.columns:
        print(f"[bonus_caio] coluna '{col_boleto}' ausente no Cont.Locação — bonus_n=0")
        return 0

    # Cutoff 180d aplicado ao 1º Boleto: bônus refere-se à edição corrente, não histórico.
    from calculate import aplicar_cutoff as _cutoff
    df_cl_ok = _cutoff(df_cl, col_boleto, ref=ref).dropna(subset=[col_boleto]).copy()
    df_cl_ok["IM"] = df_cl_ok["Título"].apply(extrair_im)
    df_cl_ok = df_cl_ok.dropna(subset=["IM"])

    # Comercial Caio (filtrado por Profissional responsável)
    df_com_caio = excluir_rascunhos(df_com)
    df_com_caio = filtrar_por_assignee(df_com_caio, "Profissional responsável", "Caio")
    df_com_caio["IM"] = df_com_caio["Título"].apply(extrair_im)
    col_anuncio = "Data publicação Anúncio"
    if col_anuncio not in df_com_caio.columns:
        print(f"[bonus_caio] coluna '{col_anuncio}' ausente no Comercial — bonus_n=0")
        return 0
    # IMs do Comercial Caio com anúncio preenchido (em qualquer momento dentro do recorte)
    ims_com_anuncio = set(
        df_com_caio.dropna(subset=[col_anuncio, "IM"])["IM"].astype(int).tolist()
    )

    candidatos = []
    for _, row in df_cl_ok.iterrows():
        im = int(row["IM"])
        if im in ims_com_anuncio:
            continue  # tem anúncio → não elegível
        cards_com_im = df_com_caio[df_com_caio["IM"] == im]
        candidatos.append({
            "im": im,
            "data_1o_boleto": row[col_boleto],
            "card_cl_id": row.get("id"),
            "qtd_cards_comercial": len(cards_com_im),
            "fases_comercial": cards_com_im["Fase atual"].tolist() if len(cards_com_im) else [],
        })

    print(f"\n[bonus_caio] {len(candidatos)} candidato(s) ao bônus — precisam validação manual:")
    for c in candidatos[:50]:
        boleto_str = c["data_1o_boleto"].date().isoformat() if pd.notna(c["data_1o_boleto"]) else "—"
        print(f"  IM{c['im']:>5}  1º Boleto={boleto_str}  comercial_cards={c['qtd_cards_comercial']}  "
              f"fases={c['fases_comercial']}")

    # Carrega lista de IMs validados de config/bonus_caio.json se não passada explicitamente
    override_ims: set[int] = set()
    if validated_ims is None:
        cfg_path = ROOT / "config" / "bonus_caio.json"
        if cfg_path.exists():
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            # Cobertura: continuação + IMs validados da edição vigente (12ª).
            validated_ims = set(cfg.get("edicao_12_continuacao", []) + cfg.get("edicao_12_validados", []))
            # Override manual: IMs que a regra automática EXCLUI (ex.: "Data publicação
            # Anúncio" preenchido sem publicação real) mas que a gestora validou como
            # elegíveis caso a caso. Somados ao N mesmo não estando entre os candidatos.
            override_ims = set((cfg.get("edicao_12_override_incluir", {}) or {}).get("ims", []))
            print(f"[bonus_caio] carregada config/bonus_caio.json: continuação={cfg.get('edicao_12_continuacao')}  "
                  f"validados_12={cfg.get('edicao_12_validados')}  override={sorted(override_ims)}")
        else:
            print(f"[bonus_caio] config/bonus_caio.json não encontrado — N=0")
            return 0

    cand_ims = {c["im"] for c in candidatos}
    validos = validated_ims & cand_ims
    override_efetivo = override_ims - validos  # evita contar duas vezes
    invalidos_da_config = validated_ims - cand_ims  # IMs validados mas que não estão entre os candidatos (drift)
    pendentes = cand_ims - validated_ims
    n_total = len(validos) + len(override_efetivo)
    print(f"[bonus_caio] N={n_total}  validados∩candidatos={sorted(validos)}  override(+{len(override_efetivo)})={sorted(override_efetivo)}")
    if invalidos_da_config:
        print(f"[bonus_caio] AVISO: validados na config mas fora dos candidatos atuais (drift): "
              f"{sorted(invalidos_da_config)}")
    if pendentes:
        print(f"[bonus_caio] pendentes (precisam validação): {sorted(pendentes)}")
    return n_total


def _contar_bonus_assessora(dfs: dict, assessora: str, ref: Optional[pd.Timestamp] = None) -> int:
    """
    Bônus assessora · "Vistoria de entrada realizada" (Cont. ADM, manual v4 §4.3).

    N = cards no pipe Cont.ADM (cutoff 180d) onde:
      - "Criar Card de Vistoria Técnica" preenchido
      - "Assessor (lista)" contém o nome da assessora
      - Para GARDÊNIA: cards SEM Assessor preenchido mas CONCLUÍDOS também contam (regra 8ª Ed).
    """
    from calculate import (excluir_rascunhos, aplicar_cutoff, _nome_assessora_alt,
                            _contem_qualquer, _as_list)

    df = dfs.get("cont_adm", pd.DataFrame())
    if len(df) == 0:
        return 0
    df = excluir_rascunhos(df)
    df = aplicar_cutoff(df, "Criado em", ref=ref)

    col_vist = "Criar Card de Vistoria Técnica"
    col_assess = "Assessor (lista)"
    if col_vist not in df.columns or col_assess not in df.columns:
        return 0

    # Critério "vistoria efetivamente criada": campo precisa ter conteúdo NÃO-VAZIO.
    # Pipefy retorna lista; quando o card não tem vistoria, vem como '[]' (string), [] (lista
    # vazia), null, "" ou whitespace. Tudo isso conta como NÃO preenchido.
    def _vist_preenchida(v) -> bool:
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return False
        if isinstance(v, list):
            return len(v) > 0
        s = str(v).strip()
        return s not in ("", "[]", "null", "None")

    nomes = _nome_assessora_alt(assessora)
    mask_nome = df[col_assess].apply(lambda v: _contem_qualquer(v, nomes))
    if assessora == "gardenia":
        sem_assessor = df[col_assess].apply(lambda v: not _as_list(v))
        concluido = df.get("Primeira vez que entrou na fase Concluído", pd.Series([pd.NaT]*len(df))).notna()
        mask_nome = mask_nome | (sem_assessor & concluido)

    mask_final = mask_nome & df[col_vist].apply(_vist_preenchida)
    sub = df[mask_final]
    n = int(len(sub))

    ims = sub["Título"].apply(lambda t: __import__("re").search(r"IM\s*(\d+)", str(t), __import__("re").IGNORECASE))
    ims_list = [int(m.group(1)) for m in ims if m]
    print(f"[bonus_{assessora}] N={n} cards  IMs={ims_list[:15]}{'…' if len(ims_list)>15 else ''}")
    return n


# ────────────────────────────────────────────────────────────────────
# CLI
# ────────────────────────────────────────────────────────────────────

def main(argv: list[str]) -> None:
    use_cache = "--no-cache" not in argv
    validate = "--validate" in argv
    # PAINEL-SOMBRA (18/08/2026, pedido da gestora)
    # --fonte banco → lê do dw_trk e grava docs/dados/banco.json, SEM tocar no
    # atual.json. O painel abre em ?fonte=banco e carrega esse arquivo. Serve
    # para rodar as duas fontes em paralelo até a migração fechar.
    fonte = "api"
    if "--fonte" in argv:
        fonte = str(argv[argv.index("--fonte") + 1]).strip().lower()
        if fonte not in ("api", "banco"):
            raise SystemExit(f"--fonte aceita 'api' ou 'banco', recebi {fonte!r}")
    saida = OUT_JSON if fonte == "api" else OUT_DIR / "banco.json"
    ref = pd.Timestamp.utcnow()
    if "--ref" in argv:
        ref = pd.Timestamp(argv[argv.index("--ref") + 1], tz="UTC")

    print(f"[run] use_cache={use_cache}  validate={validate}  fonte={fonte}  "
          f"ref={ref.isoformat()}")
    dfs = carregar_dataframes(use_cache=use_cache, verbose=True, fonte=fonte)
    dfs["_fonte"] = fonte
    if fonte == "banco":
        try:
            from pipeline.extract_dw import ultima_carga_etl
            dfs["_etl_ultima_carga"] = ultima_carga_etl()
            print(f"[fonte] última carga do ETL: {dfs['_etl_ultima_carga']}")
        except Exception as exc:
            dfs["_etl_ultima_carga"] = None
            print(f"[fonte] hora da última carga do ETL indisponível ({exc.__class__.__name__})")

    if validate:
        from pipeline.validate import validar
        validar(ref)
        return

    bonus_viv = calcular_bonus_inadimplencia(
        dfs["imobiliar"], df_inadimplencia=dfs["inadimplencia"], ref=ref,
        repasses_reais=dfs.get("repasses"),
    )
    # Persiste resultado em config/bonus_vivianne.json para auditoria e drilldown.
    cfg_viv = ROOT / "config" / "bonus_vivianne.json"
    cfg_viv.parent.mkdir(parents=True, exist_ok=True)
    cfg_viv.write_text(json.dumps({
        "edicao_12": {
            "N": bonus_viv["N"],
            "denominador_R1": bonus_viv["denominador_R1"],
            "taxa": round(bonus_viv["taxa"], 4),
            "regra_aplicada": "R1 (multa ≤15%) + R2 (card.criado ≤ data_pag) + R3 (data_pag ≤ data_repasse)",
            "data_calculo": datetime.utcnow().date().isoformat(),
            "antes_count": int(len(bonus_viv["antes"])),
            "sem_card_count": int(len(bonus_viv["sem_card"])),
            "reativos_count": int(len(bonus_viv["reativos"])),
            "depois_count": int(len(bonus_viv["depois"])),
            "excluidos_rescisao_count": int(len(bonus_viv["excluidos_rescisao"])),
            "excluidos_valor0_count": int(len(bonus_viv["excluidos_valor0"])),
            "multiplos_count": int(len(bonus_viv["multiplos"])),
            "_aviso_drift_vs_baseline": (
                f"Drift de {bonus_viv['N'] - 61:+d} vs 11ª (N=61). Regra estrita R1+R2+R3 "
                "mantida desde a 11ª (confirmada pela gestora em 14/05/2026): bônus só conta "
                "se Vivianne abriu card ANTES ou NO MESMO DIA do pagamento (cobrança proativa), "
                "com multa ≤15% (exclui rescisões) e pagamento ≤ data de repasse. Variação vs "
                "11ª é drift natural da janela rolando."
            ),
        }
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    # 13ª Ed: "Cobrança antes do repasse" virou INDICADOR (peso 4) — precisa do
    # denominador, não só do N.
    dfs["_bonus_viv_tot"] = int(bonus_viv["denominador_R1"])
    # cobrados = boletos com cobrança PROATIVA (card antes/no dia do pagamento),
    # independentemente de o dinheiro ter chegado antes ou depois do repasse.
    dfs["_bonus_viv_cobrados"] = int(len(bonus_viv["antes"]) + len(bonus_viv["depois"]))
    atual = build_atual(dfs, ref=ref, bonus_n_vivianne=bonus_viv["N"])

    # TRAVA DE FONTE DEGRADADA (18/08/2026)
    # ─────────────────────────────────────────────────────────────────
    # carregar_distratos() e carregar_repasses() retornam {} em silêncio quando
    # o banco Imobiliar não responde (.env ausente, psycopg2 não instalado,
    # banco fora do ar). O cálculo então CAI NO FALLBACK e as notas mudam sem
    # que ninguém tenha mexido em regra:
    #   • sem data_distrato  → Rescisão Loc. (Natália e Gardênia) troca a data
    #                          de início pelo campo do Pipefy
    #   • sem data_repasse   → "Recebido antes do repasse" (Vivianne) cai na
    #                          data ESTIMADA, que erra em 67,5% dos casos
    # Aconteceu em 18/08/2026 numa rodada pelo bridge Linux (sem psycopg2):
    # Natália 5,93→6,01, Gardênia 5,42→5,51, Vivianne 6,91→6,88 — mudanças que
    # pareciam efeito de um ajuste nas vistorias e não eram.
    # Rodada degradada NÃO grava atual.json. Use --permitir-degradado só para
    # inspeção, ciente de que o resultado não pode ser publicado.
    degradado = []
    if not dfs.get("distratos"):
        degradado.append("data_distrato (Imobiliar) → Rescisão Loc. cai no campo do Pipefy")
    if not dfs.get("repasses"):
        degradado.append("data_retirada_repasse (Imobiliar) → Vivianne cai no repasse ESTIMADO")
    if degradado and "--permitir-degradado" not in argv:
        print("\n" + "=" * 70)
        print("❌ RODADA ABORTADA — fonte de dados indisponível")
        for d in degradado:
            print(f"   • {d}")
        print("\n   atual.json NÃO foi gravado (o anterior continua intacto).")
        print("   As notas desta rodada NÃO seriam comparáveis com a edição publicada.")
        print("   Rode pelo Windows, onde o banco Imobiliar responde.")
        print("=" * 70 + "\n")
        raise SystemExit(2)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    saida.write_text(json.dumps(atual, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"\n[run] gravado: {saida.relative_to(ROOT)}")
    print(f"[run] pessoas (pos, id, nota):")
    for p in atual["PESSOAS"]:
        print(f"       {p['pos']}. {p['id']:9} nota={p['nota']}  inds={p['inds']}  "
              f"pts={p['pts']}  bonus={p['bonus']}")


if __name__ == "__main__":
    main(sys.argv[1:])
