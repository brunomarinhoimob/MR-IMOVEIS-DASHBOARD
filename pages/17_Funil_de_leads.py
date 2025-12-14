import streamlit as st
import pandas as pd
import requests
from datetime import date

st.set_page_config(layout="wide")

# ===============================
# CONFIGURAÇÕES FIXAS
# ===============================
TOKEN = "SEU_TOKEN_DO_SUPREMO_AQUI"

SHEET_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1Ir_fPugLsfHNk6iH0XPCA6xM92bq8tTrn7UnunGRwCw"
    "/export?format=csv&gid=1574157905"
)

CRM_URL = "https://api.supremocrm.com.br/v1/leads"

# ===============================
# FUNÇÕES DE CARGA
# ===============================
@st.cache_data
def carregar_planilha():
    df = pd.read_csv(SHEET_URL, dtype=str)
    df.columns = df.columns.str.upper().str.strip()

    df["DATA"] = pd.to_datetime(df["DATA"], errors="coerce")
    df["CLIENTE"] = df["CLIENTE"].str.upper().str.strip()
    df["CORRETOR"] = df["CORRETOR"].str.upper().str.strip()

    return df


@st.cache_data
def carregar_crm():
    headers = {"Authorization": f"Bearer {TOKEN}"}
    page = 1
    dados = []

    while True:
        r = requests.get(
            CRM_URL,
            headers=headers,
            params={"page": page, "per_page": 1000},
            timeout=30
        )

        if r.status_code != 200:
            break

        bloco = r.json().get("dados", [])
        if not bloco:
            break

        dados.extend(bloco)
        page += 1

    df = pd.json_normalize(dados)
    df["CLIENTE"] = df["nome_pessoa"].str.upper().str.strip()

    return df[["CLIENTE", "nome_origem", "nome_campanha"]]


def normalizar_status(txt):
    if pd.isna(txt):
        return "OUTRO"

    t = txt.upper()

    if "DESIST" in t:
        return "DESISTIU"
    if "VENDA INFORMADA" in t:
        return "VENDA_INFORMADA"
    if "VENDA" in t:
        return "VENDA_GERADA"
    if "REANÁLISE" in t or "REANALISE" in t:
        return "REANALISE"
    if "APROVADO BACEN" in t:
        return "APROVADO_BACEN"
    if "APROVA" in t:
        return "APROVADO"
    if "REPROV" in t:
        return "REPROVADO"
    if "PEND" in t:
        return "PENDENCIA"
    if "ANÁLISE" in t or "ANALISE" in t:
        return "EM_ANALISE"

    return "OUTRO"


# ===============================
# CARGA DOS DADOS
# ===============================
df = carregar_planilha()
df["STATUS_BASE"] = df["SITUAÇÃO"].apply(normalizar_status)

df_crm = carregar_crm()
df = df.merge(df_crm, on="CLIENTE", how="left")

# ===============================
# FILTROS
# ===============================
st.sidebar.title("Filtros")

modo = st.sidebar.radio("Período", ["DIA", "DATA BASE"])

if modo == "DIA":
    ini, fim = st.sidebar.date_input(
        "Selecione o período",
        value=(df["DATA"].min().date(), df["DATA"].max().date())
    )
    df = df[(df["DATA"].dt.date >= ini) & (df["DATA"].dt.date <= fim)]
else:
    bases = st.sidebar.multiselect(
        "Data Base",
        sorted(df["DATA BASE"].dropna().unique())
    )
    if bases:
        df = df[df["DATA BASE"].isin(bases)]

origem = st.sidebar.selectbox(
    "Origem",
    ["Todas"] + sorted(df["nome_origem"].dropna().unique())
)

if origem != "Todas":
    df = df[df["nome_origem"] == origem]

# ===============================
# HISTÓRICO POR CLIENTE
# ===============================
df = df.sort_values("DATA")

clientes = df["CLIENTE"].unique()

def cliente_tem(cliente, status):
    return (df[(df["CLIENTE"] == cliente)]["STATUS_BASE"] == status).any()

total_leads = len(clientes)

analises = sum(cliente_tem(c, "EM_ANALISE") for c in clientes)
aprovados = sum(cliente_tem(c, "APROVADO") for c in clientes)

vendas = 0
for c in clientes:
    teve_venda = cliente_tem(c, "VENDA_GERADA") or cliente_tem(c, "VENDA_INFORMADA")
    desistiu = cliente_tem(c, "DESISTIU")

    if teve_venda and not desistiu:
        vendas += 1

# ===============================
# CARDS
# ===============================
c1, c2, c3, c4 = st.columns(4)

c1.metric("Leads", total_leads)
c2.metric("Análises", analises)
c3.metric("Aprovados", aprovados)
c4.metric("Vendas", vendas)

# ===============================
# CONVERSÕES
# ===============================
st.subheader("Conversões")

cc1, cc2, cc3 = st.columns(3)

cc1.metric(
    "Lead → Análise",
    f"{(analises / total_leads * 100):.1f}%" if total_leads else "0%"
)

cc2.metric(
    "Análise → Aprovação",
    f"{(aprovados / analises * 100):.1f}%" if analises else "0%"
)

cc3.metric(
    "Aprovação → Venda",
    f"{(vendas / aprovados * 100):.1f}%" if aprovados else "0%"
)

# ===============================
# TABELA FINAL
# ===============================
st.subheader("Leads no período selecionado")

st.dataframe(
    df.sort_values("DATA", ascending=False),
    use_container_width=True
)
