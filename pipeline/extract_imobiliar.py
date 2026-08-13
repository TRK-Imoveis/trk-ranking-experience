"""
TRK Experience — Extração Imobiliar (LOCAL)
===========================================

Lê os 3 CSVs do sistema Imobiliar em `dados/csv/`:
    Relatorio_de_Boletos_Quitados.csv
    Relatorio_De_proprietarios.csv
    Relatorio_de_Imoveis.csv

Encoding: latin-1, separador: ';' (padrão do exportador Imobiliar).

Quando faltar qualquer um dos 3, `calcular_bonus_inadimplencia` retorna 0 e loga "SKIP".

Regra do bônus Inadimplência (manual v4 §4.2):
    N = boletos com (Multa.Adm > 0 OU Juros.Adm > 0)
        E Data Pag. ≤ data repasse do proprietário
        E IM com card no pipe Inadimplência
        E proprietário com `dia_pag` cadastrado.

A implementação plena do cálculo de N depende de:
- conhecer os nomes exatos das colunas dos 3 CSVs (variáveis entre exports);
- ter o df_inadimplencia do Pipefy para cruzar com IMs.

Por isso `calcular_bonus_inadimplencia` é provisório: se algum CSV faltar → 0.
Quando o usuário entregar o 1º conjunto de CSVs, completar a lógica usando este módulo.
"""
from __future__ import annotations

import sys
import zoneinfo
from pathlib import Path
from typing import Optional

import pandas as pd

TZ_BSB = zoneinfo.ZoneInfo("America/Sao_Paulo")

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent
CSV_DIR = ROOT / "dados" / "csv"

FILES = {
    "boletos":       "Relatorio_de_Boletos_Quitados.csv",
    "proprietarios": "Relatorio_De_proprietarios.csv",
    "imoveis":       "Relatorio_de_Imoveis.csv",
}


def _load_csv(name: str, *, verbose: bool = True) -> pd.DataFrame:
    path = CSV_DIR / name
    if not path.exists():
        if verbose:
            print(f"[imobiliar] SKIP — arquivo ausente: dados/csv/{name}")
        return pd.DataFrame()
    try:
        df = pd.read_csv(path, encoding="latin-1", sep=";")
        if verbose:
            print(f"  [imobiliar] {name}: {df.shape[0]} linhas × {df.shape[1]} colunas")
        return df
    except Exception as e:
        print(f"  [imobiliar] ERRO lendo {name}: {e}")
        return pd.DataFrame()


def _load_proprietarios(*, verbose: bool = True) -> pd.DataFrame:
    """
    Parser custom para `Relatorio_De_proprietarios.csv` do Imobiliar Connect.

    O arquivo é um relatório de impressão multi-record (não uma tabela plana). 5 tipos de linha:
    - Page_Footer / Page_Header — descartar (boilerplate do relatório)
    - detNomeProp_Detail (7 campos): tag, id, CPF/CNPJ, data_nasc, dia_pag, telefone, nome
    - detBanco_Detail (6 campos)   — descartar (não usado no bônus)
    - detEnder_Detail (7 campos)   — descartar (não usado no bônus)

    Extrai apenas (id, dia_pag, nome) das linhas `detNomeProp_Detail` e filtra
    proprietários com `dia_pag` numérico preenchido — regra do manual v4 §4.2.
    """
    import csv
    path = CSV_DIR / FILES["proprietarios"]
    if not path.exists():
        if verbose:
            print(f"[imobiliar] SKIP — arquivo ausente: dados/csv/{FILES['proprietarios']}")
        return pd.DataFrame()

    rows: list[tuple[str, str, str]] = []
    total_prop = 0
    try:
        with open(path, encoding="latin-1", newline="") as f:
            reader = csv.reader(f, delimiter=";")
            for r in reader:
                if not r or r[0] != "detNomeProp_Detail":
                    continue
                total_prop += 1
                # padding caso a linha venha mais curta que esperado
                while len(r) < 7:
                    r.append("")
                rows.append((r[1].strip(), r[4].strip(), r[6].strip()))
    except Exception as e:
        print(f"  [imobiliar] ERRO parseando proprietarios.csv: {e}")
        return pd.DataFrame()

    df = pd.DataFrame(rows, columns=["id_proprietario", "dia_pag", "nome"])
    # filtra dia_pag numérico
    df["dia_pag_num"] = pd.to_numeric(df["dia_pag"], errors="coerce")
    df_ok = df.dropna(subset=["dia_pag_num"]).copy()
    df_ok["dia_pag"] = df_ok["dia_pag_num"].astype(int)
    df_ok = df_ok.drop(columns=["dia_pag_num"]).reset_index(drop=True)

    if verbose:
        print(f"  [imobiliar] proprietarios.csv: {len(df_ok)} com dia_pag cadastrado "
              f"de {total_prop} total no relatório")
    return df_ok


def _parse_brl(s) -> float:
    """Converte '1.234,56' (formato BR) para float. Retorna 0.0 se inválido."""
    if s is None:
        return 0.0
    txt = str(s).strip().strip('"').replace(".", "").replace(",", ".")
    try:
        return float(txt)
    except ValueError:
        return 0.0


def _parse_date_br(s) -> Optional[pd.Timestamp]:
    """Converte 'DD/MM/YYYY [letra opcional]' para Timestamp tz-aware UTC."""
    if not s:
        return None
    txt = str(s).strip().strip('"').split()[0]  # remove sufixo 'N','E' etc.
    try:
        return pd.to_datetime(txt, format="%d/%m/%Y", utc=True)
    except (ValueError, TypeError):
        return None


def _load_boletos(*, verbose: bool = True) -> pd.DataFrame:
    """
    Parser custom para Relatorio_de_Boletos_Quitados.csv (multi-record).

    Schema de IsBandDet_Detail (19 campos, 0-indexed):
      [0] tag = "IsBandDet_Detail"
      [1] Cd.Imóvel              (int após strip)
      [2] Número do boleto       (string)
      [3] Data Pag. + sufixo     ("14/11/2025 N")
      [4] vazio
      [5] Mes Ref                ("10/2025")
      [6] Valor                  (BRL)
      [7..11] Multa.Adm, Juros.Adm, outros encargos/descontos (BRL)
      [18] Total recebido        (BRL)

    Análise empírica (1912 boletos):
      pos 9 tem 146 valores > 0 → Multa.Adm (próximo da baseline N=124)
      pos 10 tem 12 valores > 0 → Juros.Adm
      Outras posições raras ou zeros.
    """
    import csv
    path = CSV_DIR / FILES["boletos"]
    if not path.exists():
        if verbose:
            print(f"[imobiliar] SKIP — arquivo ausente: dados/csv/{FILES['boletos']}")
        return pd.DataFrame()
    rows = []
    with open(path, encoding="latin-1", newline="") as f:
        reader = csv.reader(f, delimiter=";")
        for r in reader:
            if not r or r[0] != "IsBandDet_Detail":
                continue
            while len(r) < 19:
                r.append("")
            rows.append({
                "cd_imovel": r[1].strip(),
                "num_boleto": r[2].strip(),
                "data_pag": _parse_date_br(r[3]),
                "mes_ref": r[5].strip().strip('"'),
                "valor": _parse_brl(r[6]),
                "multa_adm": _parse_brl(r[9]),
                "juros_adm": _parse_brl(r[10]),
                "total": _parse_brl(r[18]),
            })
    df = pd.DataFrame(rows)
    if verbose:
        com_encargo = ((df["multa_adm"] > 0) | (df["juros_adm"] > 0)).sum()
        print(f"  [imobiliar] boletos: {len(df)} total · {int(com_encargo)} com encargo (Multa>0 OU Juros>0)")
    return df


def _load_imoveis(*, verbose: bool = True) -> pd.DataFrame:
    """
    Parser custom para Relatorio_de_Imoveis.csv (multi-record).

    Schema de IsBandDetImovel_Detail (9 campos):
      [0] tag
      [1] Cd.Imóvel
      [2] Proprietário ("0000105-TERRAFORTE...") → extrair id_proprietario antes do '-'
      ...
    """
    import csv
    path = CSV_DIR / FILES["imoveis"]
    if not path.exists():
        if verbose:
            print(f"[imobiliar] SKIP — arquivo ausente: dados/csv/{FILES['imoveis']}")
        return pd.DataFrame()
    rows = []
    with open(path, encoding="latin-1", newline="") as f:
        reader = csv.reader(f, delimiter=";")
        for r in reader:
            if not r or r[0] != "IsBandDetImovel_Detail":
                continue
            while len(r) < 9:
                r.append("")
            prop_raw = r[2].strip()
            id_prop = prop_raw.split("-", 1)[0].strip() if "-" in prop_raw else prop_raw
            rows.append({
                "cd_imovel": r[1].strip(),
                "id_proprietario": id_prop,
                "tipo": r[3].strip(),
                "status": r[4].strip(),
                "situacao": r[5].strip(),
                "endereco": r[8].strip() if len(r) > 8 else "",
            })
    df = pd.DataFrame(rows)
    if verbose:
        print(f"  [imobiliar] imoveis: {len(df)} cadastrados")
    return df


def extract_imobiliar(*, verbose: bool = True) -> dict[str, pd.DataFrame]:
    """Retorna {"boletos", "proprietarios", "imoveis"} com DataFrames (empty se ausente)."""
    if not CSV_DIR.exists():
        if verbose:
            print(f"[imobiliar] pasta dados/csv/ não existe — SKIP completo")
        return {k: pd.DataFrame() for k in FILES}
    return {
        "boletos":       _load_boletos(verbose=verbose),
        "proprietarios": _load_proprietarios(verbose=verbose),
        "imoveis":       _load_imoveis(verbose=verbose),
    }


def _data_repasse(mes_ref: str, dia_pag: int) -> Optional[pd.Timestamp]:
    """
    [Legacy — usado pela versão antiga sem cards.]
    Data de repasse derivada SÓ do mes_ref. Mantido para compat reversa nos scripts
    de diagnóstico. A versão de produção (`calcular_bonus_inadimplencia`) usa o
    Vencimento_1º_Boleto do CARD do pipe — fonte de verdade do vencimento real.
    """
    if not mes_ref or "/" not in mes_ref:
        return None
    try:
        m, y = mes_ref.split("/")
        m, y = int(m), int(y)
    except ValueError:
        return None
    if m == 12:
        m_rep, y_rep = 1, y + 1
    else:
        m_rep, y_rep = m + 1, y
    import calendar
    last_day = calendar.monthrange(y_rep, m_rep)[1]
    d = min(dia_pag, last_day)
    return pd.Timestamp(year=y_rep, month=m_rep, day=d, tz="UTC")


def _data_repasse_from_card(venc_1o_boleto: pd.Timestamp, dia_pag: int) -> pd.Timestamp:
    """
    Data de repasse derivada do Vencimento do boleto (fonte: card do pipe).
    Mesmo mês do vencimento, no dia_pag do proprietário. Clamp para último dia do mês.

    Ex: venc=2026-04-10, dia_pag=20 → 2026-04-20.
    """
    import calendar
    last_day = calendar.monthrange(venc_1o_boleto.year, venc_1o_boleto.month)[1]
    d = min(dia_pag, last_day)
    return pd.Timestamp(year=venc_1o_boleto.year, month=venc_1o_boleto.month, day=d,
                        tz=venc_1o_boleto.tz if venc_1o_boleto.tz else "UTC")


def _mes_seguinte(mes_ref: str) -> Optional[tuple[int, int]]:
    """'10/2025' → (11, 2025); '12/2025' → (1, 2026). None se inválido."""
    if not mes_ref or "/" not in mes_ref:
        return None
    try:
        m, y = mes_ref.split("/")
        m, y = int(m), int(y)
    except ValueError:
        return None
    return (1, y + 1) if m == 12 else (m + 1, y)


def _parse_im_titulo(t: str) -> Optional[int]:
    """
    Extrai o IM do título de um card do pipe Inadimplência.
    Aceita: 'IM1841', 'IM47 - DANILO…', '1055.0', '1353/3', '47/2 NOME'.
    Descarta: 'P6409 - …' (id de proprietário).
    """
    import re as _re
    s = str(t).strip()
    if s.upper().startswith("P"):
        return None
    # IM-prefix com sufixo opcional /N
    m = _re.match(r"IM\s*(\d+)", s, _re.IGNORECASE)
    if m:
        return int(m.group(1))
    # Numérico puro ou <num>/<n>
    m = _re.match(r"(\d+)(?:/\d+|\.0)?", s)
    if m:
        return int(m.group(1))
    return None



# ────────────────────────────────────────────────────────────────────
# Data de entrega das chaves — fonte Imobiliar (13ª Ed, 13/08/2026)
# ────────────────────────────────────────────────────────────────────
def carregar_distratos(*, verbose: bool = True) -> dict[int, pd.Timestamp]:
    """
    `codigo_imovel` → `data_distrato` da tabela `imobiliar_contratos_loc` do dw_trk.

    POR QUE ESSA COLUNA E NÃO O CAMPO DO PIPEFY
    ------------------------------------------
    O indicador "Boleto prop" mede o tempo entre a ENTREGA DAS CHAVES e o
    levantamento das taxas proporcionais. O campo `Data do recebimento das
    chaves:` do Pipefy é digitado à mão e erra com frequência (IM344, IM1742,
    IM1783 e IM1785 têm data posterior ao próprio levantamento).

    No Imobiliar existem dois campos e é fácil trocá-los:
      • "Chaves" (`dataentrega`) → quando a assessora SENTOU para registrar.
        Se ela recebe hoje e cadastra amanhã, esse campo traz amanhã. Usar
        aqui deixaria o indicador CIRCULAR (mede-se contra o próprio registro).
      • "Encerramento" (`data_distrato`) → a data em que as chaves foram de
        fato entregues. É a que alimenta o cálculo do boleto final, então a
        equipe tem incentivo real de preenchê-la certo.  ← é esta.

    Retorna {} (silenciosamente) se o banco não estiver acessível — o cálculo
    então cai no encadeamento antigo (campo Pipefy → fase CHAVES RECEBIDAS →
    saída de Vistoria recebida / Agendamento).
    """
    sandbox = Path(__file__).resolve().parent.parent / "trk-bd-sandbox"
    if str(sandbox) not in sys.path:
        sys.path.insert(0, str(sandbox))
    try:
        from db_connection import query as _query  # type: ignore
        df = _query(
            "SELECT codigo_imovel, max(data_distrato) AS data_distrato "
            "FROM imobiliar_contratos_loc "
            "WHERE data_distrato IS NOT NULL AND codigo_imovel IS NOT NULL "
            "GROUP BY codigo_imovel"
        )
    except Exception as exc:  # banco fora do ar, .env ausente, etc.
        if verbose:
            print(f"[imobiliar] data_distrato indisponível ({exc.__class__.__name__}) "
                  f"— Boleto prop/final cai no campo do Pipefy")
        return {}

    fora = {}
    for _, r in df.iterrows():
        try:
            im = int(r["codigo_imovel"])
        except (TypeError, ValueError):
            continue
        d = pd.Timestamp(r["data_distrato"])
        if pd.isna(d):
            continue
        # Meia-noite de Brasília, em UTC (as colunas do pipeline são tz-aware UTC).
        d = d.normalize()
        if d.tzinfo is None:
            d = d.tz_localize(TZ_BSB)
        fora[im] = d.tz_convert("UTC")
    if verbose:
        print(f"[imobiliar] data_distrato: {len(fora)} imóveis")
    return fora


def carregar_repasses(*, verbose: bool = True) -> dict[tuple[int, str], pd.Timestamp]:
    """
    (codigo_imovel, competencia 'MM/AAAA') → `data_retirada_repasse` do `dw_trk`.

    É a data em que o PROPRIETÁRIO efetivamente recebeu — a coluna "Pagto Prop"
    da tela de Boletos do Imobiliar. Confirmada pela gestora em 13/08/2026 com o
    IM87 (CLN 211 BL D, 216): boleto pago 09/07/2026, repasse 30/07/2026, e o
    Demonstrativo de competência 06/2026 traz a linha ALUGUEL de 09/07.

    POR QUE ISSO IMPORTA
    --------------------
    Até 13/08/2026 a regra R3 usava uma data ESTIMADA:
        mês do "Vencimento 1º Boleto" do card + dia_pag do proprietário.
    O repasse real anda para o dia útil anterior quando o dia cai em fim de
    semana. No próprio IM87 (dia_pag cadastrado = 30) os repasses foram
    30/07 · 30/06 · 29/05 · 30/04 · 30/03 · 27/02 · 30/01 · 30/12 · 28/11 · 29/08.
    Medido nos 77 boletos da janela: a estimativa erra em 52 (67,5%) — para os
    dois lados, gerando ✓ e ✗ falsos.

    Retorna {} se o banco estiver fora — aí o cálculo cai na estimativa antiga.
    """
    sandbox = Path(__file__).resolve().parent.parent / "trk-bd-sandbox"
    if str(sandbox) not in sys.path:
        sys.path.insert(0, str(sandbox))
    try:
        from db_connection import query as _query  # type: ignore
        df = _query(
            "SELECT codigo_imovel, competencia, max(data_retirada_repasse) AS repasse "
            "FROM imobiliar_boletos_encargo_adm "
            "WHERE data_retirada_repasse IS NOT NULL "
            "GROUP BY codigo_imovel, competencia"
        )
    except Exception as exc:
        if verbose:
            print(f"[imobiliar] data_retirada_repasse indisponível ({exc.__class__.__name__}) "
                  f"— R3 cai na data de repasse ESTIMADA")
        return {}

    fora: dict[tuple[int, str], pd.Timestamp] = {}
    for _, r in df.iterrows():
        try:
            im = int(r["codigo_imovel"])
        except (TypeError, ValueError):
            continue
        comp = str(r["competencia"] or "").strip()      # banco: 'AAAA-MM'
        if len(comp) != 7 or "-" not in comp:
            continue
        ano, mes = comp.split("-")
        chave = (im, f"{mes}/{ano}")                    # CSV: 'MM/AAAA'
        d = pd.Timestamp(r["repasse"])
        if pd.isna(d):
            continue
        d = d.normalize()
        if d.tzinfo is None:
            d = d.tz_localize(TZ_BSB)
        fora[chave] = d.tz_convert("UTC")
    if verbose:
        print(f"[imobiliar] data_retirada_repasse: {len(fora)} pares imóvel×competência")
    return fora

def calcular_bonus_inadimplencia(
    dfs: dict[str, pd.DataFrame],
    df_inadimplencia: Optional[pd.DataFrame] = None,
    *,
    ref: Optional[pd.Timestamp] = None,
    repasses_reais: Optional[dict] = None,
    cutoff_dias: int = 180,
    verbose: bool = True,
) -> dict:
    """
    Calcula N do bônus Vivianne · Inadimplência (manual v4 §4.2 + regras 11ª Ed).

    Regras estritas decididas em 14/05/2026:

      R1 — Filtro de tipo de multa
            multa_adm / valor entre 0% e 15% → atraso (mantém)
            > 15% → rescisão/outro (exclui)
            valor = 0 ou nulo → exclui

      R2 — Card criado antes ou no MESMO DIA do pagamento (cobrança proativa)
            card.criado_em ≤ boleto.data_pag → mantém
            card.criado_em > boleto.data_pag → reativa, exclui

      R3 — Pagamento antes do repasse
            boleto.data_pag ≤ data_repasse
            data_repasse = mês do Vencimento_1º_Boleto do card, dia = dia_pag do proprietário

    Match boleto ↔ card:
      IM do boleto == IM no Título do card (tolera sufixo /N)
      Vencimento_1º_Boleto do card no MÊS SEGUINTE ao mes_ref do boleto

    Returns: {N, denominador_R1, antes, excluidos_*, _aviso_*}
    """
    boletos = dfs.get("boletos", pd.DataFrame())
    proprietarios = dfs.get("proprietarios", pd.DataFrame())
    imoveis = dfs.get("imoveis", pd.DataFrame())

    if len(boletos) == 0 or len(proprietarios) == 0 or len(imoveis) == 0:
        if verbose:
            print(f"[imobiliar] bonus_inadimplencia=0 (CSVs ausentes ou incompletos)")
        return {"N": 0, "denominador": 0, "taxa": 0.0, "df": pd.DataFrame()}

    def _norm_cd(v):
        try:
            return int(str(v).strip().lstrip("0") or "0")
        except (ValueError, TypeError):
            return None

    # 1. Boletos com encargo (Multa.Adm > 0 OU Juros.Adm > 0)
    b = boletos.copy()
    b["com_encargo"] = (b["multa_adm"] > 0) | (b["juros_adm"] > 0)
    b_enc = b[b["com_encargo"]].copy()
    b_enc["cd_imovel"] = b_enc["cd_imovel"].apply(_norm_cd)
    b_enc = b_enc.dropna(subset=["cd_imovel"])

    # R1 — Filtro de tipo de multa: multa_adm/valor entre 0% e 15%
    b_enc["multa_ratio"] = b_enc["multa_adm"] / b_enc["valor"].where(b_enc["valor"] > 0)
    excluidos_r1_valor0 = b_enc[b_enc["multa_ratio"].isna()].copy()
    excluidos_r1_rescisao = b_enc[(b_enc["multa_ratio"].notna()) & (b_enc["multa_ratio"] > 0.15)].copy()
    b_enc = b_enc[(b_enc["multa_ratio"].notna()) & (b_enc["multa_ratio"] <= 0.15)].copy()

    # 2. Merge → Imóveis (id_proprietario)
    imov = imoveis.copy()
    imov["cd_imovel"] = imov["cd_imovel"].apply(_norm_cd)
    imov = imov.dropna(subset=["cd_imovel"])
    b_enc = b_enc.merge(imov[["cd_imovel", "id_proprietario", "endereco"]],
                          on="cd_imovel", how="left")

    # 3. Merge → Proprietários (dia_pag)
    b_enc["id_proprietario"] = b_enc["id_proprietario"].apply(_norm_cd)
    props = proprietarios.copy()
    props["id_proprietario"] = props["id_proprietario"].apply(_norm_cd)
    b_enc = b_enc.merge(
        props[["id_proprietario", "dia_pag", "nome"]].rename(columns={"nome": "nome_proprietario"}),
        on="id_proprietario", how="left"
    )

    # 4. Filtra: precisa ter dia_pag preenchido
    b_enc = b_enc.dropna(subset=["dia_pag"]).copy()
    b_enc["dia_pag"] = b_enc["dia_pag"].astype(int)

    # 4b. RECORTE DE 180 DIAS (13/08/2026) — até aqui este era o ÚNICO indicador
    # do ranking sem janela: media o que o CSV do Imobiliar por acaso trouxesse
    # (22/01 a 10/07) enquanto todo o resto media 14/02 a 13/08.
    fora_janela = 0
    if cutoff_dias:
        base = pd.Timestamp(ref) if ref is not None else pd.Timestamp.utcnow()
        if base.tzinfo is None:
            base = base.tz_localize("UTC")
        limite = base - pd.Timedelta(days=cutoff_dias)
        pag = pd.to_datetime(b_enc["data_pag"], errors="coerce", utc=True)
        fora_janela = int((pag < limite).sum())
        b_enc = b_enc[pag >= limite].copy()

    denominador_r1 = len(b_enc)  # denominador após R1 + janela (antes de R2/R3)

    # 5. Index dos cards do pipe Inadimplência por (IM, ano-mes do Venc 1º Boleto)
    cards_no_venc: list[dict] = []
    cards_idx: dict[tuple[int, int, int], list[pd.Series]] = {}
    if df_inadimplencia is not None and len(df_inadimplencia) > 0:
        c = df_inadimplencia.copy()
        c["im_titulo"] = c["Título"].apply(_parse_im_titulo)
        c["venc"] = pd.to_datetime(c["Vencimento 1º Boleto:"], errors="coerce", utc=True)
        c["criado_em"] = pd.to_datetime(c["Criado em"], errors="coerce", utc=True)
        sem_venc_cards = c[c["venc"].isna() & c["im_titulo"].notna()]
        for _, row in sem_venc_cards.iterrows():
            cards_no_venc.append({"id": row["id"], "titulo": row["Título"],
                                   "im": int(row["im_titulo"])})
        c_ok = c.dropna(subset=["venc", "im_titulo"]).copy()
        c_ok["im_titulo"] = c_ok["im_titulo"].astype(int)
        for _, row in c_ok.iterrows():
            key = (int(row["im_titulo"]), row["venc"].year, row["venc"].month)
            cards_idx.setdefault(key, []).append(row)

    # 6. Aplicar R2 + R3 + match card por mes_ref+1
    antes_rows, depois_rows, sem_card_rows, reativa_rows, multiplos_rows = [], [], [], [], []
    for r in b_enc.itertuples(index=False):
        ms = _mes_seguinte(r.mes_ref)
        if ms is None:
            sem_card_rows.append({"cd": r.cd_imovel, "mes_ref": r.mes_ref, "data_pag": r.data_pag,
                                   "valor": r.valor, "multa": r.multa_adm,
                                   "motivo": "mes_ref inválido"})
            continue
        mes_t, ano_t = ms
        candidatos = cards_idx.get((int(r.cd_imovel), ano_t, mes_t), [])
        if not candidatos:
            sem_card_rows.append({"cd": r.cd_imovel, "mes_ref": r.mes_ref, "data_pag": r.data_pag,
                                   "valor": r.valor, "multa": r.multa_adm,
                                   "motivo": "nenhum card no mês_ref+1"})
            continue
        if len(candidatos) > 1:
            multiplos_rows.append({"cd": r.cd_imovel, "mes_alvo": f"{mes_t:02d}/{ano_t}",
                                    "qtd": len(candidatos),
                                    "titulos": [c2["Título"] for c2 in candidatos]})
        card = sorted(candidatos, key=lambda x: x["venc"], reverse=True)[0]
        data_pag = pd.to_datetime(r.data_pag, utc=True)
        criado_em = card["criado_em"]

        # R2 — card criado antes ou no mesmo dia do pagamento (compara só DATA, não datetime)
        if pd.notna(criado_em) and criado_em.date() > data_pag.date():
            reativa_rows.append({"cd": r.cd_imovel, "mes_ref": r.mes_ref, "data_pag": data_pag,
                                  "valor": r.valor, "multa": r.multa_adm,
                                  "card_criado_em": criado_em.date(),
                                  "card_titulo": card["Título"],
                                  "diff_dias": (criado_em.date() - data_pag.date()).days})
            continue

        # R3 — data_pag ≤ data_repasse
        # PRIMEIRO a data REAL do banco (coluna "Pagto Prop" do Imobiliar);
        # só cai na estimativa quando o par imóvel×competência não existe lá.
        data_rep = (repasses_reais or {}).get((int(r.cd_imovel), str(r.mes_ref).strip()))
        repasse_real = data_rep is not None
        if not repasse_real:
            data_rep = _data_repasse_from_card(card["venc"], int(r.dia_pag))
        # Compara DATA, não instante — "Pagto Prop" é um dia no Imobiliar e o
        # pagamento também. Pagar NO dia do repasse conta como antes.
        # (mesmo critério já usado na R2 acima)
        if pd.notna(data_pag) and data_pag.date() <= pd.Timestamp(data_rep).date():
            antes_rows.append({"cd_imovel": r.cd_imovel, "data_pag": data_pag,
                                "mes_ref": r.mes_ref, "venc_card": card["venc"],
                                "data_repasse": data_rep, "dia_pag": r.dia_pag,
                                "repasse_real": repasse_real,
                                "multa_adm": r.multa_adm, "multa_ratio": r.multa_ratio,
                                "card_id": card["id"], "card_titulo": card["Título"],
                                "card_criado_em": criado_em})
        else:
            depois_rows.append({"cd_imovel": r.cd_imovel, "data_pag": data_pag,
                                 "mes_ref": r.mes_ref, "venc_card": card["venc"],
                                 "data_repasse": data_rep, "card_titulo": card["Título"],
                                 "repasse_real": repasse_real})

    N = len(antes_rows)

    if verbose:
        taxa = (N / denominador_r1 * 100) if denominador_r1 else 0
        print(f"[bonus_vivianne] N={N} (regra estrita R1+R2+R3)")
        print(f"[bonus_vivianne] denominador (após R1): {denominador_r1}")
        print(f"[bonus_vivianne] excluídos por multa de rescisão (>15%): {len(excluidos_r1_rescisao)}")
        print(f"[bonus_vivianne] excluídos por valor=0/nulo: {len(excluidos_r1_valor0)}")
        print(f"[bonus_vivianne] sem card no mês esperado: {len(sem_card_rows)}")
        print(f"[bonus_vivianne] excluídos por card reativo (criado depois do pagamento): {len(reativa_rows)}")
        print(f"[bonus_vivianne] excluídos por pagamento após repasse: {len(depois_rows)}")
        print(f"[bonus_vivianne] múltiplos cards no mesmo mês (escolhido o mais recente): {len(multiplos_rows)}")
        print(f"[bonus_vivianne] taxa de exibição: {taxa:.1f}%")
        if cutoff_dias:
            print(f"[bonus_vivianne] fora da janela de {cutoff_dias}d (descartados): {fora_janela}")
        _com_real = sum(1 for x in antes_rows + depois_rows if x.get("repasse_real"))
        _tot_r3 = len(antes_rows) + len(depois_rows)
        print(f"[bonus_vivianne] R3 com data de repasse REAL: {_com_real}/{_tot_r3} "
              f"(resto caiu na estimativa)")
        if cards_no_venc:
            print(f"[bonus_vivianne] ⚠ {len(cards_no_venc)} cards sem 'Vencimento 1º Boleto:' preenchido — não podem casar")

    return {
        "N": N,
        "denominador_R1": denominador_r1,
        "fora_janela": fora_janela,
        "taxa": (N / denominador_r1) if denominador_r1 else 0.0,
        "antes": pd.DataFrame(antes_rows),
        "depois": pd.DataFrame(depois_rows),
        "sem_card": pd.DataFrame(sem_card_rows),
        "reativos": pd.DataFrame(reativa_rows),
        "multiplos": pd.DataFrame(multiplos_rows),
        "excluidos_rescisao": excluidos_r1_rescisao,
        "excluidos_valor0": excluidos_r1_valor0,
        "cards_sem_venc": cards_no_venc,
    }


if __name__ == "__main__":
    res = extract_imobiliar()
    for k, df in res.items():
        print(f"{k:14}: shape={df.shape}")
    n = calcular_bonus_inadimplencia(res)
    print(f"bonus_n calculado: {n}")
