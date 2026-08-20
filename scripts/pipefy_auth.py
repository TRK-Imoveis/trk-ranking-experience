"""
TRK Experience — Pipefy OAuth helper (Service Account)
======================================================

Obtém access_token via client_credentials e expõe um cliente GraphQL simples.
Reutilizado pelos scripts de descoberta e pelos módulos de extração.
"""
from __future__ import annotations

import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

GRAPHQL_URL = "https://api.pipefy.com/graphql"
OAUTH_URL = os.getenv("PIPEFY_OAUTH_URL", "https://app.pipefy.com/oauth/token")
CLIENT_ID = os.getenv("PIPEFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("PIPEFY_CLIENT_SECRET")

_token_cache: dict = {"access_token": None, "expires_at": 0.0}


def get_access_token(force_refresh: bool = False) -> str:
    """Obtém access_token via OAuth2 client_credentials. Cacheia em memória."""
    if not force_refresh and _token_cache["access_token"] and time.time() < _token_cache["expires_at"]:
        return _token_cache["access_token"]

    if not CLIENT_ID or not CLIENT_SECRET:
        raise RuntimeError("PIPEFY_CLIENT_ID/SECRET ausentes no .env")

    resp = requests.post(
        OAUTH_URL,
        data={
            "grant_type": "client_credentials",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        },
        timeout=30,
    )
    resp.raise_for_status()
    payload = resp.json()
    _token_cache["access_token"] = payload["access_token"]
    # margem de 60s antes do expires_in real
    _token_cache["expires_at"] = time.time() + max(60, int(payload.get("expires_in", 3600)) - 60)
    return _token_cache["access_token"]


# TENTATIVAS EM ERRO DE REDE (20/08/2026)
# ────────────────────────────────────────────────────────────────────
# Uma rodada com --no-cache faz centenas de chamadas ao Pipefy ao longo de
# 2-3 minutos. Em 20/08 uma única queda de conexão derrubou a rodada inteira:
#   ConnectionResetError(10054, 'cancelamento de uma conexão existente pelo
#   host remoto')
# Só repetimos falhas TRANSITÓRIAS: queda de conexão, timeout e HTTP 5xx/429.
# Erro de GraphQL, 401 e 4xx (fora 429) NÃO se repetem — são bug ou permissão,
# e repetir só esconde o problema e multiplica a espera.
ERRO_TRANSITORIO = (
    requests.exceptions.ConnectionError,
    requests.exceptions.Timeout,
    requests.exceptions.ChunkedEncodingError,
)
GQL_TENTATIVAS = 3
GQL_ESPERA_BASE = 2.0   # 2s, 4s, 8s


def gql(query: str, variables: dict | None = None) -> dict:
    """Executa uma query GraphQL. Lança em erros HTTP ou GraphQL.

    Repete até GQL_TENTATIVAS vezes em falha transitória de rede, com espera
    dobrando a cada tentativa. Cada nova tentativa pega o token de novo — se a
    queda foi por token expirado no meio de uma rodada longa, resolve junto.
    """
    ultima = None
    for tentativa in range(1, GQL_TENTATIVAS + 1):
        try:
            token = get_access_token()
            resp = requests.post(
                GRAPHQL_URL,
                headers={"Authorization": f"Bearer {token}",
                         "Content-Type": "application/json"},
                json={"query": query, "variables": variables or {}},
                timeout=60,
            )
            if resp.status_code == 429 or resp.status_code >= 500:
                raise requests.exceptions.ConnectionError(
                    f"HTTP {resp.status_code} do Pipefy")
            resp.raise_for_status()
            data = resp.json()
            if "errors" in data and data["errors"]:
                raise RuntimeError(f"GraphQL errors: {data['errors']}")
            return data["data"]
        except ERRO_TRANSITORIO as exc:
            ultima = exc
            if tentativa == GQL_TENTATIVAS:
                break
            espera = GQL_ESPERA_BASE * (2 ** (tentativa - 1))
            print(f"  [pipefy] falha de rede ({exc.__class__.__name__}) — "
                  f"tentativa {tentativa}/{GQL_TENTATIVAS}, repetindo em {espera:.0f}s")
            time.sleep(espera)
    raise RuntimeError(
        f"Pipefy: {GQL_TENTATIVAS} tentativas falharam por erro de rede. "
        f"Último erro: {ultima!r}"
    ) from ultima


if __name__ == "__main__":
    # Sanity check: obter token e fazer um ping mínimo
    print("[auth] solicitando access_token via client_credentials…")
    tok = get_access_token()
    print(f"[auth] OK — token de {len(tok)} chars")
    print("[auth] testando query mínima `me { id name email }`…")
    me = gql("query { me { id name email } }")
    print(f"[auth] OK — me = {me}")
