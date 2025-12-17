import streamlit as st
import json
from pathlib import Path
import re

# =========================================================
# BLOQUEIO SEM LOGIN
# =========================================================
if "logado" not in st.session_state or not st.session_state.logado:
    st.warning("🔒 Acesso restrito. Faça login para continuar.")
    st.stop()

# =========================================================
# ARQUIVO DE USUÁRIOS
# =========================================================
CAMINHO_USERS = Path("users.json")

def carregar_users():
    if CAMINHO_USERS.exists():
        with open(CAMINHO_USERS, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def salvar_users(users: dict):
    with open(CAMINHO_USERS, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2, ensure_ascii=False)

# =========================================================
# FUNÇÕES DE NEGÓCIO
# =========================================================
def validar_senha(usuario_login: str, senha_digitada: str) -> bool:
    users = carregar_users()

    usuario_login = usuario_login.strip()
    senha_digitada = senha_digitada.strip()

    if usuario_login not in users:
        return False

    return users[usuario_login]["senha"].strip() == senha_digitada


def salvar_nova_senha(usuario_login: str, senha_atual: str, nova_senha: str):
    users = carregar_users()

    usuario_login = usuario_login.strip()
    senha_atual = senha_atual.strip()
    nova_senha = nova_senha.strip()

    if usuario_login not in users:
        return False, "Usuário não encontrado."

    if not validar_senha(usuario_login, senha_atual):
        return False, "Senha atual incorreta."

    users[usuario_login]["senha"] = nova_senha
    salvar_users(users)

    return True, None

# =========================================================
# INTERFACE
# =========================================================
st.set_page_config(
    page_title="Alterar Senha",
    page_icon="🔐",
    layout="centered"
)

st.title("🔐 Alterar Senha")
st.caption("Crie uma nova senha para acessar o dashboard.")

usuario_login = st.session_state.get("usuario")
nome_usuario = st.session_state.get("nome_usuario", usuario_login)

st.markdown(f"**Usuário logado:** `{nome_usuario}`")
st.markdown("---")

senha_atual = st.text_input("Senha atual", type="password")
nova_senha = st.text_input("Nova senha", type="password")
confirmar_senha = st.text_input("Confirmar nova senha", type="password")

st.markdown("""
**Regras da senha:**
- mínimo de 6 caracteres  
- deve conter letras e números  
- diferente da senha atual
""")

# =========================================================
# AÇÃO
# =========================================================
if st.button("Salvar nova senha", use_container_width=True):

    if not senha_atual or not nova_senha or not confirmar_senha:
        st.error("Preencha todos os campos.")
        st.stop()

    if nova_senha != confirmar_senha:
        st.error("A nova senha e a confirmação não conferem.")
        st.stop()

    if nova_senha.strip() == senha_atual.strip():
        st.error("A nova senha não pode ser igual à senha atual.")
        st.stop()

    if len(nova_senha.strip()) < 6:
        st.error("A nova senha deve ter pelo menos 6 caracteres.")
        st.stop()

    if not re.search(r"[A-Za-z]", nova_senha) or not re.search(r"[0-9]", nova_senha):
        st.error("A senha deve conter letras e números.")
        st.stop()

    ok, erro = salvar_nova_senha(usuario_login, senha_atual, nova_senha)

    if not ok:
        st.error(erro)
        st.stop()

    st.success("✅ Senha alterada com sucesso!")
    st.info("Use a nova senha no próximo login.")
