# ---------------------------------------------------------
# BARRA LATERAL – BUSCA
# ---------------------------------------------------------
st.sidebar.title("🔎 Buscar Cliente")

tipo_busca = st.sidebar.radio("Buscar por:", ["Nome (parcial)", "CPF"])
termo = st.sidebar.text_input("Digite o nome ou CPF")
btn = st.sidebar.button("Buscar")

if not termo:
    st.info("Digite um nome ou CPF para buscar.")
    st.stop()

df_busca = df.copy()

# BUSCA POR NOME
if tipo_busca == "Nome (parcial)":
    termo_up = termo.upper().strip()
    df_busca = df_busca[df_busca["NOME_CLIENTE_BASE"].str.contains(termo_up, na=False)]
else:
    termo_cpf = limpar_cpf(termo)
    df_busca = df_busca[df_busca["CPF_CLIENTE_BASE"] == termo_cpf]

if df_busca.empty:
    st.warning("Nenhum cliente encontrado.")
    st.stop()

df_busca = df_busca.sort_values("DT_BASE")

# ---------------------------------------------------------
# RESUMO POR CLIENTE
# ---------------------------------------------------------
resumos = []

for chave, g in df_busca.groupby("CHAVE_CLIENTE"):
    g = g.sort_values("DT_BASE")

    ultimo = g.iloc[-1]
    status = g["STATUS_BASE"]

    analises_em = (status == "EM ANÁLISE").sum()
    reanalises = (status == "REANÁLISE").sum()
    aprovacoes = (status == "APROVADO").sum()

    # Venda gerada sobrepõe informada
    if (status == "VENDA GERADA").any():
        mask = status == "VENDA GERADA"
    else:
        mask = status == "VENDA INFORMADA"

    vendas = int(mask.sum())
    vgv = float(g.loc[mask, "VGV"].sum())

    resumo = {
        "CHAVE": chave,
        "NOME": ultimo["NOME_CLIENTE_BASE"],
        "CPF": ultimo["CPF_CLIENTE_BASE"] or "",
        "STATUS": ultimo["STATUS_BASE"],
        "ULT_DATA": ultimo["DT_BASE"],
        "EQUIPE": ultimo["EQUIPE"],
        "CORRETOR": ultimo["CORRETOR"],
        "ANALISES_EM": analises_em,
        "REANALISES": reanalises,
        "APROVACOES": aprovacoes,
        "VENDAS": vendas,
        "VGV": vgv,
        "OBS": ultima_observacao(g),
        "HIST": g
    }
    resumos.append(resumo)

st.markdown(f"### 🔍 {len(resumos)} cliente(s) encontrado(s)")

# ---------------------------------------------------------
# MOSTRAR CARDS
# ---------------------------------------------------------
for r in resumos:
    st.markdown("---")
    st.markdown(f"### 👤 {r['NOME']}")

    colA, colB = st.columns([2, 3])

    with colA:
        cpf_fmt = r["CPF"] if r["CPF"] else "NÃO INFORMADO"
        dt_fmt = r["ULT_DATA"].strftime("%d/%m/%Y")

        st.markdown(f"**CPF:** `{cpf_fmt}`")
        st.markdown(f"**Equipe:** {r['EQUIPE']}")
        st.markdown(f"**Corretor responsável:** `{r['CORRETOR']}`")
        st.markdown(f"**Último status:** {r['STATUS']}")
        st.markdown(f"**Última movimentação:** {dt_fmt}")
        st.markdown(f"**Última observação:** {r['OBS']}")

    with colB:
        c1, c2, c3 = st.columns(3)
        c1.metric("Análises (EM)", r["ANALISES_EM"])
        c2.metric("Reanálises", r["REANALISES"])
        c3.metric("Aprovações", r["APROVACOES"])

        c4, c5, c6 = st.columns(3)
        c4.metric("Vendas", r["VENDAS"])
        c5.metric("VGV Total", f"R$ {r['VGV']:,.2f}")
        c6.metric("Análises Totais", r["ANALISES_EM"] + r["REANALISES"])

    # HISTÓRICO
    st.markdown("#### 📜 Histórico do cliente")
    hist = r["HIST"].copy()
    hist["DATA"] = hist["DT_BASE"].dt.strftime("%d/%m/%Y")
    tabela = hist[["DATA", "STATUS_BASE", "EQUIPE", "CORRETOR", "OBSERVAÇÕES"]]

    st.dataframe(tabela, use_container_width=True, hide_index=True)
