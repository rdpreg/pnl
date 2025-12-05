import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from io import BytesIO

st.set_page_config(
    page_title="Dashboard de Comissões por Assessor",
    layout="wide"
)

st.title("Dashboard de Comissões por Assessor")

st.markdown(
    """
Este app lê os relatórios B2B em Excel, trata a base e monta um painel 
de acompanhamento da evolução mensal das comissões por assessor.
"""
)

uploaded_files = st.file_uploader(
    "Envie um ou mais relatórios B2B em Excel",
    type=["xlsx", "xls"],
    accept_multiple_files=True
)

# Dicionário de repasse por assessor para a seção PNL
# use sempre o nome em maiúsculas, igual vem na planilha tratada
# Dicionário de repasse por assessor para a seção PNL
# use sempre o nome em maiúsculas, igual vem na planilha tratada
repasse_por_assessor = {
    "ABRAAO RIBEIRO DA SILVA": 0.70,
    "ARTHUR MOTA RODRIGUES": 0.50,
    "BRUNO TERRA DE ASSUNCAO": 0.60,
    "CAIO DOS SANTOS CARLOS": 0.40,
    "CARLOS ALEXANDRE IGNACIO DA SILVA": 0.50,
    "CARLOS EDUARDO CAMERA LOUREIRO PINTO": 0.60,
    "CELSO LUIZ DE OLIVEIRA JUNIOR": 0.60,
    "DANIEL MAGRINA GUIMARAES": 0.40,
    "EDUARDO KAZAY": 0.70,
    "EDUARDO MEYER": 0.70,
    "EMANUEL NASCIMENTO CAVALCANTI": 0.80,
    "EMERSON CERBINO DOBLAS": 0.50,
    "EMERSON VIEIRA DE FARIAS JUNIOR": 0.70,
    "FABIANO JOSE RAMOS BITTENCOURT": 0.75,
    "FLAVIO LUIZ NUNES DE BARROS": 0.85,
    "JADER DA MOTA MENDONCA": 0.80,
    "JOAO VITOR ARAUJO SACCARDO": 0.50,
    "JOICE ELIANA BRITES DE OLIVEIRA": 0.60,
    "JONATHAN DA CUNHA VALENTE": 0.80,
    "LEONARDO BARBOSA FRISONI": 0.80,
    "LUCIANO HENRIQUE MATTOS DE ALMEIDA": 0.80,
    "LUIZ FILIPE COSTA GARCIA": 0.80,
    "MANSUR PAPICHO MIRANDA": 0.90,
    "OTAVIO NUNES CARDOZO JÚNIOR": 0.60,  # se na base vier sem acento, posso duplicar a chave
    "PEDRO AMMAR FORATO": 0.80,
    "PEDRO BORGERTH TEIXEIRA DE LUCA": 0.70,
    "RAFAEL MADALENA MARTINS": 0.80,
    "ROBERTO DE MATTOS BRUNER": 0.70,
    "RODRIGO RODRIGUES MARINO": 0.70,
    "RUAN MARINS NOGUEIRA": 0.80,
    "THIAGO KEMPER RICCIOPPO": 0.90,
    "TIAGO DE CARVALHO RAMOS": 0.60,
    "VANESSA PEREIRA DE OLIVEIRA": 0.70,
}

default_repasse = 0.70


ALIQUOTA_IMPOSTO = 0.1953
FATOR_LIQUIDO = 1 - ALIQUOTA_IMPOSTO  # 0.8047


def get_repasse(assessor):
    if pd.isna(assessor):
        return default_repasse
    chave = str(assessor).strip().upper()
    return repasse_por_assessor.get(chave, default_repasse)


def formata_brl(x):
    return f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def tratar_relatorio(file, competencia_date):
    """
    Lê o relatório, pega apenas as colunas:
    5 -> Assessor
    6 -> Conta
    7 -> Receita Líquida
    8 -> Comissão

    Preenche o nome do assessor para baixo.
    Remove cabeçalhos, linhas vazias e as linhas de subtotal
    (primeira linha de cada assessor, onde Conta está vazia).
    Adiciona coluna de competência (mês e ano).
    """
    df = pd.read_excel(file)

    # Seleciona colunas 5, 6, 7, 8 (índices 5, 6, 7, 8)
    df2 = df.iloc[:, [5, 6, 7, 8]].copy()
    df2.columns = ["Assessor", "Conta", "Receita_Liquida", "Comissao"]

    # Preencher assessor para baixo
    df2["Assessor"] = df2["Assessor"].ffill()

    # Remover cabeçalho interno e linhas com assessor vazio
    df2 = df2[df2["Assessor"].notna()]
    df2 = df2[df2["Assessor"] != "Assessor Principal"]

    # Converter colunas numéricas
    df2["Receita_Liquida"] = pd.to_numeric(df2["Receita_Liquida"], errors="coerce")
    df2["Comissao"] = pd.to_numeric(df2["Comissao"], errors="coerce")

    # Remover linhas de subtotal: Conta vazia
    df2 = df2[df2["Conta"].notna()]

    # Remover linhas totalmente sem valores numéricos
    df2 = df2[~(df2["Receita_Liquida"].isna() & df2["Comissao"].isna())]

    # Adicionar competência
    competencia_ts = pd.to_datetime(competencia_date)
    df2["Competencia"] = competencia_ts
    df2["Ano"] = df2["Competencia"].dt.year
    df2["Mes"] = df2["Competencia"].dt.month
    df2["Mes_Ano"] = df2["Competencia"].dt.strftime("%Y-%m")

    return df2


all_dfs = []

if uploaded_files:
    st.subheader("Defina a competência de cada arquivo")

    ano_atual = date.today().year
    anos_possiveis = list(range(ano_atual - 5, ano_atual + 1))

    meses_dict = {
        1: "Jan",
        2: "Fev",
        3: "Mar",
        4: "Abr",
        5: "Mai",
        6: "Jun",
        7: "Jul",
        8: "Ago",
        9: "Set",
        10: "Out",
        11: "Nov",
        12: "Dez",
    }

    for file in uploaded_files:
        st.markdown(f"**Arquivo:** {file.name}")
        col1, col2 = st.columns(2)

        with col1:
            ano_sel = st.selectbox(
                f"Ano do relatório para {file.name}",
                options=anos_possiveis,
                index=len(anos_possiveis) - 1,
                key=f"ano_{file.name}"
            )

        with col2:
            mes_sel = st.selectbox(
                f"Mês do relatório para {file.name}",
                options=list(meses_dict.keys()),
                format_func=lambda m: meses_dict[m],
                index=date.today().month - 1,
                key=f"mes_{file.name}"
            )

        competencia_input = date(ano_sel, mes_sel, 1)
        df_tratado = tratar_relatorio(file, competencia_input)
        all_dfs.append(df_tratado)

if not uploaded_files:
    st.info("Envie ao menos um arquivo para iniciar o dashboard.")

if all_dfs:
    base = pd.concat(all_dfs, ignore_index=True)

    st.subheader("Base consolidada tratada")

    with st.expander("Ver tabela completa"):
        st.dataframe(base)

    # Função para gerar Excel da base consolidada
    def to_excel_bytes(df):
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="Base")
        buffer.seek(0)
        return buffer

    excel_bytes = to_excel_bytes(base)
    st.download_button(
        label="Baixar base consolidada em Excel",
        data=excel_bytes,
        file_name="base_comissoes_consolidada.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    st.markdown("---")

    # Agregações para os gráficos
    df_mes = (
        base.groupby("Mes_Ano", as_index=False)["Comissao"].sum()
        .sort_values("Mes_Ano")
    )

    # Para PNL do mês e acumulado no ano, já deixo Ano junto
    df_ass_mes = (
        base.groupby(["Ano", "Mes_Ano", "Assessor"], as_index=False)["Comissao"].sum()
        .sort_values(["Ano", "Mes_Ano", "Assessor"])
    )

    st.subheader("Filtros")

    col_f1, col_f2 = st.columns(2)

    with col_f1:
        assessores_unicos = sorted(base["Assessor"].unique())
        assessores_selecionados = st.multiselect(
            "Selecione os assessores",
            options=assessores_unicos,
            default=assessores_unicos
        )

    with col_f2:
        meses_unicos = sorted(df_mes["Mes_Ano"].unique())
        mes_selecionado = st.selectbox(
            "Selecione um mês para ver o ranking e a PNL",
            options=meses_unicos
        )

    df_ass_mes_filtrado = df_ass_mes[
        df_ass_mes["Assessor"].isin(assessores_selecionados)
    ]

    st.subheader("Evolução mensal da comissão total")
    fig_total = px.line(
        df_mes,
        x="Mes_Ano",
        y="Comissao",
        markers=True,
        labels={"Mes_Ano": "Mês", "Comissao": "Comissão"},
        title="Comissão total por mês"
    )
    st.plotly_chart(fig_total, use_container_width=True)

    st.subheader("Evolução da comissão por assessor")
    if not df_ass_mes_filtrado.empty:
        fig_ass = px.line(
            df_ass_mes_filtrado,
            x="Mes_Ano",
            y="Comissao",
            color="Assessor",
            markers=True,
            labels={"Mes_Ano": "Mês", "Comissao": "Comissão"},
            title="Comissão por assessor ao longo dos meses"
        )
        st.plotly_chart(fig_ass, use_container_width=True)
    else:
        st.warning("Nenhum dado para os assessores selecionados.")

    # Ranking com formatação BRL
    st.subheader(f"Ranking de assessores em {mes_selecionado}")

    df_ranking = (
        df_ass_mes[df_ass_mes["Mes_Ano"] == mes_selecionado]
        .sort_values("Comissao", ascending=False)
    ).copy()

    tabela_ranking = df_ranking.copy()
    tabela_ranking["Comissao"] = tabela_ranking["Comissao"].apply(formata_brl)

    col_g1, col_g2 = st.columns([2, 1])

    with col_g1:
        fig_rank = px.bar(
            df_ranking,
            x="Comissao",
            y="Assessor",
            orientation="h",
            labels={"Comissao": "Comissão", "Assessor": "Assessor"},
            title=f"Comissão por assessor em {mes_selecionado}"
        )
        st.plotly_chart(fig_rank, use_container_width=True)

    with col_g2:
        st.markdown("Tabela de ranking")
        st.dataframe(tabela_ranking.reset_index(drop=True))

    st.markdown("---")

    # Seção PNL do mês
    st.subheader(f"PNL por assessor em {mes_selecionado}")

    df_pnl_mes = df_ass_mes[df_ass_mes["Mes_Ano"] == mes_selecionado].copy()
    if df_pnl_mes.empty:
        st.warning("Nenhum dado para calcular PNL neste mês.")
    else:
        # Comissão líquida após imposto
        df_pnl_mes["Comissao_Liquida"] = df_pnl_mes["Comissao"] * FATOR_LIQUIDO

        # Repasse em cima da comissão líquida
        df_pnl_mes["Repasse"] = df_pnl_mes["Assessor"].apply(get_repasse)
        df_pnl_mes["Para_Assessor"] = df_pnl_mes["Comissao_Liquida"] * df_pnl_mes["Repasse"]
        df_pnl_mes["Para_Empresa"] = df_pnl_mes["Comissao_Liquida"] - df_pnl_mes["Para_Assessor"]

        df_pnl_mes = df_pnl_mes.sort_values("Comissao_Liquida", ascending=False)

        tabela_pnl_mes = pd.DataFrame({
            "Assessor": df_pnl_mes["Assessor"],
            "Comissão bruta": df_pnl_mes["Comissao"],
            "Comissão líquida": df_pnl_mes["Comissao_Liquida"],
            "Repasse": df_pnl_mes["Repasse"],
            "Para assessor": df_pnl_mes["Para_Assessor"],
            "Para empresa": df_pnl_mes["Para_Empresa"],
        }).reset_index(drop=True)

        for col in ["Comissão bruta", "Comissão líquida", "Para assessor", "Para empresa"]:
            tabela_pnl_mes[col] = tabela_pnl_mes[col].apply(formata_brl)

        tabela_pnl_mes["Repasse"] = tabela_pnl_mes["Repasse"].apply(
            lambda x: f"{x*100:.0f}%"
        )

        col_p1, col_p2 = st.columns([2, 1])

        with col_p1:
            df_plot_mes = df_pnl_mes.melt(
                id_vars=["Assessor"],
                value_vars=["Para_Assessor", "Para_Empresa"],
                var_name="Tipo",
                value_name="Valor"
            )
            df_plot_mes["Tipo"] = df_plot_mes["Tipo"].replace({
                "Para_Assessor": "Para o assessor",
                "Para_Empresa": "Para a empresa"
            })

            fig_pnl_mes = px.bar(
                df_plot_mes,
                x="Assessor",
                y="Valor",
                color="Tipo",
                barmode="group",
                labels={"Valor": "Valor", "Assessor": "Assessor", "Tipo": "Tipo"},
                title="PNL por assessor no mês selecionado (comissão líquida)"
            )
            st.plotly_chart(fig_pnl_mes, use_container_width=True)

        with col_p2:
            st.markdown("Tabela de PNL do mês")
            st.dataframe(tabela_pnl_mes)

    st.markdown("---")

        # Seção PNL acumulado no ano
ano_selecionado = int(mes_selecionado.split("-")[0])
st.subheader(f"PNL acumulado no ano de {ano_selecionado}")

df_pnl_ytd = df_ass_mes[df_ass_mes["Ano"] == ano_selecionado].copy()
if df_pnl_ytd.empty:
    st.warning("Nenhum dado para calcular PNL acumulado neste ano.")
else:
    # Soma comissão bruta do ano por assessor
    df_pnl_ytd = df_pnl_ytd.groupby("Assessor", as_index=False)["Comissao"].sum()

    # Comissão líquida após imposto
    df_pnl_ytd["Comissao_Liquida"] = df_pnl_ytd["Comissao"] * FATOR_LIQUIDO

    # Repasse em cima da comissão líquida
    df_pnl_ytd["Repasse"] = df_pnl_ytd["Assessor"].apply(get_repasse)
    df_pnl_ytd["Para_Assessor"] = df_pnl_ytd["Comissao_Liquida"] * df_pnl_ytd["Repasse"]
    df_pnl_ytd["Para_Empresa"] = df_pnl_ytd["Comissao_Liquida"] - df_pnl_ytd["Para_Assessor"]

    # Total que ficou para a empresa no ano inteiro
    total_empresa_ano = df_pnl_ytd["Para_Empresa"].sum()

    # % do total da empresa que cada assessor gerou
    df_pnl_ytd["Pct_Empresa_sobre_Total"] = (
        df_pnl_ytd["Para_Empresa"] / total_empresa_ano
    )

    df_pnl_ytd = df_pnl_ytd.sort_values("Para_Empresa", ascending=False)

    # Montar tabela para exibição
    tabela_pnl_ytd = pd.DataFrame({
        "Assessor": df_pnl_ytd["Assessor"],
        "Comissão bruta": df_pnl_ytd["Comissao"],
        "Comissão líquida": df_pnl_ytd["Comissao_Liquida"],
        "Repasse": df_pnl_ytd["Repasse"],
        "Para assessor": df_pnl_ytd["Para_Assessor"],
        "Para empresa": df_pnl_ytd["Para_Empresa"],
        "% empresa do total anual": df_pnl_ytd["Pct_Empresa_sobre_Total"],
    }).reset_index(drop=True)

    # Formatação em R$
    for col in ["Comissão bruta", "Comissão líquida", "Para assessor", "Para empresa"]:
        tabela_pnl_ytd[col] = tabela_pnl_ytd[col].apply(formata_brl)

    # Formatar percentuais
    tabela_pnl_ytd["Repasse"] = tabela_pnl_ytd["Repasse"].apply(lambda x: f"{x*100:.0f}%")
    tabela_pnl_ytd["% empresa do total anual"] = tabela_pnl_ytd["% empresa do total anual"].apply(
        lambda x: f"{x*100:.1f}%"
    )

    col_y1, col_y2 = st.columns([2, 1])

    with col_y1:
        df_plot_ytd = df_pnl_ytd.melt(
            id_vars=["Assessor"],
            value_vars=["Para_Assessor", "Para_Empresa"],
            var_name="Tipo",
            value_name="Valor"
        )
        df_plot_ytd["Tipo"] = df_plot_ytd["Tipo"].replace({
            "Para_Assessor": "Para o assessor",
            "Para_Empresa": "Para a empresa"
        })

        fig_pnl_ytd = px.bar(
            df_plot_ytd,
            x="Assessor",
            y="Valor",
            color="Tipo",
            barmode="group",
            labels={"Valor": "Valor", "Assessor": "Assessor", "Tipo": "Tipo"},
            title="PNL acumulado por assessor no ano (comissão líquida)"
        )
        st.plotly_chart(fig_pnl_ytd, use_container_width=True)

    with col_y2:
        st.markdown("Tabela de PNL acumulado no ano")
        st.dataframe(tabela_pnl_ytd)

else:
    # Sem dados consolidados ainda
    pass
