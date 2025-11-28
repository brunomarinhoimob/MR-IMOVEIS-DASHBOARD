import streamlit as st
import pandas as pd
from datetime import date

from app_dashboard import carregar_dados_planilha

# ---------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA
# ---------------------------------------------------------
st.set_page_config(
    page_title="Carteira de Clientes – MR Imóveis",
    page_icon="📂",
    layout="wide",
)

# ---------------------------------------------------------
# LOGO E TÍTULO
# ---------------------------------------------------------
col_logo, col_tit = st.columns([1, 4])
with col_logo:
    try:
        st.image("logo_mr.png", use_column_width=True)
    except Exception:
        st.write("MR Imóveis")
with col_tit:
    st.markdown("## 📂 Carteira de Clientes por Equipe / Corretor")
    st.caption(
        "Visualize todos os clientes de uma equipe ou corretor em um período.\n\n"
        "A situação atual de cada cliente respeita a regra:\n"
        "- Se houver **VENDA GERADA** ou **VENDA INFORMADA** depois do último `DESISTIU`, "
        "a venda é considerada a situação atual.\n"
        "- Se depois da venda houver um `DESISTIU`, esse `DESISTIU` zera o ciclo e passa a valer o que vier depois."
    )

# ---------------------------------------------------------
# CARREGAMENTO E TRATAMENTO DA BASE
# ---------------------------------------------------------
@st.cache_data(ttl=60)
def carregar_dados_carteira() -> pd.DataFrame:
    df = carregar_dados_planilha()
    if df is None or df.empty:
        return pd.DataFrame()

    df.columns = [c.strip().upper() for c in df.columns]

    # DATA / DIA
    if "DIA" in df.columns:
        df["DIA"] = pd.to_datetime(df["DIA"], errors="coerce")
    elif "DATA" in df.columns:
        df["DIA"] = pd.to_datetime(df["DATA"], errors="coerce")
    else:
        df["DIA"] = pd.NaT

    # NOME / CPF BASE (garante colunas existentes)
    possiveis_nome = ["NOME_CLIENTE_BASE", "NOME", "CLIENTE", "NOME CLIENTE", "NOME DO CLIENTE"]
    possiveis_cpf = ["CPF_CLIENTE_BASE", "CPF", "CPF CLIENTE", "CPF DO CLIENTE"]

    col_nome = next((c for c in possiveis_nome if c in df.columns), None)
    col_cpf = next((c for c in possiveis_cpf if c in df.columns), None)

    if col_nome:
        df["NOME_CLIENTE_BASE"] = (
            df[col_nome].fillna("NÃO INFORMADO").astype(str).str.upper().str.strip()
        )
    else:
        df["NOME_CLIENTE_BASE"] = "NÃO INFORMADO"

    if col_cpf:
        df["CPF_CLIENTE_BASE"] = (
            df[col_cpf]
            .fillna("")
            .astype(str)
            .str.replace(r"\D", "", regex=True)
            .str.strip()
        )
    else:
        df["CPF_CLIENTE_BASE"] = ""

    # EQUIPE / CORRETOR
    if "EQUIPE" in df.columns:
        df["EQUIPE"] = (
            df["EQUIPE"]
            .fillna("NÃO INFORMADO")
            .astype(str)
            .str.upper()
            .str.strip()
        )
    else:
        df["EQUIPE"] = "NÃO INFORMADO"

    if "CORRETOR" in df.columns:
        df["CORRETOR"] = (
            df["CORRETOR"]
            .fillna("NÃO INFORMADO")
            .astype(str)
            .str.upper()
            .str.strip()
        )
    else:
        df["CORRETOR"] = "NÃO INFORMADO"

    # CONSTRUTORA / EMPREENDIMENTO (se existirem)
    if "CONSTRUTORA" in df.columns:
        df["CONSTRUTORA"] = (
            df["CONSTRUTORA"].fillna("").astype(str).str.upper().str.strip()
        )
    else:
        df["CONSTRUTORA"] = ""

    if "EMPREENDIMENTO" in df.columns:
        df["EMPREENDIMENTO"] = (
            df["EMPREENDIMENTO"].fillna("").astype(str).str.upper().str.strip()
        )
    else:
        df["EMPREENDIMENTO"] = ""

    # SITUAÇÃO ORIGINAL (texto da planilha)
    possiveis_cols_situacao = [
        "SITUAÇÃO",
        "SITUAÇÃO ATUAL",
        "SITUACAO",
        "SITUACAO ATUAL",
        "STATUS",
    ]
    col_situacao = next((c for c in possiveis_cols_situacao if c in df.columns), None)
    if col_situacao:
        df["SITUACAO_ORIGINAL"] = (
            df[col_situacao].fillna("").astype(str).str.strip()
        )
    else:
        if "STATUS_BASE" in df.columns:
            df["SITUACAO_ORIGINAL"] = df["STATUS_BASE"].fillna("").astype(str)
        else:
            df["SITUACAO_ORIGINAL"] = ""

    # STATUS_BASE (já vem classificado do app_dashboard, mas garante existência)
    if "STATUS_BASE" not in df.columns:
        df["STATUS_BASE"] = df["SITUACAO_ORIGINAL"].str.upper()

    # VGV (já vem do app_dashboard; se não, cria zerado)
    if "VGV" not in df.columns:
        df["VGV"] = 0.0
    df["VGV"] = pd.to_numeric(df["VGV"], errors="coerce").fillna(0.0)

    # CHAVE CLIENTE
    df["CHAVE_CLIENTE"] = (
        df["NOME_CLIENTE_BASE"].fillna("NÃO INFORMADO")
        + " | "
        + df["CPF_CLIENTE_BASE"].fillna("")
    )

    return df


df = carregar_dados_carteira()
if df is None or df.empty:
    st.error("Não foi possível carregar a base de clientes da planilha.")
    st.stop()

# ---------------------------------------------------------
# FUNÇÕES DE APOIO
# ---------------------------------------------------------
def format_currency(valor: float) -> str:
    return (
        f"R$ {valor:,.2f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )

def obter_linha_situacao_atual(grupo: pd.DataFrame) -> pd.Series:
    """
    Regra:
    - Considera apenas o trecho após o último DESISTIU (se houver).
    - Dentro desse trecho, se houver VENDA GERADA / VENDA INFORMADA, pega a última venda.
    - Caso contrário, pega a última linha do trecho.
    """
    if grupo.empty:
        return pd.Series(dtype="object")

    df_cli = grupo.sort_values("DIA").copy()

    # identifica último 'DESIST' na situação original
    s_orig = df_cli["SITUACAO_ORIGINAL"].fillna("").astype(str).str.upper()
    idx_desist = s_orig[s_orig.str.contains("DESIST")].index

    if len(idx_desist) > 0:
        last_reset_idx = idx_desist[-1]
        df_seg = df_cli.loc[last_reset_idx:]
    else:
        df_seg = df_cli

    # procura vendas no segmento
    status_upper = df_seg["STATUS_BASE"].fillna("").astype(str).str.upper()
    mask_venda = status_upper.isin(["VENDA GERADA", "VENDA INFORMADA"])

    if mask_venda.any():
        return df_seg.loc[mask_venda].iloc[-1]
    else:
        return df_seg.iloc[-1]

# ---------------------------------------------------------
# FILTROS (SIDEBAR)
# ---------------------------------------------------------
st.sidebar.title("Filtros – Carteira de Clientes")

data_min = df["DIA"].min()
data_max = df["DIA"].max()
hoje = date.today()

if pd.isna(data_min) or pd.isna(data_max):
    data_min = hoje
    data_max = hoje

periodo = st.sidebar.date_input(
    "Período de movimentação",
    value=(data_min, data_max),
    min_value=data_min,
    max_value=data_max,
)

if isinstance(periodo, (tuple, list)):
    data_ini, data_fim = periodo
else:
    data_ini = periodo
    data_fim = periodo

if data_ini > data_fim:
    st.sidebar.error("Data inicial maior que data final.")
    st.stop()

mask_periodo = (df["DIA"] >= pd.to_datetime(data_ini)) & (df["DIA"] <= pd.to_datetime(data_fim))
df_filtro = df[mask_periodo].copy()

if df_filtro.empty:
    st.info("Nenhum cliente encontrado no período selecionado.")
    st.stop()

equipe_opcoes = ["Todas"] + sorted(df_filtro["EQUIPE"].dropna().unique().tolist())
equipe_sel = st.sidebar.selectbox("Equipe:", options=equipe_opcoes, index=0)

if equipe_sel != "Todas":
    df_filtro = df_filtro[df_filtro["EQUIPE"] == equipe_sel].copy()

corretor_opcoes = ["Todos"] + sorted(df_filtro["CORRETOR"].dropna().unique().tolist())
corretor_sel = st.sidebar.selectbox("Corretor:", options=corretor_opcoes, index=0)

if corretor_sel != "Todos":
    df_filtro = df_filtro[df_filtro["CORRETOR"] == corretor_sel].copy()

if df_filtro.empty:
    st.info("Nenhum cliente encontrado com os filtros selecionados.")
    st.stop()

st.markdown("---")

# ---------------------------------------------------------
# RESUMO POR CLIENTE (CARTEIRA)
# ---------------------------------------------------------
st.markdown("### 🧾 Carteira de clientes do período")

# agrupa por cliente + corretor
grupos = df_filtro.groupby(["CHAVE_CLIENTE", "CORRETOR"], as_index=False)

linhas_resumo = []
for (_, corretor), grupo in grupos:
    linha_atual = obter_linha_situacao_atual(grupo)

    nome = linha_atual.get("NOME_CLIENTE_BASE", "NÃO INFORMADO")
    cpf = linha_atual.get("CPF_CLIENTE_BASE", "")
    equipe = linha_atual.get("EQUIPE", "NÃO INFORMADO")
    corretor_nome = linha_atual.get("CORRETOR", "NÃO INFORMADO")
    construtora = linha_atual.get("CONSTRUTORA", "")
    empreendimento = linha_atual.get("EMPREENDIMENTO", "")
    situacao_atual = linha_atual.get("SITUACAO_ORIGINAL", "")
    data_ult = linha_atual.get("DIA", pd.NaT)
    vgv_hist = grupo["VGV"].sum()

    status_hist = grupo["STATUS_BASE"].fillna("").astype(str).str.upper()
    analises = status_hist.isin(["EM ANÁLISE", "REANÁLISE"]).sum()
    aprovacoes = (status_hist == "APROVADO").sum()
    vendas_hist = status_hist.isin(["VENDA GERADA", "VENDA INFORMADA"]).sum()

    linhas_resumo.append(
        {
            "Cliente": nome,
            "CPF": cpf,
            "Equipe": equipe,
            "Corretor": corretor_nome,
            "Situação atual": situacao_atual,
            "Última movimentação": data_ult,
            "Construtora": construtora,
            "Empreendimento": empreendimento,
            "Análises (histórico)": int(analises),
            "Aprovações (histórico)": int(aprovacoes),
            "Vendas (histórico)": int(vendas_hist),
            "VGV histórico": float(vgv_hist),
        }
    )

df_resumo = pd.DataFrame(linhas_resumo)

if df_resumo.empty:
    st.info("Nenhum cliente encontrado para montar a carteira.")
    st.stop()

# formatação
df_resumo["Última movimentação"] = pd.to_datetime(
    df_resumo["Última movimentação"], errors="coerce"
).dt.strftime("%d/%m/%Y")

df_resumo["VGV histórico"] = df_resumo["VGV histórico"].apply(format_currency)

# ordenação padrão: corretor, situação, cliente
df_resumo = df_resumo.sort_values(
    by=["Corretor", "Situação atual", "Cliente"],
    ascending=[True, True, True],
)

qtd_clientes = len(df_resumo)
st.caption(
    f"Foram encontrados **{qtd_clientes}** clientes únicos para os filtros selecionados."
)

st.dataframe(
    df_resumo,
    use_container_width=True,
    hide_index=True,
)
