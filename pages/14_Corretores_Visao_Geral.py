@st.cache_data(ttl=60)
def carregar_base():
    df = pd.read_csv(CSV_URL)

    df.columns = [c.upper().strip() for c in df.columns]

    # DIA
    if "DATA" in df.columns:
        df["DIA"] = limpar_data(df["DATA"])
    elif "DIA" in df.columns:
        df["DIA"] = limpar_data(df["DIA"])
    else:
        df["DIA"] = pd.NaT

    # NOME CLIENTE
    possiveis_nomes = ["NOME", "CLIENTE", "NOME CLIENTE", "NOME DO CLIENTE"]
    col_nome = next((c for c in possiveis_nomes if c in df.columns), None)
    df["NOME_CLIENTE_BASE"] = (
        df[col_nome].astype(str).str.upper().str.strip() if col_nome else "NÃO INFORMADO"
    )

    # CPF
    possiveis_cpf = ["CPF", "CPF CLIENTE", "CPF DO CLIENTE"]
    col_cpf = next((c for c in possiveis_cpf if c in df.columns), None)
    df["CPF_CLIENTE_BASE"] = (
        df[col_cpf].astype(str).str.replace(r"\D", "", regex=True)
        if col_cpf else ""
    )

    # EQUIPE
    if "EQUIPE" in df.columns:
        df["EQUIPE"] = df["EQUIPE"].astype(str).str.upper().str.strip()
    else:
        df["EQUIPE"] = "NÃO INFORMADO"

    # CORRETOR
    if "CORRETOR" in df.columns:
        df["CORRETOR"] = df["CORRETOR"].astype(str).str.upper().str.strip()
    else:
        df["CORRETOR"] = "NÃO INFORMADO"

    # STATUS – corrigido 🔥
    possiveis_status = ["STATUS", "SITUAÇÃO", "SITUAÇÃO ATUAL", "SITUACAO", "SITUACAO ATUAL"]

    col_status = next((c for c in possiveis_status if c in df.columns), None)

    df["STATUS_BASE"] = ""

    if col_status:
        s = df[col_status].fillna("").astype(str).str.upper()

        df.loc[s.str.contains("VENDA GERADA"), "STATUS_BASE"] = "VENDA GERADA"
        df.loc[s.str.contains("VENDA INFORMADA"), "STATUS_BASE"] = "VENDA INFORMADA"
        df.loc[s.str.contains("APROV"), "STATUS_BASE"] = "APROVADO"
        df.loc[s.str.contains("REPROV"), "STATUS_BASE"] = "REPROVADO"
        df.loc[s.str.contains("ANÁLISE"), "STATUS_BASE"] = "EM ANÁLISE"
        df.loc[s.str.contains("REANÁLISE"), "STATUS_BASE"] = "REANÁLISE"
    else:
        df["STATUS_BASE"] = "NÃO INFORMADO"

    # VGV
    if "OBSERVAÇÕES" in df.columns:
        df["VGV"] = pd.to_numeric(df["OBSERVAÇÕES"], errors="coerce").fillna(0)
    else:
        df["VGV"] = 0

    return df
