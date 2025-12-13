import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(
    page_title="Funil de Leads",
    layout="wide"
)

# =========================================================
# CARGA DE DADOS (IDÊNTICA À 99_PAGINA_TESTE)
# =========================================================
@st.cache_data(ttl=1800)
def carregar_dados():
    url = "COLE_AQUI_EXATAMENTE_O_MESMO_LINK_DA_99_PAGINA_TESTE"
    df = pd.read_csv(url, dtype=str)

    df.columns = df.columns.str.upper().str.strip()

    df["CLIENTE"] = df["CLIENTE"].str.upper().str.strip()
    df["CORRETOR"] = df["CORRETOR"].str.upper().str.strip()
    df["EQUIPE"] = df["EQUIPE"].str.upper().str.strip()
    df["SITUAÇÃO"] = df["SITUAÇÃO"].str.upper().str.strip()

    df["ORIGEM_FINAL"] = (
        df.get("ORIGEM")
        .fillna("SEM CADASTRO NO CRM")
        .astype(str)
        .str.upper()
        .str.strip()
    )

    df["DATA"] = pd.to_datetime(df["DATA"], errors="coerce")

    return df


df = carregar_dados()

# =========================================================
# FILTROS GERAIS
# =========================================================
st.title("📊 Funil de Leads – Origem, Status e Conversão")

col1, col2, col3, col4 = st.columns(4)

with col1:
    data_inicio, data_fim = st.date_input(
        "Período (DATA)",
        value=(df["DATA"].min().date(), df["DATA"].max().date())
    )

with col2:
    datas_base = sorted(df["DATA BASE"].dropna().unique())
    data_base_sel = st.multiselect("Data Base", datas_base, default=datas_base)

with col3:
    equipes = ["TODAS"] + sorted(df["EQUIPE"].dropna().unique())
    equipe_sel = st.selectbox("Equipe", equipes)

with col4:
    corretores = ["TODOS"] + sorted(df["CORRETOR"].dropna().unique())
    corretor_sel = st.selectbox("Corretor", corretores)

# Aplica filtros
df_f = df[
    (df["DATA"].dt.date >= data_inicio) &
    (df["DATA"].dt.date <= data_fim) &
    (df["DATA BASE"].isin(data_base_sel))
]

if equipe_sel != "TODAS":
    df_f = df_f[df_f["EQUIPE"] == equipe_sel]

if corretor_sel != "TODOS":
    df_f = df_f[df_f["CORRETOR"] == corretor_sel]

# =========================================================
# FUNIL ATUAL (STATUS)
# =========================================================
st.markdown("---")
st.subheader("📌 Status Atual do Funil")

status_counts = df_f.groupby("SITUAÇÃO")["CLIENTE"].nunique()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Em Análise", status_counts.get("EM ANÁLISE", 0))
c2.metric("Reanálise", status_counts.get("REANÁLISE", 0))
c3.metric("Aprovados", status_counts.get("APROVADO", 0))
c4.metric("Aprovados Bacen", status_counts.get("APROVADO BACEN", 0))

c5, c6, c7, c8 = st.columns(4)
c5.metric("Pendências", status_counts.get("PENDÊNCIA", 0))
c6.metric("Reprovados", status_counts.get("REPROVAÇÃO", 0))
c7.metric("Vendas Informadas", status_counts.get("VENDA INFORMADA", 0))
c8.metric("Vendas Geradas", status_counts.get("VENDA GERADA", 0))

st.metric("Leads Ativos no Funil", df_f["CLIENTE"].nunique())

# =========================================================
# PERFORMANCE POR ORIGEM
# =========================================================
st.markdown("---")
st.subheader("🎯 Performance e Conversão por Origem")

origens = ["TODAS"] + sorted(df_f["ORIGEM_FINAL"].unique())
origem_sel = st.selectbox("Origem", origens)

tipo_venda = st.radio(
    "Tipo de Venda para Conversão",
    ["Vendas Informadas + Geradas", "Apenas Vendas Geradas"]
)

df_o = df_f.copy()
if origem_sel != "TODAS":
    df_o = df_o[df_o["ORIGEM_FINAL"] == origem_sel]

# Última atualização por lead
df_o = (
    df_o.sort_values("DATA")
        .groupby("CLIENTE", as_index=False)
        .last()
)

# Regra: venda gerada elimina venda informada
df_o.loc[df_o["SITUAÇÃO"] == "VENDA GERADA", "SITUAÇÃO"] = "VENDA GERADA"

leads = df_o["CLIENTE"].nunique()
analises = df_o[df_o["SITUAÇÃO"] == "EM ANÁLISE"]["CLIENTE"].nunique()
reanalis = df_o[df_o["SITUAÇÃO"] == "REANÁLISE"]["CLIENTE"].nunique()

if tipo_venda == "Apenas Vendas Geradas":
    vendas = df_o[df_o["SITUAÇÃO"] == "VENDA GERADA"]["CLIENTE"].nunique()
else:
    vendas = df_o[df_o["SITUAÇÃO"].isin(["VENDA GERADA", "VENDA INFORMADA"])]["CLIENTE"].nunique()

aprovados = df_o[df_o["SITUAÇÃO"].isin(["APROVADO", "APROVADO BACEN"])]["CLIENTE"].nunique()

# Conversões (sempre baseadas em EM ANÁLISE)
conv_lead_analise = (analises / leads * 100) if leads else 0
conv_analise_aprov = (aprovados / analises * 100) if analises else 0
conv_analise_venda = (vendas / analises * 100) if analises else 0
conv_aprov_venda = (vendas / aprovados * 100) if aprovados else 0

c1, c2, c3, c4 = st.columns(4)
c1.metric("Leads", leads)
c2.metric("Análises", analises)
c3.metric("Reanálises", reanalis)
c4.metric("Vendas", vendas)

c5, c6, c7, c8 = st.columns(4)
c5.metric("Lead → Análise", f"{conv_lead_analise:.1f}%")
c6.metric("Análise → Aprovação", f"{conv_analise_aprov:.1f}%")
c7.metric("Análise → Venda", f"{conv_analise_venda:.1f}%")
c8.metric("Aprovação → Venda", f"{conv_aprov_venda:.1f}%")

# =========================================================
# TABELA – ÚLTIMO STATUS DO LEAD
# =========================================================
st.markdown("---")
st.subheader("📋 Leads da Origem Selecionada (Última Atualização)")

st.dataframe(
    df_o[["CLIENTE", "CORRETOR", "EQUIPE", "SITUAÇÃO", "DATA"]]
        .sort_values("DATA", ascending=False),
    use_container_width=True
)

# =========================================================
# AUDITORIA DE CLIENTE
# =========================================================
st.markdown("---")
st.subheader("🔍 Auditoria Rápida de Cliente")

modo_busca = st.radio("Buscar por:", ["Nome", "CPF"], horizontal=True)
busca = st.text_input("Digite para buscar")

if busca:
    if modo_busca == "Nome":
        df_c = df[df["CLIENTE"].str.contains(busca.upper(), na=False)]
    else:
        df_c = df[df["CPF"].astype(str).str.contains(busca, na=False)]

    if not df_c.empty:
        cliente = df_c.iloc[0]

        st.markdown(f"### 👤 {cliente['CLIENTE']}")
        st.write(f"**CPF:** {cliente.get('CPF', 'NÃO INFORMADO')}")
        st.write(f"**Situação atual:** {cliente['SITUAÇÃO']}")
        st.write(f"**Última movimentação:** {cliente['DATA'].date()}")
        st.write(f"**Corretor:** {cliente['CORRETOR']}")
        st.write(f"**Construtora:** {cliente.get('CONSTRUTORA', '-')}")
        st.write(f"**Empreendimento:** {cliente.get('EMPREENDIMENTO', '-')}")

        st.markdown("### 📜 Histórico do Cliente")
        st.dataframe(
            df_c.sort_values("DATA")[["DATA", "SITUAÇÃO", "OBSERVAÇÕES"]],
            use_container_width=True
        )
