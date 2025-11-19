# ---------------------------------------------------------
# EXIBIÇÃO – TABELA EM CIMA, GRÁFICO EMBAIXO
# ---------------------------------------------------------

st.markdown("#### 📋 Tabela detalhada do ranking por corretor")
st.dataframe(
    rank_cor.style.format(
        {
            "VGV": "R$ {:,.2f}".format,
            "TAXA_APROV_ANALISES": "{:.1f}%".format,
            "TAXA_VENDAS_ANALISES": "{:.1f}%".format,
        }
    ),
    use_container_width=True,
    hide_index=True,
)

st.markdown("#### 💰 VGV por corretor (período filtrado)")
chart_vgv = (
    alt.Chart(rank_cor)
    .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
    .encode(
        x=alt.X("VGV:Q", title="VGV (R$)"),
        y=alt.Y("CORRETOR:N", sort="-x", title="Corretor"),
        tooltip=[
            "CORRETOR",
            "ANALISES",
            "APROVACOES",
            "VENDAS",
            alt.Tooltip("VGV:Q", title="VGV"),
            alt.Tooltip(
                "TAXA_APROV_ANALISES:Q",
                title="% Aprov./Análises",
                format=".1f"
            ),
            alt.Tooltip(
                "TAXA_VENDAS_ANALISES:Q",
                title="% Vendas/Análises",
                format=".1f"
            ),
        ],
    )
    .properties(height=500)
)
st.altair_chart(chart_vgv, use_container_width=True)
