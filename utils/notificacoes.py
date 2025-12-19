import streamlit as st
import pandas as pd

# ---------------------------------------------------------
# NOTIFICAÇÕES (CACHE EM MEMÓRIA - SESSION_STATE)
# REGRA: NOVA LINHA = EVENTO
# ---------------------------------------------------------
def verificar_notificacoes(df: pd.DataFrame):
    if df is None or df.empty:
        return

    perfil = st.session_state.get("perfil")
    nome_corretor = st.session_state.get("nome_usuario", "").upper().strip()

    colunas = {"CHAVE_CLIENTE", "STATUS_BASE", "CORRETOR"}
    if not colunas.issubset(df.columns):
        return

    # inicializa cache global de notificações (por sessão)
    if "notificacoes_cache" not in st.session_state:
        st.session_state["notificacoes_cache"] = {}

    cache = st.session_state["notificacoes_cache"]

    # chave por perfil
    chave_cache = nome_corretor if perfil == "corretor" else "ADMIN"
    cache_usuario = cache.get(chave_cache, {})

    # filtro por corretor
    if perfil == "corretor":
        df = df[df["CORRETOR"] == nome_corretor]

    if df.empty:
        return

    # percorre histórico
    for _, row in df.iterrows():
        chave = row["CHAVE_CLIENTE"]
        status_atual = row["STATUS_BASE"]

        if not status_atual:
            continue

        # total de linhas desse cliente (define "nova linha")
        total_linhas_cliente = len(df[df["CHAVE_CLIENTE"] == chave])

        ultimo_total = cache_usuario.get(chave)

        # REGRA: SE SURGIU LINHA NOVA → NOTIFICA
        if ultimo_total is not None and total_linhas_cliente > ultimo_total:
            cliente = chave.split("|")[0].strip()
            st.toast(
                f"🔔 Nova atualização do cliente {cliente}\nStatus: {status_atual}",
                icon="🔔",
            )

        # atualiza cache SEMPRE
        cache_usuario[chave] = total_linhas_cliente

    cache[chave_cache] = cache_usuario
    st.session_state["notificacoes_cache"] = cache
