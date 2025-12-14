import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime

# =========================
# CONFIGURAÇÕES
# =========================
st.set_page_config(
    page_title="Funil de Leads - MR Imóveis",
    layout="wide"
)

LOGO_PATH = "logo_mr.png"

URL_PLANILHA = (
    "https://docs.google.com/spreadsheets/d/"
    "SEU_ID_AQUI/export?format=csv"
)

URL_CRM_ULTIMOS_1000 = "https://app.crm.supremo.app/api/leads"
TOKEN_SUPREMO = st.secrets.get("TOKEN_SUPREMO", None)

TTL_CACHE = 600

# =========================
# FUNÇÕES AUXILIARES
# =========================
def normalizar_texto(txt):
    if pd.isna(txt):
        return ""
    return (
        str(txt)
        .upper()
        .strip()
        .replace("  ", " ")
    )

@st.cache_data(ttl=TTL_CACHE)
def carregar_planilha():
    df = pd.read_csv(URL_PLANILHA, dtype=str)

    df.columns = [c.upper().strip() for c in df.columns]

    df["CLIENTE_NORM"] = df["CLIENTE"].map(normalizar_texto)
    df["STATUS_BASE"] = df["SITUACAO"].str.upper().str.strip()

    df["DATA"] = pd.to_datetime(df["DATA"], errors="coerce")
    df["ULTIMA_ATUALIZACAO"] = df["DATA"]

    return df


@st.cache_data(ttl=TTL_CACHE)
def carregar_crm_ultimos_1000():
    cols = ["CLIENTE_NORM", "ORIGEM_CRM"]

    if not TOKEN_SUPREMO:
        return pd.DataFrame(columns=cols)

    try:
        headers = {"Authorization": f"Bearer {TOKEN_SUPREMO}"}
        r = requests.get(URL_CRM_ULTIMOS_1000, headers=headers, timeout=30)
        r.raise_for_status()

        dados = r.json().get("dados", [])
        df = pd.DataFrame(dados)

        if df.empty:
            return pd.DataFrame(columns=cols)

        df["CLIENTE_NORM"] = (
            df["nome_pessoa"]
            .astype(str)
            .map(normalizar_texto)
        )

        df["ORIGEM_CRM"] = (
            df["nome_origem"]
            .fillna("SEM ORIGEM")
            .astype(str)
            .str.upper()
        )

        df = (
            df.sort_values("data_captura")
              .drop_duplicates("CLIENTE_NORM", keep="last")
        )

        return df[cols]

    except Exception:
        st.warning(
            "⚠️ CRM indisponível no momento. "
            "Origem exibida como SEM CADASTRO NO CRM."
        )
        return pd.DataFrame(columns=cols)


# =========================
# CARREGAMENTO
# =========================
df = carregar_planilha()
df_crm = carregar_crm_ultimos_1000()

df = df.merge(
    df_crm,
    on="CLIENTE_NORM",
    how="left"
)

df["ORIGEM_CRM"] = df["ORIGEM_CRM"].fillna("SEM CADASTRO NO CRM")

# =========================
# ÚLTIMA SITUAÇÃO DO LEAD
# =========================
df_ult = (
    df.sort_values("ULTIMA_ATUALIZACAO")
      .drop_duplicates("CLIENTE_NORM", keep="last")
)

# =========================
# STATUS DO FUNIL
# =========================
EM_ANALISE = df_ult["STATUS_BASE"].eq("EM ANALISE")
REANALISE = df_ult["STATUS_BASE"].eq("REANALISE")
APROVADO = df_ult["STATUS_BASE"].str.contains("APROVADO", na=False)
PENDENCIA = df_ult["STATUS_BASE"].eq("PENDENCIA")
REPROVADO = df_ult["STATUS_BASE"].eq("REPROVADO")
VENDA_GERADA = df_ult["STATUS_BASE"].eq("VENDA GERADA")
VENDA_INFORMADA = df_ult["STATUS_BASE"].eq("VENDA INFORMADA")
DESISTIU = df_ult["STATUS_BASE"].eq("DESISTIU")

# =========================
# HEADER
# =========================
col_logo, col_title = st.columns([1, 6])
with col_logo:
    st.image(LOGO_PATH, width=120)
with col_title:
    st.title("🎯 Funil de Leads – Origem, Status e Conversão")

# =========================
# STATUS ATUAL DO FUNIL
# =========================
st.subheader("📌 Status Atual do Funil")

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Em Análise", EM_ANALISE.sum())
c2.metric("Reanálises", REANALISE.sum())
c3.metric("Pendências", PENDENCIA.sum())
c4.metric("Vendas Geradas", VENDA_GERADA.sum())
c5.metric("Leads Ativos", len(df_ult))

st.divider()

# =========================
# PERFORMANCE POR ORIGEM
# =========================
st.subheader("📈 Performance e Conversão por Origem")

origens = ["TODAS"] + sorted(df_ult["ORIGEM_CRM"].unique().tolist())
origem_sel = st.selectbox("Origem", origens)

tipo_venda = st.radio(
    "Tipo de Venda para Conversão",
    ["Vendas Geradas + Informadas", "Apenas Vendas Geradas"],
    horizontal=True
)

df_perf = df_ult.copy()

if origem_sel != "TODAS":
    df_perf = df_perf[df_perf["ORIGEM_CRM"] == origem_sel]

# Contagens corretas
leads = len(df_perf)

analises = df_perf["STATUS_BASE"].eq("EM ANALISE").sum()
aprovados = df_perf["STATUS_BASE"].str.contains("APROVADO", na=False).sum()
reanalises = df_perf["STATUS_BASE"].eq("REANALISE").sum()

if tipo_venda == "Apenas Vendas Geradas":
    vendas = df_perf["STATUS_BASE"].eq("VENDA GERADA").sum()
else:
    vendas = df_perf["STATUS_BASE"].isin(
        ["VENDA GERADA", "VENDA INFORMADA"]
    ).sum()

def pct(a, b):
    return f"{(a / b * 100):.1f}%" if b > 0 else "0%"

c1, c2, c3, c4 = st.columns(4)
c1.metric("Leads", leads)
c2.metric("Análises", analises)
c3.metric("Reanálises", reanalises)
c4.metric("Vendas", vendas)

c1.metric("Lead → Análise", pct(analises, leads))
c2.metric("Análise → Aprovação", pct(aprovados, analises))
c3.metric("Análise → Venda", pct(vendas, analises))
c4.metric("Aprovação → Venda", pct(vendas, aprovados))

# =========================
# TABELA DA ORIGEM
# =========================
st.subheader("📋 Leads da Origem Selecionada")

cols_tabela = [
    "CLIENTE",
    "CORRETOR",
    "EQUIPE",
    "STATUS_BASE",
    "ULTIMA_ATUALIZACAO"
]

st.dataframe(
    df_perf[cols_tabela]
    .sort_values("ULTIMA_ATUALIZACAO", ascending=False),
    use_container_width=True
)

st.divider()

# =========================
# AUDITORIA DE CLIENTE
# =========================
st.subheader("🔎 Auditoria Rápida de Cliente")

nome_busca = st.text_input("Digite o nome do cliente")

if nome_busca:
    nome_norm = normalizar_texto(nome_busca)

    hist = df[df["CLIENTE_NORM"].str.contains(nome_norm, na=False)]

    if hist.empty:
        st.warning("Cliente não encontrado.")
    else:
        atual = hist.sort_values("ULTIMA_ATUALIZACAO").iloc[-1]

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Situação Atual", atual["STATUS_BASE"])
        c2.metric("Corretor", atual["CORRETOR"])
        c3.metric("Equipe", atual["EQUIPE"])
        c4.metric("Origem", atual["ORIGEM_CRM"])

        st.subheader("🕒 Linha do Tempo do Cliente")

        st.dataframe(
            hist.sort_values("ULTIMA_ATUALIZACAO")[
                ["DATA", "STATUS_BASE", "OBSERVACOES"]
            ],
            use_container_width=True
        )
