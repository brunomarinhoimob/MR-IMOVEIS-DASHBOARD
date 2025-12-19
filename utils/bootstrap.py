import streamlit as st
import pandas as pd

from utils.notificacoes import verificar_notificacoes
from login import tela_login


def iniciar_app(df: pd.DataFrame):
    # ---------------------------------------------------------
    # CONTROLE DE LOGIN (GLOBAL)
    # ---------------------------------------------------------
    if "logado" not in st.session_state:
        st.session_state.logado = False

    if not st.session_state.logado:
        tela_login()
        st.stop()

    # ---------------------------------------------------------
    # EXECUTA NOTIFICAÇÕES (BACKEND)
    # ---------------------------------------------------------
    verificar_notificacoes(df)

    # ---------------------------------------------------------
    # ALERTAS FIXOS (FRONTEND – FECHAMENTO MANUAL)
    # ---------------------------------------------------------
    if "alertas_fixos" not in st.session_state:
        st.session_state["alertas_fixos"] = []

    if st.session_state["alertas_fixos"]:
        st.markdown("### 🔔 Atualizações Recentes")

        for i, alerta in enumerate(list(st.session_state["alertas_fixos"])):
            col1, col2 = st.columns([9, 1])

            with col1:
                st.warning(
                    f"Cliente **{alerta['cliente']}**  \n"
                    f"{alerta['de']} → **{alerta['para']}**"
                )

            with col2:
                if st.button("❌", key=f"fechar_alerta_{i}"):
                    st.session_state["alertas_fixos"].pop(i)
                    st.rerun()
