"""
TRK Experience — grava a rodada do ranking no mart do DW (tabelas mart.ranking_*)
=================================================================================

Roda depois do pipeline (python -m pipeline.run --fonte banco), no servidor:

    python -m pipeline.gravar_mart                      # grava docs/dados/banco.json (ou atual.json)
    python -m pipeline.gravar_mart --arquivo docs/dados/atual.json
    python -m pipeline.gravar_mart --oficial "13ª edição"   # fechamento do mês

Conexão: variável RANKING_DB_URL (usuário ranking_app, que só grava nas tabelas do ranking).
Tudo numa transação: se der erro, nada é gravado. Rodadas diárias com mais de 60 dias são apagadas;
as oficiais ficam para o histórico.
"""
import argparse, json, os, pathlib, sys
from datetime import datetime

RAIZ = pathlib.Path(__file__).resolve().parent.parent


def ler_env():
    env = RAIZ / ".env"
    if env.exists():
        for linha in env.read_text(encoding="utf-8").splitlines():
            if "=" in linha and not linha.strip().startswith("#"):
                k, v = linha.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def num(v):
    return None if v is None or v == "" else v


def main(argv=None):
    ap = argparse.ArgumentParser(description="Grava a rodada do ranking TRK Experience no mart do DW.")
    ap.add_argument("--arquivo", help="JSON gerado pelo pipeline (padrão: docs/dados/banco.json, senão atual.json)")
    ap.add_argument("--oficial", metavar="EDICAO", help="marca a rodada como fechamento oficial, ex.: '13ª edição'")
    a = ap.parse_args(argv)

    ler_env()
    url = os.environ.get("RANKING_DB_URL")
    if not url:
        sys.exit("[ERRO] Defina RANKING_DB_URL no .env (usuário ranking_app do dw_trk).")

    if a.arquivo:
        arq = pathlib.Path(a.arquivo)
    else:
        arq = RAIZ / "docs" / "dados" / "banco.json"
        if not arq.exists():
            arq = RAIZ / "docs" / "dados" / "atual.json"
    d = json.loads(arq.read_text(encoding="utf-8"))
    meta = d.get("_meta", {})
    pessoas = d.get("PESSOAS", [])
    if not pessoas:
        sys.exit(f"[ERRO] {arq.name} não tem PESSOAS: o pipeline rodou?")

    import psycopg  # psycopg 3
    with psycopg.connect(url) as c, c.cursor() as cur:
        cur.execute("SET TIME ZONE 'America/Sao_Paulo'")
        cur.execute(
            "INSERT INTO mart.ranking_rodada (gerado_em, data_ref, fonte, edicao, oficial) "
            "VALUES (%s, %s, %s, %s, %s) RETURNING rodada_id",
            (meta.get("geradoEm") or datetime.utcnow().isoformat() + "Z", meta.get("ref"),
             meta.get("fonte", "api"), a.oficial, bool(a.oficial)))
        rid = cur.fetchone()[0]

        for p in pessoas:
            cur.execute(
                "INSERT INTO mart.ranking_pessoa (rodada_id, pessoa_id, nome, cargo, posicao, nota, pontos, indicadores, bonus, "
                "pontos_fortes, pontos_atencao) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (rid, p["id"], p["nome"], p.get("cargo"), p.get("pos"), num(p.get("nota")), num(p.get("pts")),
                 p.get("inds"), num(p.get("bonus")), p.get("pontosFort") or [], p.get("pontosAten") or []))
            bpp = p.get("bonus_por_proc") or {}
            for proc, nota in (p.get("scores") or {}).items():
                if nota is not None or proc in bpp:
                    cur.execute("INSERT INTO mart.ranking_processo (rodada_id, pessoa_id, processo, nota, bonus) VALUES (%s,%s,%s,%s,%s)",
                                (rid, p["id"], proc, num(nota), num(bpp.get(proc))))
            for i, x in enumerate(p.get("detalhes") or [], 1):
                cur.execute(
                    "INSERT INTO mart.ranking_indicador (rodada_id, pessoa_id, ordem, indicador, meta, ok, total, pct, peso, nota) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (rid, p["id"], i, x.get("nome"), x.get("meta"), x.get("ok"), x.get("tot"), num(x.get("pct")),
                     num(x.get("peso")), num(x.get("score"))))

        for chave, caso in (d.get("IMOVEIS") or {}).items():
            cur.execute("INSERT INTO mart.ranking_caso (rodada_id, chave, titulo, colunas, linhas) VALUES (%s,%s,%s,%s,%s)",
                        (rid, chave, caso.get("titulo"), json.dumps(caso.get("cols"), ensure_ascii=False),
                         json.dumps(caso.get("rows"), ensure_ascii=False)))

        cur.execute("DELETE FROM mart.ranking_rodada WHERE NOT oficial AND gerado_em < now() - interval '60 days'")
        c.commit()
    print(f"OK — rodada {rid} gravada ({len(pessoas)} pessoas, fonte {meta.get('fonte')}){' · oficial: ' + a.oficial if a.oficial else ''}")


if __name__ == "__main__":
    main()
