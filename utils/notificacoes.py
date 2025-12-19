import streamlit as st
import pandas as pd

# ---------------------------------------------------------
# NOTIFICAÇÕES (CACHE EM MEMÓRIA - SESSION_STATE)
# REGRA: NOVA LINHA NO CLIENTE => STATUS MAIS RECENTE
# ---------------------------------------------------------
def verificar_notificacoes(df: pd.DataFrame):
    if df is None or df.empty:
        return

    perfil = st.session_state.get("perfil")
    nome_corretor = st.session_state.get("nome_usuario", "").upper().strip()

    colunas = {"CHAVE_CLIENTE", "STATUS_BASE", "CORRETOR"}
    if not colunas.issubset(df.columns):
        return

    # cache global por sessão
    if "notificacoes_cache" not in st.session_state:
        st.session_state["notificacoes_cache"] = {}

    cache = st.session_state["notificacoes_cache"]
    chave_cache = nome_corretor if perfil == "corretor" else "ADMIN"
    cache_usuario = cache.get(chave_cache, {})

    # filtro por corretor
    if perfil == "corretor":
        df = df[df["CORRETOR"] == nome_corretor]

    if df.empty:
        return

    # -----------------------------
    # ordenação (DIA se existir)
    # -----------------------------
    df = df.copy()
    df["_ord"] = range(len(df))

    if "DIA" in df.columns:
        df["_dia_dt"] = pd.to_datetime(df["DIA"], errors="coerce", dayfirst=True)
        df = df.sort_values(["_dia_dt", "_ord"])
    else:
        df = df.sort_values(["_ord"])

    # último status por cliente (linha mais recente)
    ultimos = (
        df.groupby("CHAVE_CLIENTE", as_index=False)
          .tail(1)[["CHAVE_CLIENTE", "STATUS_BASE"]]
          .set_index("CHAVE_CLIENTE")["STATUS_BASE"]
          .to_dict()
    )

    # total de linhas por cliente (detecta "linha nova")
    contagens = df["CHAVE_CLIENTE"].value_counts().to_dict()

    # -----------------------------
    # normalizador de cache antigo
    # -----------------------------
    def _normalizar_antigo(valor):
        """
        Converte cache antigo para dict padrão:
        - dict -> mantém
        - int -> {"count": int, "status": None}
        - str -> {"count": 0, "status": str}
        - None/outros -> None
        """
        if isinstance(valor, dict):
            return {
                "count": int(valor.get("count", 0) or 0),
                "status": valor.get("status"),
            }
        if isinstance(valor, int):
            return {"count": int(valor), "status": None}
        if isinstance(valor, str):
            return {"count": 0, "status": valor}
        return None

    # -----------------------------
    # lógica de notificação
    # -----------------------------
    for chave, status_atual in ultimos.items():
        if not status_atual:
            continue

        count_atual = int(contagens.get(chave, 0))
        antigo_raw = cache_usuario.get(chave)
        antigo = _normalizar_antigo(antigo_raw)

        # primeira vez vendo esse cliente na sessão -> só registra
        if not antigo:
            cache_usuario[chave] = {"count": count_atual, "status": status_atual}
            continue

        antigo_count = int(antigo.get("count", 0) or 0)
        antigo_status = antigo.get("status")

        # entrou linha nova?
        if count_atual > antigo_count:
            # notifica só se status mudou (mudança real)
            if antigo_status and antigo_status != status_atual:
                cliente = str(chave).split("|")[0].strip()
                st.toast(
                    f"🔔 Cliente {cliente}\n{antigo_status} → {status_atual}",
                    icon="🔔",
                )

        # atualiza cache sempre no formato novo
        cache_usuario[chave] = {"count": count_atual, "status": status_atual}

    cache[chave_cache] = cache_usuario
    st.session_state["notificacoes_cache"] = cache
