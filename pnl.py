# Seção PNL
st.subheader(f"PNL por assessor em {mes_selecionado}")

df_pnl = df_ass_mes[df_ass_mes["Mes_Ano"] == mes_selecionado].copy()
if df_pnl.empty:
    st.warning("Nenhum dado para calcular PNL neste mês.")
else:
    # Calcula repasse, quanto vai para o assessor e quanto fica na empresa
    df_pnl["Repasse"] = df_pnl["Assessor"].apply(get_repasse)
    df_pnl["Para_Assessor"] = df_pnl["Comissao"] * df_pnl["Repasse"]
    df_pnl["Para_Empresa"] = df_pnl["Comissao"] - df_pnl["Para_Assessor"]

    df_pnl = df_pnl.sort_values("Comissao", ascending=False)

    # Tabela formatada
    tabela_pnl = df_pnl[[
        "Assessor",
        "Comissao",
        "Repasse",
        "Para_Assessor",
        "Para_Empresa"
    ]].reset_index(drop=True)

    # Formatação brasileira de moeda
    for col in ["Comissao", "Para_Assessor", "Para_Empresa"]:
        tabela_pnl[col] = tabela_pnl[col].apply(
            lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )

    # Formatar repasse em percentual
    tabela_pnl["Repasse"] = tabela_pnl["Repasse"].apply(
        lambda x: f"{x*100:.0f}%"
    )

    col_p1, col_p2 = st.columns([2, 1])

    with col_p1:
        # Gráfico de barras agrupadas mostrando PNL (sem formatação)
        df_plot = df_pnl.melt(
            id_vars=["Assessor"],
            value_vars=["Para_Assessor", "Para_Empresa"],
            var_name="Tipo",
            value_name="Valor"
        )
        df_plot["Tipo"] = df_plot["Tipo"].replace({
            "Para_Assessor": "Para o assessor",
            "Para_Empresa": "Para a empresa"
        })

        fig_pnl = px.bar(
            df_plot,
            x="Assessor",
            y="Valor",
            color="Tipo",
            barmode="group",
            labels={"Valor": "Valor", "Assessor": "Assessor", "Tipo": "Tipo"},
            title="PNL por assessor no mês selecionado"
        )
        st.plotly_chart(fig_pnl, use_container_width=True)

    with col_p2:
        st.markdown("Tabela de PNL")
        st.dataframe(tabela_pnl)
