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

    # Remover linhas totalmente sem valores numéricos (segurança extra)
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

    df_ass_mes = (
        base.groupby(["Mes_Ano", "Assessor"], as_index=False)["Comissao"].sum()
        .sort_values(["Mes_Ano", "Assessor"])
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
            "Selecione um mês para ver o ranking",
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

    st.subheader(f"Ranking de assessores em {mes_selecionado}")
    df_ranking = (
        df_ass_mes[df_ass_mes["Mes_Ano"] == mes_selecionado]
        .sort_values("Comissao", ascending=False)
    )

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
        st.dataframe(df_ranking.reset_index(drop=True))
