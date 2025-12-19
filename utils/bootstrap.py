import streamlit as st
import pandas as pd

from utils.notificacoes import verificar_notificacoes
from login import tela_login


def iniciar_app(df: pd.DataFrame):
    """
    Bootstrap global do app:
    - controla login
    - executa notificações
    - renderiza alertas fixos
    """

    # -------------------------------------------------
    # CONTROLE DE LOGIN (GLOBAL)
    # -------------------------------------------------
    if "logado" not in st.session_state:
        st.session_state.logado = False

    if not st.session_state.logado:
        tela_login()
        st.stop()

    # -------------------------------------------------
    # EXECUÇÃO DAS NOTIFICAÇÕES (BACKEND)
    # -------------------------------------------------
    verificar_notificacoes(df)

    # -------------------------------------------------
    # GARANTIA DE ESTRUTURA NO SESSION STATE
    # -------------------------------------------------
    if "alertas_fixos" not in st.session_state:
        st.session_state["alertas_fixos"] = []

    if "alertas_fixos_ids" not in st.session_state:
        st.session_state["alertas_fixos_ids"] = set()

    # -------------------------------------------------
    # RENDERIZAÇÃO DOS ALERTAS FIXOS (FRONTEND)
    # -------------------------------------------------
    if st.session_state["alertas_fixos"]:

        st.markdown("### 🔔 Atualizações Recentes")

        # copia segura (evita problema ao remover item)
        alertas = list(st.session_state["alertas_fixos"])

        for alerta in alertas:

            col1, col2 = st.columns([9, 1])

            with col1:
                st.warning(
                    f"Cliente **{alerta['cliente']}**  \n"
                    f"{alerta['de']} → **{alerta['para']}**"
                )

            with col2:
                if st.button("❌", key=f"fechar_alerta_{alerta['id']}"):

                    # remove o alerta visual
                    st.session_state["alertas_fixos"] = [
                        a for a in st.session_state["alertas_fixos"]
                        if a["id"] != alerta["id"]
                    ]

                    # remove o id para não reaparecer
                    if alerta["id"] in st.session_state["alertas_fixos_ids"]:
                        st.session_state["alertas_fixos_ids"].remove(alerta["id"])

                    st.rerun()
