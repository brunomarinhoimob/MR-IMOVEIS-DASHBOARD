import streamlit as st
import pandas as pd
import json
from pathlib import Path

# ---------------------------------------------------------
# CACHE LOCAL
# ---------------------------------------------------------
ARQ_STATUS = Path("utils/status_clientes_cache.json")


def _carregar_cache():
    if ARQ_STATUS.exists():
        try:
            with open(ARQ_STATUS, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _salvar_cache(cache: dict):
    try:
        with open(ARQ_STATUS, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# ---------------------------------------------------------
# NOTIFICAÇÕES
# NOVA LINHA + STATUS DIFERENTE = EVENTO
# ---------------------------------------------------------
def verificar_notificacoes(df: pd.DataFrame):
    if df is None or df.empty:
        return

    perfil = st.session_state.get("perfil")
    nome_corretor = st.session_state.get("nome_usuario", "").upper().strip()

    colunas = {"CHAVE_CLIENTE", "STATUS_BASE", "CORRETOR", "DIA"}
    if not colunas.issubset(df.columns):
        return

    # filtro por perfil
    if perfil == "corretor":
        df = df[df["CORRETOR"] == nome_corretor]

    if df.empty:
        return

    df = df.sort_values("DIA")

    cache = _carregar_cache()
    chave_cache = nome_corretor if perfil == "corretor" else "ADMIN"
    cache_usuario = cache.get(chave_cache, {})

    for _, row in df.iterrows():
        chave = row["CHAVE_CLIENTE"]
        status_atual = row["STATUS_BASE"]
        dia_atual = str(row["DIA"])

        if not status_atual:
            continue

        ultimo = cache_usuario.get(chave)

        # compatibilidade com cache antigo (string)
        if isinstance(ultimo, str):
            ultimo_status = ultimo
            ultimo_dia = None
        elif isinstance(ultimo, dict):
            ultimo_status = ultimo.get("status")
            ultimo_dia = ultimo.get("dia")
        else:
            ultimo_status = None
            ultimo_dia = None

        # NOVA LINHA + STATUS DIFERENTE = NOTIFICA
        if ultimo_status and ultimo_status != status_atual and ultimo_dia != dia_atual:
            cliente = chave.split("|")[0].strip()
            st.toast(
                f"🔔 Cliente {cliente}\n{ultimo_status} → {status_atual}",
                icon="🔔",
            )

        # atualiza cache SEMPRE
        cache_usuario[chave] = {
            "status": status_atual,
            "dia": dia_atual,
        }

    cache[chave_cache] = cache_usuario
    _salvar_cache(cache)
