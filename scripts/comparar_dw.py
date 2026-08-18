"""
Fase 1 da migração — comparador API × banco `dw_trk`
====================================================

Roda os MESMOS indicadores duas vezes: uma com os DataFrames vindos da API do
Pipefy (fonte atual, em produção) e outra com os DataFrames vindos do `dw_trk`,
e diffa ok/tot indicador por indicador.

    python scripts/comparar_dw.py              # tudo
    python scripts/comparar_dw.py vistorias    # só um pipe (auditoria de colunas)

⚠️ RODAR NO MESMO DIA (Armadilha 9): a janela de 180 dias é rolante e o ETL
   recarrega a cada 6–12h. Comparar com dias de diferença gera divergência falsa.

⚠️ Divergência de DENOMINADOR: antes de acusar erro de fórmula, checar o
   `_etl_loaded_at` do card (Armadilha 10). O ETL atualiza só cards que mudaram,
   então um card pode estar dias atrasado mesmo com a tabela "carregada hoje".
   O relatório já mostra a carga mais antiga de cada pipe para ajudar nisso.

Nada aqui escreve no banco nem no painel — é só leitura e comparação.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.extract_pipefy import extract_pipe as extract_api      # noqa: E402
from pipeline.extract_dw import extract_pipe as extract_dw           # noqa: E402

PIPES = [
    "comercial_locacao", "cont_locacao", "cont_adm", "rescisao_adm", "rescisao_loc",
    "reparos", "renovacao", "inadimplencia", "backoffice", "dirf_darf",
    "vistorias", "contestacoes",
]


# ────────────────────────────────────────────────────────────────────
# Parte 1 — auditoria de COLUNAS (o extrator devolve o mesmo contrato?)
# ────────────────────────────────────────────────────────────────────

USAR_CACHE_API = True   # --api-fresh desliga (busca ao vivo, ~2s por página)


def auditar_colunas(pipe: str, verbose: bool = True) -> dict:
    a = extract_api(pipe, use_cache=USAR_CACHE_API, verbose=False)
    b = extract_dw(pipe, verbose=False)
    ca, cb = set(a.columns), set(b.columns) - {"_etl_card"}

    faltando = sorted(ca - cb)
    sobrando = sorted(cb - ca)

    print(f"\n{'='*68}\n{pipe}\n{'='*68}")
    print(f"  cards   API {len(a):>5}   banco {len(b):>5}   diff {len(b)-len(a):+d}")
    print(f"  colunas API {len(ca):>5}   banco {len(cb):>5}")
    if faltando:
        print(f"  ❌ FALTANDO no banco ({len(faltando)}):")
        for c in faltando:
            print(f"       {c}")
    if sobrando:
        print(f"  ➕ só no banco ({len(sobrando)}): {sobrando}")
    if not faltando and not sobrando:
        print("  ✓ contrato de colunas idêntico")

    # Valores, card a card, nas colunas comuns
    if "id" in a.columns and "id" in b.columns:
        ja = a.set_index(a["id"].astype(str))
        jb = b.set_index(b["id"].astype(str))
        comuns = sorted(set(ja.index) & set(jb.index))
        print(f"  cards em comum: {len(comuns)}"
              f"  (só na API: {len(set(ja.index)-set(jb.index))}"
              f" · só no banco: {len(set(jb.index)-set(ja.index))})")
        divergencias = []
        abertas = []
        for col in sorted(ca & cb):
            if col in ("URL", "_finished_at", "_done"):
                continue
            alvo = comuns
            # "Tempo total na fase X (dias)" de fase ABERTA é grandeza AO VIVO:
            # a API calcula no momento do fetch (que pode vir de cache) e o banco
            # no momento da leitura. Divergir pelo intervalo entre os dois é
            # esperado, não é erro. Comparamos só as fases já FECHADAS, onde o
            # valor é final e tem de bater exatamente.
            if col.startswith("Tempo total na fase ") and col.endswith(" (dias)"):
                fase = col[len("Tempo total na fase "):-len(" (dias)")]
                col_out = f"Última vez que saiu da fase {fase}"
                if col_out in ja.columns and col_out in jb.columns:
                    fechada = [c for c in comuns
                               if pd.notna(ja.loc[c, col_out]) and pd.notna(jb.loc[c, col_out])]
                    n_abertas = len(comuns) - len(fechada)
                    if n_abertas:
                        abertas.append((n_abertas, fase))
                    alvo = fechada
                    if not alvo:
                        continue
            va, vb = ja.loc[alvo, col], jb.loc[alvo, col]
            comuns_col = alvo
            if pd.api.types.is_datetime64_any_dtype(va) or pd.api.types.is_datetime64_any_dtype(vb):
                sa = pd.to_datetime(va, errors="coerce", utc=True)
                sb = pd.to_datetime(vb, errors="coerce", utc=True)
                dif = (sa.notna() | sb.notna()) & (
                    (sa.isna() != sb.isna())
                    | ((sa - sb).abs() > pd.Timedelta(seconds=90))
                )
            else:
                # Sentinela: em pandas, None != None dá True (NaN semantics).
                # Sem isso, colunas 100% vazias apareciam como 634 divergências.
                na = va.apply(_norm).where(lambda s: s.notna(), "\x00NULO")
                nb = vb.apply(_norm).where(lambda s: s.notna(), "\x00NULO")
                dif = na != nb
            n = int(dif.sum())
            if n:
                divergencias.append((n, col, [c for c in comuns_col if dif.get(c, False)][:3]))
        if abertas:
            for n_ab, fase in sorted(abertas, reverse=True):
                print(f"  ℹ️  fase {fase!r}: {n_ab} cards AINDA na fase — duração é "
                      "grandeza ao vivo, fora da comparação (por desenho)")
        if divergencias:
            print(f"  ⚠️  {len(divergencias)} colunas com valores divergentes:")
            for n, col, exemplos in sorted(divergencias, reverse=True):
                print(f"       {n:>4} cards  {col}")
                for cid in exemplos:
                    print(f"              card {cid}: API={ja.loc[cid, col]!r} "
                          f"banco={jb.loc[cid, col]!r}")
        else:
            print("  ✓ valores idênticos em todas as colunas comparáveis")

    # Armadilha 10 — quão velho está o card mais atrasado deste pipe
    if "_etl_card" in b.columns and len(b):
        carga = pd.to_datetime(b["_etl_card"], errors="coerce", utc=True)
        if carga.notna().any():
            print(f"  ETL: card mais recente {carga.max():%d/%m %H:%M} · "
                  f"mais ATRASADO {carga.min():%d/%m %H:%M}")
    return {"pipe": pipe, "faltando": faltando}


def _norm(v):
    """Normaliza para comparar: lista → string ordenada; NaN → None; strip."""
    if isinstance(v, list):
        return "|".join(sorted(str(x).strip() for x in v))
    if v is None:
        return None
    if isinstance(v, float) and pd.isna(v):
        return None
    if isinstance(v, float):
        return round(v, 6)
    s = str(v).strip()
    return s if s and s.lower() not in ("nan", "none", "nat") else None


# ────────────────────────────────────────────────────────────────────
# Parte 2 — diff dos INDICADORES (o número final bate?)
# ────────────────────────────────────────────────────────────────────

def _dfs(extrator) -> dict:
    from pipeline.extract_octadesk import extract_octadesk
    from pipeline.extract_imobiliar import extract_imobiliar
    if extrator is extract_api:
        dfs = {k: extrator(k, use_cache=USAR_CACHE_API, verbose=False) for k in PIPES}
    else:
        dfs = {k: extrator(k, verbose=False) for k in PIPES}
    dfs.update(extract_octadesk(verbose=False))
    dfs["imobiliar"] = extract_imobiliar(verbose=False)
    return dfs


def _indicadores(dfs: dict, ref: pd.Timestamp) -> dict[str, tuple]:
    """Roda os cálculos de Pipefy e devolve {nome_indicador: (ok, tot)}."""
    import calculate as C
    out: dict[str, tuple] = {}

    def add(res):
        for i in (res or {}).get("indicadores", []):
            if "★" in i["nome"]:
                continue
            out[i["nome"]] = (i.get("ok"), i.get("tot"))

    add(C.calc_caio_comercial_locacao(dfs["comercial_locacao"], ref=ref))
    add(C.calc_caio_contrato_locacao(dfs["comercial_locacao"], dfs["cont_locacao"], ref=ref))
    add(C.calc_caio_contrato_adm(dfs["cont_adm"], ref=ref))
    add(C.calc_caio_renovacao(dfs["renovacao"], ref=ref))
    add(C.calc_vivianne_contrato_adm(dfs["cont_adm"], ref=ref))
    add(C.calc_vivianne_rescisao_adm(dfs["rescisao_adm"], ref=ref))
    add(C.calc_vivianne_contrato_locacao(dfs["cont_locacao"], ref=ref))
    add(C.calc_vivianne_rescisao_locacao(dfs["rescisao_loc"], ref=ref))
    add(C.calc_vivianne_renovacao(dfs["renovacao"], ref=ref))
    add(C.calc_vivianne_inadimplencia(dfs["inadimplencia"], ref=ref))
    add(C.calc_vivianne_backoffice(dfs["backoffice"], ref=ref))
    for a in ("natalia", "gardenia"):
        pre = f"[{a}] "
        for res in (
            C.calc_assessora_contrato_adm(dfs["cont_adm"], a, ref=ref),
            C.calc_assessora_rescisao_adm(dfs["rescisao_adm"], a, ref=ref),
            C.calc_assessora_rescisao_locacao(dfs["rescisao_loc"], a, ref=ref),
            C.calc_assessora_reparos(dfs["reparos"], a, ref=ref),
            C.calc_assessora_renovacao(dfs["renovacao"], a, ref=ref),
            C.calc_assessora_backoffice(dfs["backoffice"], a, ref=ref),
            C.calc_assessora_dirf_darf(dfs["dirf_darf"], a, ref=ref),
        ):
            for i in (res or {}).get("indicadores", []):
                if "★" in i["nome"]:
                    continue
                out[pre + i["nome"]] = (i.get("ok"), i.get("tot"))
    add(C.calc_marinho_vistorias(dfs["vistorias"], ref=ref))
    add(C.calc_marinho_contestacoes(dfs["contestacoes"], ref=ref))
    return out


def comparar_indicadores() -> int:
    ref = pd.Timestamp.now(tz="UTC")
    print(f"\n{'#'*68}\n# DIFF DE INDICADORES — ref {ref:%d/%m/%Y %H:%M} UTC\n{'#'*68}")
    print("\n[1/2] carregando pela API do Pipefy…")
    ind_api = _indicadores(_dfs(extract_api), ref)
    print("[2/2] carregando pelo banco dw_trk…")
    ind_dw = _indicadores(_dfs(extract_dw), ref)

    nomes = sorted(set(ind_api) | set(ind_dw))
    iguais, difs = [], []
    for n in nomes:
        a, b = ind_api.get(n), ind_dw.get(n)
        (iguais if a == b else difs).append((n, a, b))

    print(f"\n✓ IDÊNTICOS: {len(iguais)} de {len(nomes)}")
    if difs:
        print(f"\n⚠️  DIVERGENTES: {len(difs)}")
        print(f"    {'indicador':<52} {'API':>10} {'banco':>10}")
        for n, a, b in difs:
            fa = f"{a[0]}/{a[1]}" if a else "—"
            fb = f"{b[0]}/{b[1]}" if b else "—"
            if not (a and b):
                marca = "----"
            elif a[0] == b[0]:
                marca = "den "          # só o denominador mudou
            elif (a[0] - b[0]) == (a[1] - b[1]):
                marca = "card"          # ok e tot variaram junto → card a mais/menos
            else:
                marca = "num!"          # proporção mudou → suspeita de regra
            print(f"  {marca} {n[:52]:<52} {fa:>10} {fb:>10}")
        print("\n  'den ' = só o denominador difere.")
        print("  'card' = ok e tot mudaram na MESMA medida → é card presente num lado")
        print("           e não no outro (atraso de ETL / cache), não erro de regra.")
        print("  'num!' = a PROPORÇÃO mudou → aí sim é candidato a erro de regra.")
        print("\n  Nos dois primeiros casos, checar o _etl_loaded_at do card "
              "(Armadilha 10)\n  ANTES de mexer em fórmula.")
    else:
        print("\n🎉 Todos os indicadores de Pipefy batem entre API e banco.")
    return len(difs)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--api-fresh"]
    if "--api-fresh" in sys.argv:
        USAR_CACHE_API = False
        print("⚠️  --api-fresh: buscando o lado da API AO VIVO (lento, ~2s/página).\n"
              "    Sem isso, o lado da API vem do cache de dados/raw e as diferenças\n"
              "    de contagem de cards e de timestamps recentes são só defasagem\n"
              "    entre o cache e a leitura do banco — não erro de extração.")
    if args:
        for p in args:
            auditar_colunas(p)
    else:
        for p in PIPES:
            auditar_colunas(p)
        comparar_indicadores()
