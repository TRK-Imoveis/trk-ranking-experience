"""
TRK Experience — Extração do banco `dw_trk` (Fase 1 da migração)
================================================================

Substituto DROP-IN do `pipeline/extract_pipefy.py`: devolve DataFrames com
EXATAMENTE as mesmas colunas, para que `calculate.py`, `imoveis_builder.py` e
`procrich_builder.py` não mudem uma linha.

    from pipeline.extract_dw import extract_pipe      # em vez de extract_pipefy
    df = extract_pipe("vistorias")

Contrato de saída (idêntico ao extrator da API):
    id · Título · Criado em · Fase atual · URL · _done · _finished_at · Responsáveis
    + uma coluna por campo listado em config/fields_map.json[<pipe>].fields
    + quatro colunas por fase listada em ...[<pipe>].phases:
        Primeira vez que entrou na fase <X>
        Última vez que entrou na fase <X>
        Última vez que saiu da fase <X>
        Tempo total na fase <X> (dias)

Fontes: pipefy_cards · pipefy_cards_fase_historico · pipefy_campos_custom.

────────────────────────────────────────────────────────────────────
ARMADILHAS RESPEITADAS AQUI (ver ESTADO_PROJETO_TRK.md)
────────────────────────────────────────────────────────────────────
5  — fuso: as colunas são timestamptz e a sessão do banco está em
     America/Sao_Paulo. NÃO subtraímos horas; só normalizamos para UTC,
     que é o que o extrator da API entrega (pd.to_datetime(..., utc=True)).
7  — performance: todo filtro é por `pipe_id` + igualdade exata em
     `field_label` / `phase_name` (índices). NUNCA função na coluna filtrada.
     `value_numeric` não é confiável → só usado para tipos numéricos, com
     fallback para `value_text`.
8  — selects guardam ID de opção sem tradução no banco. Ver OPCOES_POR_LABEL.
     Qualquer valor com cara de ID que não esteja no mapa vira aviso no console.
10 — o ETL atrasa POR CARD. `_etl_loaded_at` é exposto em `_etl_card` para o
     comparador distinguir "cálculo errado" de "dado ainda não chegou".

⚠️ O `label` do fields_map às vezes difere da chave (espaço no fim, caixa).
   Consultamos o banco pelo `label` e devolvemos a coluna com o nome da CHAVE.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
FIELDS_MAP_PATH = ROOT / "config" / "fields_map.json"

# Reaproveita o helper read-only já endurecido (set_session(readonly=True)).
_SANDBOX = ROOT / "trk-bd-sandbox"
if str(_SANDBOX) not in sys.path:
    sys.path.insert(0, str(_SANDBOX))
try:
    from db_connection import query as _query  # type: ignore
except Exception as exc:  # pragma: no cover
    raise ImportError(
        "extract_dw precisa de trk-bd-sandbox/db_connection.py e do .env com "
        "DB_HOST/DB_PORT/DB_NAME/DB_USER/DB_PASSWORD. "
        f"Erro original: {exc}"
    ) from exc


# ────────────────────────────────────────────────────────────────────
# Tradução de opções de select/multi_select (Armadilha 8)
# ────────────────────────────────────────────────────────────────────
# O banco guarda o ID da opção e NÃO existe tabela de tradução
# (pipefy_definicoes_campos não cobre esses campos). Mapeamento descoberto
# cruzando com o XLSX exportado — 8/8 consistentes na validação de 31/07.
_OPCOES_BRUTO: dict[str, dict[str, str]] = {
    "Tipo de vistoria": {
        "307759431": "Entrada",
        "307759437": "Saída",
        "307796563": "Conferência",
        # Identificado em 12/08/2026 comparando com a API (era o ID sem tradução):
        "307759441": "Proprietário",
    },
}

# ⚠️ O banco junta multi-valores com vírgula ("307759437, 307796563"), não como
# JSON. Descoberto na 1ª comparação com a API em 12/08/2026.

_RE_ID_OPCAO = re.compile(r"^\d{6,}$")
_AVISOS: set[str] = set()

# Indexado por rótulo normalizado (strip + casefold).
OPCOES_POR_LABEL: dict[str, dict[str, str]] = {
    k.strip().casefold(): v for k, v in _OPCOES_BRUTO.items()
}


def _avisar(msg: str) -> None:
    """Avisa uma vez por mensagem (evita poluir o console em loop de cards).
    NÃO é silenciado por verbose=False: aviso engolido é bug que passa batido."""
    if msg not in _AVISOS:
        _AVISOS.add(msg)
        print(f"   ⚠️  {msg}")


def _norm_label(s: Any) -> str:
    """Normaliza rótulo p/ casar chave do fields_map com field_label do banco.
    Existe porque o fields_map guarda 'vistoria iniciada em ' (com espaço no fim)
    e o banco guarda 'vistoria iniciada em' — e há casos de caixa diferente
    ('Criar Card de Vistoria Técnica' × 'Criar card de vistoria técnica')."""
    return str(s or "").strip().casefold()


def _candidatos_label(chave: str, info: dict) -> list[str]:
    """Todas as grafias plausíveis do rótulo, para consultar o banco."""
    label = info.get("label", chave)
    out: list[str] = []
    for c in (label, str(label).strip(), chave, str(chave).strip()):
        if c and c not in out:
            out.append(c)
    return out


def _load_fields_map() -> dict[str, dict]:
    return json.loads(FIELDS_MAP_PATH.read_text(encoding="utf-8"))


def _vazio(v: Any) -> bool:
    """None, string vazia ou NaN. Existe porque pandas troca None por NaN em
    colunas numéricas, e `nan not in (None, "")` é True — o que fazia
    `float(nan)` passar como valor válido."""
    if v is None or v == "":
        return True
    try:
        return bool(pd.isna(v))
    except (TypeError, ValueError):
        return False


_RE_SO_DATA = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TZ_BR = "America/Sao_Paulo"


def _titulos_de_cards(ids: list[str]) -> dict[str, str]:
    """card_id → título, para resolver campos `connector`.
    O banco guarda o card_id do destino; a API devolve o título. Os destinos
    moram em outros pipes (ex.: 'BD - Imóveis'), por isso a consulta é por
    card_id (indexado) sem filtro de pipe."""
    ids = [i for i in ids if i]
    if not ids:
        return {}
    d = _query(
        "SELECT card_id, title FROM pipefy_cards WHERE card_id = ANY(%s)",
        (sorted(set(ids)),),
    )
    return {str(r["card_id"]): r["title"] for _, r in d.iterrows()}


def _data_campo(linha: pd.Series, tipo: str = "") -> Any:
    """
    Data de um campo date/datetime/due_date. O tratamento DEPENDE DO TIPO.

    Como a API se comporta (extract_pipefy._extract_field_value):
      • date               → `date_value or datetime_value`
      • due_date, datetime → `datetime_value`

    Consequência medida em 12/08/2026, campo por campo:
      • `date`     → o Pipefy tem `date_value` = '2024-09-25' e
        `pd.to_datetime(utc=True)` dá meia-noite **UTC** — igual ao `value_date`
        do banco. NÃO converter (converter criava 943 divergências no
        'Vencimento 1º Boleto:' que antes batiam).
      • `due_date` → vem do `datetime_value`, o instante real. Quando o usuário
        preencheu só a data, esse instante é meia-noite de **BRASÍLIA**
        (03:00 UTC). Aí sim a conversão de fuso é necessária.

    ⚠️ LACUNA L5 DO ETL (12/08/2026): quando o campo tem HORA no Pipefy, o banco
    guarda só a data — `value_text` vem '2024-10-31' e `value_date` meia-noite.
    A hora NÃO é recuperável (`value_json` e `value_numeric` nulos). Isso quebra
    'Rescisão Loc. — Boleto prop <24h', que usa 'Data do recebimento das chaves:'
    como início de uma meta de 24h: truncar para meia-noite empurra o tempo em
    até 24h. Enquanto o ETL não persistir o datetime completo, esse indicador
    não migra.
    """
    raw = linha.get("value_text")
    if not _vazio(raw):
        txt = str(raw).strip()
        if not _RE_SO_DATA.match(txt):
            # value_text com hora é a fonte mais fiel que existe no banco
            ts = pd.to_datetime(txt, errors="coerce", utc=True)
            if not pd.isna(ts):
                return ts
        elif (tipo or "").lower() in ("due_date", "datetime"):
            # Campo cuja API entrega `datetime_value` (instante real), mas o banco
            # só tem a data → a HORA foi truncada pelo ETL (lacuna L5).
            # Assumimos meia-noite de Brasília, que é como o Pipefy grava quando
            # o usuário preenche só a data. É APROXIMAÇÃO: medido em 12/08/2026,
            # acerta 212 cards de 'Data de vencimento' e erra ~51 de
            # 'Data do recebimento das chaves:' (onde o instante era meia-noite
            # UTC). Não há regra que acerte os dois — o dado foi perdido.
            _avisar(
                "L5: campo de data com hora truncada pelo ETL — valor APROXIMADO "
                "(meia-noite de Brasília). Não confiar em indicador de meta curta "
                "que dependa dele (ex.: Rescisão Loc. Boleto prop <24h)."
            )
            return pd.Timestamp(txt, tz=TZ_BR).tz_convert("UTC")
    return _to_utc(linha.get("value_date"))


def _to_utc(v: Any) -> Any:
    """Normaliza para datetime tz-aware em UTC — igual ao extrator da API.
    NÃO aplicar offset manual: o banco já entrega timestamptz (Armadilha 5)."""
    if v is None or v is pd.NaT or (isinstance(v, float) and pd.isna(v)):
        return pd.NaT
    ts = pd.to_datetime(v, errors="coerce", utc=True)
    return ts


def _json_lista(raw: Any) -> list[str]:
    """assignee_select: value_text vem como JSON '["Nome "]'."""
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return []
    if isinstance(raw, list):
        return [str(x) for x in raw if x not in (None, "")]
    txt = str(raw).strip()
    if not txt:
        return []
    try:
        parsed = json.loads(txt)
    except (ValueError, TypeError):
        return [txt]
    if isinstance(parsed, list):
        out = []
        for x in parsed:
            if isinstance(x, dict):
                nome = x.get("name") or x.get("nome")
                if nome:
                    out.append(str(nome))
            elif x not in (None, ""):
                out.append(str(x))
        return out
    return [str(parsed)] if parsed else []


def _traduzir(label: str, raw: Any) -> Any:
    """multi_select / select: traduz IDs de opção quando necessário."""
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return None
    mapa = OPCOES_POR_LABEL.get(_norm_label(label)) or OPCOES_POR_LABEL.get(label, {})
    brutos = _json_lista(raw) or [str(raw).strip()]
    # O banco junta multi-valores com vírgula, não como JSON — precisa abrir.
    abertos: list[str] = []
    for b in brutos:
        abertos.extend(p for p in str(b).split(",") if p.strip())
    brutos = abertos or brutos
    saida: list[str] = []
    for b in brutos:
        b = b.strip()
        if not b:
            continue
        if b in mapa:
            saida.append(mapa[b])
        elif _RE_ID_OPCAO.match(b):
            _avisar(
                f"campo {label!r}: opção {b!r} sem tradução em OPCOES_POR_LABEL "
                "— valor mantido cru (vai divergir do XLSX)"
            )
            saida.append(b)
        else:
            saida.append(b)  # banco já devolveu texto limpo
    # o extrator da API junta multi_select com ', '
    return ", ".join(saida) if saida else None


def _valor_campo(linha: pd.Series, tipo: str, label: str) -> Any:
    t = (tipo or "").lower()
    if t in ("datetime", "due_date", "date"):
        return _data_campo(linha, t)
    if t == "assignee_select":
        # A API devolve None quando o campo não existe no card e lista quando
        # existe. Aqui só chegamos com linha existente → lista (pode ser vazia).
        return _json_lista(linha.get("value_text"))
    if t in ("multi_select", "label_select") or _norm_label(label) in OPCOES_POR_LABEL:
        return _traduzir(label, linha.get("value_text"))
    if t in ("number", "currency", "id"):
        # value_text PRIMEIRO: `value_numeric` é numeric(…,4) e ARREDONDA
        # (Área útil 1.06067 virava 1.0607). Além de não ser confiável para
        # preenchimento, perde precisão. Fallback para value_numeric.
        raw = linha.get("value_text")
        if not _vazio(raw):
            try:
                f = float(raw)
                if not pd.isna(f):
                    return f
            except (TypeError, ValueError):
                pass
        v = linha.get("value_numeric")
        if not _vazio(v):
            return float(v)
        return None if _vazio(raw) else raw
    valor = linha.get("value_text")
    # Rede de segurança: select/radio devolvendo ID em vez de rótulo
    if isinstance(valor, str) and _RE_ID_OPCAO.match(valor.strip()) and t in (
        "select", "radio_horizontal", "radio_vertical", "label_select"
    ):
        _avisar(
            f"campo {label!r} ({t}) devolveu o que parece ser ID de opção "
            f"({valor!r}) — conferir antes de confiar no número"
        )
    return valor


# ────────────────────────────────────────────────────────────────────
# Extração
# ────────────────────────────────────────────────────────────────────

def extract_pipe(pipe_key: str, *, use_cache: bool = True, verbose: bool = True) -> pd.DataFrame:
    """
    Extrai um pipe do `dw_trk` no formato do extrator da API.

    `use_cache` existe só para manter a assinatura compatível com
    extract_pipefy.extract_pipe — o banco não usa cache local.
    """
    fmap = _load_fields_map()
    if pipe_key not in fmap:
        raise KeyError(f"pipe '{pipe_key}' não está em config/fields_map.json")
    cfg = fmap[pipe_key]
    pipe_id = str(cfg["pipe_id"])
    campos = cfg.get("fields") or {}
    fases = list((cfg.get("phases") or {}).keys())

    if verbose:
        print(f"[dw] {pipe_key} (pipe {pipe_id}) — "
              f"{len(campos)} campos, {len(fases)} fases")

    # ── 1) cards
    cards = _query(
        """
        SELECT card_id, title, created_at, current_phase_name, url, done,
               assignee_names, _etl_loaded_at
        FROM pipefy_cards
        WHERE pipe_id = %s
        """,
        (pipe_id,),
    )
    if cards.empty:
        if verbose:
            print(f"   (nenhum card no banco para o pipe {pipe_id})")
        return pd.DataFrame()

    df = pd.DataFrame({
        "id": cards["card_id"].astype(str),
        "Título": cards["title"],
        "Criado em": cards["created_at"].apply(_to_utc),
        "Fase atual": cards["current_phase_name"],
        "URL": cards["url"],
        "_done": cards["done"].fillna(False).astype(bool),
        "_finished_at": pd.NaT,   # não existe no dw_trk; não é consumido pelo cálculo
        "Responsáveis": cards["assignee_names"].apply(_json_lista),
        "_etl_card": cards["_etl_loaded_at"],  # Armadilha 10
    })
    df.index = cards["card_id"].astype(str)

    # ── 2) campos custom (igualdade exata no field_label — Armadilha 7)
    #    Consulta pelo LABEL, devolve com o nome da CHAVE.
    if campos:
        labels = sorted({c for chave, info in campos.items()
                         for c in _candidatos_label(chave, info)})
        cc = _query(
            """
            SELECT card_id, field_label, value_text, value_numeric, value_date
            FROM pipefy_campos_custom
            WHERE pipe_id = %s AND field_label = ANY(%s)
            """,
            (pipe_id, labels),
        )
        cc["_lbl"] = cc["field_label"].map(_norm_label)
        for chave, info in campos.items():
            label = info.get("label", chave)
            tipo = info.get("type", "")
            alvos = {_norm_label(c) for c in _candidatos_label(chave, info)}
            sub = cc[cc["_lbl"].isin(alvos)]
            if sub.empty:
                df[chave] = None
                _avisar(f"campo {chave!r} (label {label!r}) sem nenhum valor no banco "
                        f"— indicador que dependa dele vai zerar")
                continue
            achados = sorted(set(sub["field_label"]))
            if label not in achados:
                _avisar(f"campo {chave!r}: fields_map diz label {label!r}, "
                        f"banco tem {achados!r} — casado por normalização")
            # Um card pode ter o mesmo label mais de uma vez → mantém o último
            sub = sub.drop_duplicates(subset="card_id", keep="last")
            # connector: o banco guarda o card_id do destino; a API devolve o
            # TÍTULO em JSON. Resolvemos via pipefy_cards para o `Imóvel ` voltar
            # a conter "IM890 | ..." — de onde calculate.py extrai o IM por regex.
            if tipo == "connector":
                alvo_ids = sorted({
                    p.strip() for v in sub["value_text"].dropna()
                    for p in str(v).split(",") if p.strip()
                })
                titulos = _titulos_de_cards(alvo_ids)
                valores = {}
                for _, r in sub.iterrows():
                    ids = [p.strip() for p in str(r.get("value_text") or "").split(",") if p.strip()]
                    nomes = [titulos.get(i, i) for i in ids]
                    valores[str(r["card_id"])] = (
                        json.dumps(nomes, ensure_ascii=False) if nomes else None)
            else:
                valores = {
                    str(r["card_id"]): _valor_campo(r, tipo, label)
                    for _, r in sub.iterrows()
                }
            df[chave] = df.index.map(lambda cid: valores.get(cid))
            if tipo in ("datetime", "date", "due_date"):
                df[chave] = pd.to_datetime(df[chave], errors="coerce", utc=True)

    # ── 3) histórico de fases — casado por phase_id (imune a renomeação!)
    #    A fase 'Cobrança (inicial)' do fields_map está como 'Cobrança inicial'
    #    no banco: casar por nome perdia 833 cards em silêncio (12/08/2026).
    if fases:
        ids_fase = {str((cfg["phases"][f] or {}).get("id")): f for f in fases
                    if (cfg["phases"][f] or {}).get("id")}
        fh = _query(
            """
            SELECT card_id, phase_id, phase_name, first_time_in, last_time_in,
                   last_time_out, duration_s
            FROM pipefy_cards_fase_historico
            WHERE pipe_id = %s AND phase_id = ANY(%s)
            """,
            (pipe_id, sorted(ids_fase)),
        )
        fh["_fase"] = fh["phase_id"].astype(str).map(ids_fase)
        for fase in fases:
            sub = fh[fh["_fase"] == fase].drop_duplicates(subset="card_id", keep="last")
            if sub.empty:
                _avisar(f"fase {fase!r} (id {(cfg['phases'][fase] or {}).get('id')!r}) "
                        f"sem NENHUM registro no banco — indicador que dependa dela vai zerar")
            else:
                nomes_banco = sorted(set(sub["phase_name"]))
                if fase not in nomes_banco:
                    _avisar(f"fase {fase!r}: banco chama {nomes_banco!r} "
                            f"— casado por phase_id (renomeação no Pipefy)")
            idx = sub["card_id"].astype(str)
            m_in = dict(zip(idx, sub["first_time_in"]))
            m_lin = dict(zip(idx, sub["last_time_in"]))
            m_out = dict(zip(idx, sub["last_time_out"]))
            m_dur = dict(zip(idx, sub["duration_s"]))
            df[f"Primeira vez que entrou na fase {fase}"] = df.index.map(
                lambda cid: _to_utc(m_in.get(cid)))
            df[f"Última vez que entrou na fase {fase}"] = df.index.map(
                lambda cid: _to_utc(m_lin.get(cid)))
            df[f"Última vez que saiu da fase {fase}"] = df.index.map(
                lambda cid: _to_utc(m_out.get(cid)))
            # ⚠️ `duration_s` de fase ABERTA (sem last_time_out) é um RETRATO do
            # momento da carga do ETL daquele card — a API calcula ao vivo.
            # Sem este ajuste o tempo vem subestimado pelo tanto que o ETL
            # está atrasado (medido: 7,6 dias em cards carregados em 04/08).
            # Descoberto na 1ª comparação API × banco, 12/08/2026.
            agora = pd.Timestamp.now(tz="UTC")
            etl = {cid: _to_utc(v) for cid, v in zip(df.index, df["_etl_card"])}

            def _dur(cid: str):
                d = m_dur.get(cid)
                if d is None or pd.isna(d):
                    return None
                dias = d / 86400.0
                if pd.isna(_to_utc(m_out.get(cid))):          # ainda na fase
                    t = etl.get(cid)
                    if t is not None and not pd.isna(t):
                        dias += max(0.0, (agora - t).total_seconds() / 86400.0)
                return dias

            df[f"Tempo total na fase {fase} (dias)"] = df.index.map(_dur)
            # dtype: sem isto a coluna vira `object` quando tudo é NaT, e
            # `serie_datetime - serie_object` estoura em TypeError no calculate.
            for pref in ("Primeira vez que entrou na fase ",
                         "Última vez que entrou na fase ",
                         "Última vez que saiu da fase "):
                c = f"{pref}{fase}"
                df[c] = pd.to_datetime(df[c], errors="coerce", utc=True)

    df = df.reset_index(drop=True)
    if verbose:
        print(f"   ✓ {len(df)} cards, {len(df.columns)} colunas")
    return df


def extract_all(*, use_cache: bool = True, verbose: bool = True) -> dict[str, pd.DataFrame]:
    return {k: extract_pipe(k, use_cache=use_cache, verbose=verbose)
            for k in _load_fields_map()}


if __name__ == "__main__":
    key = sys.argv[1] if len(sys.argv) > 1 else "vistorias"
    d = extract_pipe(key)
    print(f"\n{key}: {d.shape[0]} linhas × {d.shape[1]} colunas")
    print("\nColunas:")
    for c in d.columns:
        print("  ", c)
