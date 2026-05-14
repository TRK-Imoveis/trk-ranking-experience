"""
Lê os dumps em config/_pipe_dumps/ e tenta casar fases + campos
contra as referências do manual_v4.md. Produz dois artefatos:

- config/pipes.json         — chave do ranking → {id, name, uuid}
- config/fields_map.json    — chave do ranking → {fields: {label_manual: {id, internal_id}}, phases: {nome_manual: phase_id}}

Imprime relatório de OK / FALTA / AMBÍGUO para revisão humana.
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
DUMPS = ROOT / "config" / "_pipe_dumps"
OUT_PIPES = ROOT / "config" / "pipes.json"
OUT_FIELDS = ROOT / "config" / "fields_map.json"

# Mapeamento ranking_key → pipe_id (validado nas etapas anteriores)
RANKING_PIPES = {
    "comercial_locacao":  "301686632",  # COM - Comercial de aluguel
    "cont_locacao":       "304021288",  # ADM - Locação COM ADM - NOVO  (validado com usuário 2026-05-13)
    "cont_adm":           "301689857",  # ADM - Cont. de ADMINISTRAÇÃO
    "rescisao_adm":       "301688015",  # ADM - Resc. de ADMINISTRAÇÃO
    "rescisao_loc":       "301686638",  # ADM - Rescisão de LOCAÇÃO
    "reparos":            "301687289",  # ADM - Reparos
    "renovacao":          "301683424",  # ADM - Renovações de contratos
    "inadimplencia":      "302601622",  # ADM - Inadimplência
    "backoffice":         "305733753",  # ADM - Solicitações BackOffice
    "dirf_darf":          "302274599",  # ADM - DARFs / DIRFs
    "vistorias":          "302750891",  # ADM - Vistorias
    "contestacoes":       "301722113",  # ADM - Contestação de vistoria
}

# O que o manual_v4 referencia em cada pipe.
# Para fields: label visível no XLSX/manual.
# Para phases: nome da fase (usado em "Primeira vez que entrou em", "Última vez que saiu de", "Tempo total na fase X").
MANUAL_REFS = {
    "comercial_locacao": {
        "fields": ["IM", "Data publicação Anúncio", "Profissional responsável"],
        "phases": [
            "Avaliação Técnica",
            "Cadastro / Reativação no NIDO",
            "Conferência Final",
            "15 dias desocupado",
            "30 Dias desocupado",
            "60 Dias desocupado",
            "90 Dias desocupado",
            "180 Dias desocupado",
            "Concluído",
        ],
    },
    "cont_locacao": {
        # OBS: pipe migrou para "ADM - Locação COM ADM - NOVO" (304021288), e a fase chama-se "1º Boleto" exato.
        "fields": ["Imóvel"],
        "phases": [
            "Confecção do contrato de locação",
            "1º Boleto",
            "Fechamento NIDO",
            "Concluído",
        ],
    },
    "cont_adm": {
        "fields": ["Assessor (lista)", "Criar Card de Vistoria Técnica"],
        "phases": [
            "Contrato assinado - Conferir Nido",
            "Confecção do contrato",
            "Conferência do contrato",
            "Concluído",
        ],
    },
    "rescisao_adm": {
        # OBS: manual diz "Sem filtro (compartilhado)" mas baseline 10ª mostra denominadores diferentes
        # por assessora — está faltando filtro Assessor (lista) na documentação.
        "fields": ["Termo de Distrato assinado", "Assessor (lista)"],
        "phases": [
            "Encerramento",
            "Repasse final / Distrato (FINANCEIRO)",
            "Concluído",
        ],
    },
    "rescisao_loc": {
        "fields": ["Data do recebimento das chaves:", "Imóvel", "Assessor (lista)"],
        "phases": [
            "Vistoria recebida",
            "Levant. Taxas Proporcionais",
            "Agendamento de vistoria",
            "Envio do boleto final",
            "Levantamento de taxas",
        ],
    },
    "reparos": {
        "fields": ["Selecionar o assessor"],
        "phases": [
            "Orçamento | Prestador",
            "Pós-venda",
        ],
    },
    "renovacao": {
        "fields": ["Assessor (lista)", "Data de vencimento"],
        "phases": [
            "Avaliação de mercado",
            "Contato com proprietário",
            "Contrato assinado / Finalizar",
            "Processo concluído",
            "Confecção do contrato",
        ],
    },
    "inadimplencia": {
        "fields": ["Vencimento 1º Boleto:"],
        "phases": [
            "Cobrança (inicial)",
            "CredPago: Acionar",
            "Negativação (No 8º dia de atraso)",
        ],
    },
    "backoffice": {
        "fields": ["Responsável"],
        "phases": [
            "↪️ Troca de Titularidade",
            "🚩 Pendência Assessor",
            "Concluído",
        ],
    },
    "dirf_darf": {
        "fields": ["Ano:", "Responsável"],
        "phases": ["Concluído"],
    },
    "vistorias": {
        "fields": ["Área útil M²", "IM", "vistoria iniciada em", "Vistoria finalizada em"],
        "phases": ["Em produção", "Concluído"],
    },
    "contestacoes": {
        "fields": [],
        "phases": ["Concluído"],
    },
}


def slug(s: str) -> str:
    s = unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", s)).strip()


def find_field(dump: dict, label_manual: str) -> list[dict]:
    """Procura campo por label (exato e por slug). Retorna matches."""
    target = slug(label_manual)
    out = []
    seen_ids = set()
    fields = list(dump.get("start_form_fields") or [])
    for ph in dump.get("phases") or []:
        fields.extend(ph.get("fields") or [])
    for f in fields:
        if f["id"] in seen_ids:
            continue
        seen_ids.add(f["id"])
        lbl = f.get("label") or ""
        if lbl == label_manual or slug(lbl) == target:
            out.append({"id": f["id"], "internal_id": f["internal_id"], "label": lbl, "type": f["type"]})
    return out


def find_phase(dump: dict, name_manual: str) -> list[dict]:
    target = slug(name_manual)
    out = []
    for ph in dump.get("phases") or []:
        if ph["name"] == name_manual or slug(ph["name"]) == target:
            out.append({"id": ph["id"], "name": ph["name"], "cards_count": ph.get("cards_count", 0)})
    return out


def load_dump(pipe_id: str) -> dict | None:
    for f in DUMPS.glob(f"{pipe_id}__*.json"):
        return json.loads(f.read_text(encoding="utf-8"))
    return None


def main() -> None:
    pipes_index = {}
    fields_map = {}
    ambiguous = []

    for key, pipe_id in RANKING_PIPES.items():
        dump = load_dump(pipe_id)
        if not dump:
            print(f"[{key}] DUMP NÃO ENCONTRADO para pipe {pipe_id}")
            continue
        pipes_index[key] = {
            "id": pipe_id,
            "name": dump["name"],
        }

        refs = MANUAL_REFS[key]
        entry_fields = {}
        entry_phases = {}
        missing_f = []
        missing_p = []
        amb_f = []
        amb_p = []

        for lbl in refs["fields"]:
            matches = find_field(dump, lbl)
            if not matches:
                missing_f.append(lbl)
            elif len(matches) == 1:
                entry_fields[lbl] = matches[0]
            else:
                amb_f.append((lbl, matches))

        for ph_name in refs["phases"]:
            matches = find_phase(dump, ph_name)
            if not matches:
                missing_p.append(ph_name)
            elif len(matches) == 1:
                entry_phases[ph_name] = matches[0]
            else:
                amb_p.append((ph_name, matches))

        fields_map[key] = {
            "pipe_id": pipe_id,
            "pipe_name": dump["name"],
            "fields": entry_fields,
            "phases": entry_phases,
        }

        # relatório
        print(f"\n=== [{key}]  {dump['name']}  (id={pipe_id})")
        print(f"  campos OK ({len(entry_fields)}):  {list(entry_fields.keys())}")
        print(f"  fases OK ({len(entry_phases)}):   {list(entry_phases.keys())}")
        if missing_f:
            print(f"  CAMPO FALTA:    {missing_f}")
        if missing_p:
            print(f"  FASE FALTA:     {missing_p}")
        if amb_f:
            print(f"  CAMPO AMBÍGUO:  {[(a, [m['label'] for m in ms]) for a, ms in amb_f]}")
        if amb_p:
            print(f"  FASE AMBÍGUA:   {[(a, [m['name'] for m in ms]) for a, ms in amb_p]}")

        if missing_f or missing_p or amb_f or amb_p:
            ambiguous.append(key)

    OUT_PIPES.write_text(json.dumps(pipes_index, ensure_ascii=False, indent=2), encoding="utf-8")
    OUT_FIELDS.write_text(json.dumps(fields_map, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n→ {OUT_PIPES.relative_to(ROOT)} ({len(pipes_index)} pipes)")
    print(f"→ {OUT_FIELDS.relative_to(ROOT)} ({len(fields_map)} pipes)")

    if ambiguous:
        print(f"\n⚠️  Pipes com gaps/ambiguidades a resolver: {ambiguous}")
    else:
        print("\nOK — todos os campos e fases do manual mapeados sem ambiguidade.")


if __name__ == "__main__":
    main()
