#Seleção de aba no upload das bases

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from io import BytesIO

st.set_page_config(
    page_title="Dashboard de Comissões por Assessor - Base detalhada",
    layout="wide"
)

st.title("Dashboard de Comissões por Assessor (base detalhada)")

st.markdown(
    """
Este app lê a **planilha detalhada de receitas** (Agente Autônomo e Corban),
trata a base e monta um painel de acompanhamento da evolução mensal
das comissões por assessor.

- Mantém as categorias originais de cada base  
- Usa a coluna **Categoria** para identificar se a origem é AA ou CORBAN  
- PNL sempre calculado sobre a **comissão total** da linha
"""
)

uploaded_files = st.file_uploader(
    "Envie um ou mais relatórios detalhados em Excel",
    type=["xlsx", "xls"],
    accept_multiple_files=True
)

# =========================
# Configurações de PNL
# =========================

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
    "OTAVIO NUNES CARDOZO JÚNIOR": 0.60,
    "PEDRO AMMAR FORATO": 0.80,
    "PEDRO BORGERTH TEIXEIRA DE LUCA": 0.70,
    "RAFAEL MADALENA MARTINS": 0.80,
    "RAFAEL DADOORIAN PREGNOLATI": 0.80,
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


# categorias da planilha Corban para identificar origem
CATEGORIAS_CORBAN = {
    "CAMBIO",
    "CONTA VIRADA",
    "CREDITO",
    "CREDITO ESTRUTURADO",
    "ENERGIA",
    "FEE TRANSACIONAL",
    "FEE TRANSACIONAL PME",
    "MESA CAMBIO",
}


def tratar_detalhado(file):
    """
    Lê a planilha detalhada, permite escolher a aba e normaliza as colunas.
    Funciona mesmo que o cabeçalho não esteja na primeira linha.
    """

    st.markdown(f"### 📄 Arquivo: **{file.name}**")

    # 1. Seleção de aba
    xls = pd.ExcelFile(file)
    abas_disponiveis = xls.sheet_names

    aba_escolhida = st.selectbox(
        f"Aba da planilha {file.name}",
        options=abas_disponiveis,
        index=0,
        key=f"aba_{file.name}"
    )

    # 2. Lê a aba escolhida sem cabeçalho fixo
    raw = pd.read_excel(xls, sheet_name=aba_escolhida, header=None)

    # 3. Procura a linha onde a primeira coluna é "Data Receita"
    first_col = raw.iloc[:, 0].astype(str).str.strip().str.upper()
    header_mask = first_col == "DATA RECEITA"
    if not header_mask.any():
        st.error(
            f"Não encontrei a linha de cabeçalho com 'Data Receita' "
            f"na aba '{aba_escolhida}' do arquivo {file.name}."
        )
        st.stop()

    header_idx = header_mask[header_mask].index[0]
    header = raw.iloc[header_idx].tolist()

    # 4. Dados a partir da linha seguinte ao cabeçalho
    df = raw.iloc[header_idx + 1 :].copy()
    df.columns = header
    df.columns = df.columns.astype(str).str.strip()

    rename_map = {
        "Data Receita": "Data_Receita",
        "Conta": "Conta",
        "Cliente": "Cliente",
        "Código Assessor": "Codigo_Assessor",
        "Assessor Principal": "Assessor",
        "Categoria": "Categoria",
        "Produto": "Produto",
        "Ativo": "Ativo",
        "Código/CNPJ": "Codigo_CNPJ",
        "Tipo Receita": "Tipo_Receita",
        "Receita Bruta": "Receita_Bruta",
        "Receita Líquida": "Receita_Liquida",
        "Comissão": "Comissao",
    }

    faltando = [c for c in rename_map.keys() if c not in df.columns]
    if faltando:
        st.error(
            f"No arquivo {file.name}, aba '{aba_escolhida}', ainda faltam as colunas: {faltando}"
        )
        st.stop()

    df = df.rename(columns=rename_map)

    # 5. Conversões
    df["Data_Receita"] = pd.to_datetime(
        df["Data_Receita"], errors="coerce", dayfirst=True
    )
    df = df[df["Data_Receita"].notna()]

    for col in ["Receita_Bruta", "Receita_Liquida", "Comissao"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df["Assessor"] = df["Assessor"].astype(str).str.strip()
    df["Categoria"] = df["Categoria"].astype(str).str.strip()
    df["Produto"] = df["Produto"].astype(str).str.strip()

    df["Ano"] = df["Data_Receita"].dt.year
    df["Mes"] = df["Data_Receita"].dt.month
    df["Mes_Ano"] = df["Data_Receita"].dt.strftime("%Y-%m")

    # 6. Origem (AA x Corban) com base na categoria
    cat_upper = df["Categoria"].str.upper()
    df["Origem"] = cat_upper.apply(
        lambda x: "CORBAN" if x in CATEGORIAS_CORBAN else "AA"
    )

    return df


all_dfs = []

if not uploaded_files:
    st.info("Envie ao menos um arquivo para iniciar o dashboard.")
else:
    for file in uploaded_files:
        df_tratado = tratar_detalhado(file)
        all_dfs.append(df_tratado)

if all_dfs:
    base = pd.concat(all_dfs, ignore_index=True)

    st.subheader("Base detalhada consolidada")

    with st.expander("Ver tabela completa"):
        st.dataframe(base)

    # download da base consolidada
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
        file_name="base_detalhada_consolidada.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    st.markdown("---")

    # =========================
    # Filtros
    # =========================

    st.subheader("Filtros")

    col_f1, col_f2, col_f3 = st.columns(3)

    with col_f1:
        assessores_unicos = sorted(base["Assessor"].unique())
        assessores_selecionados = st.multiselect(
            "Selecione os assessores",
            options=assessores_unicos,
            default=assessores_unicos
        )

    with col_f2:
        origens_unicas = sorted(base["Origem"].unique())
        origens_selecionadas = st.multiselect(
            "Origem da receita",
            options=origens_unicas,
            default=origens_unicas
        )

    with col_f3:
        categorias_unicas = sorted(base["Categoria"].unique())
        categorias_selecionadas = st.multiselect(
            "Categoria",
            options=categorias_unicas,
            default=categorias_unicas
        )

    col_f4, col_f5 = st.columns(2)

    with col_f4:
        produtos_unicos = sorted(base["Produto"].unique())
        produtos_selecionados = st.multiselect(
            "Produto",
            options=produtos_unicos,
            default=produtos_unicos
        )

    with col_f5:
        meses_unicos = sorted(base["Mes_Ano"].unique())
        mes_selecionado = st.selectbox(
            "Selecione um mês para ranking e PNL",
            options=meses_unicos
        )

    mask = (
        base["Assessor"].isin(assessores_selecionados)
        & base["Origem"].isin(origens_selecionadas)
        & base["Categoria"].isin(categorias_selecionadas)
        & base["Produto"].isin(produtos_selecionados)
    )
    base_filtrada = base[mask].copy()

    if base_filtrada.empty:
        st.warning("Nenhum dado após aplicação dos filtros.")
        st.stop()

    # =========================
    # Agregações
    # =========================

    df_mes = (
        base_filtrada.groupby("Mes_Ano", as_index=False)["Comissao"]
        .sum()
        .sort_values("Mes_Ano")
    )

    df_ass_mes = (
        base_filtrada.groupby(["Ano", "Mes_Ano", "Assessor"], as_index=False)["Comissao"]
        .sum()
        .sort_values(["Ano", "Mes_Ano", "Assessor"])
    )

    # =========================
    # Evolução mensal
    # =========================

    st.subheader("Evolução mensal da comissão total (filtros aplicados)")
    fig_total = px.line(
        df_mes,
        x="Mes_Ano",
        y="Comissao",
        markers=True,
        labels={"Mes_Ano": "Mês", "Comissao": "Comissão"},
        title="Comissão total por mês"
    )
    fig_total.update_xaxes(type="category")
    st.plotly_chart(fig_total, use_container_width=True)

    st.subheader("Evolução da comissão por assessor")
    if not df_ass_mes.empty:
        fig_ass = px.line(
            df_ass_mes,
            x="Mes_Ano",
            y="Comissao",
            color="Assessor",
            markers=True,
            labels={"Mes_Ano": "Mês", "Comissao": "Comissão"},
            title="Comissão por assessor ao longo dos meses"
        )
        fig_ass.update_xaxes(type="category")
        st.plotly_chart(fig_ass, use_container_width=True)
    else:
        st.warning("Nenhum dado para os assessores selecionados.")

    # =========================
    # Ranking do mês
    # =========================

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

    # ================================================================
    # 1. Ranking de receita por categoria (mês selecionado)
    # ================================================================

    st.markdown("---")
    st.subheader(f"Ranking de receita por categoria em {mes_selecionado}")

    df_cat_mes = (
        base_filtrada[base_filtrada["Mes_Ano"] == mes_selecionado]
        .groupby("Categoria", as_index=False)["Comissao"]
        .sum()
        .sort_values("Comissao", ascending=False)
    )

    if df_cat_mes.empty:
        st.warning("Nenhuma categoria encontrada no mês selecionado.")
    else:
        df_cat_mes["Comissao_fmt"] = df_cat_mes["Comissao"].apply(formata_brl)
        df_cat_mes["Pct"] = df_cat_mes["Comissao"] / df_cat_mes["Comissao"].sum()
        df_cat_mes["Pct_fmt"] = df_cat_mes["Pct"].apply(lambda x: f"{x*100:.1f}%")

        col_c1, col_c2 = st.columns([2, 1])

        with col_c1:
            fig_cat = px.bar(
                df_cat_mes,
                x="Comissao",
                y="Categoria",
                orientation="h",
                labels={"Comissao": "Receita", "Categoria": "Categoria"},
                title=f"Receita por categoria em {mes_selecionado}",
            )
            st.plotly_chart(fig_cat, use_container_width=True)

        with col_c2:
            st.markdown("Tabela de receita por categoria")
            st.dataframe(
                df_cat_mes[["Categoria", "Comissao_fmt", "Pct_fmt"]].rename(
                    columns={"Comissao_fmt": "Receita", "Pct_fmt": "% do total"}
                )
            )

    # ================================================================
    # 2. Receita dos assessores por categoria (mês selecionado)
    # ================================================================

    st.markdown("---")
    st.subheader(f"Receita dos assessores por categoria em {mes_selecionado}")

    df_ass_cat = (
        base_filtrada[base_filtrada["Mes_Ano"] == mes_selecionado]
        .groupby(["Assessor", "Categoria"], as_index=False)["Comissao"]
        .sum()
    )

    if df_ass_cat.empty:
        st.warning("Nenhum dado de assessor x categoria no mês selecionado.")
    else:
        df_pivot = df_ass_cat.pivot_table(
            index="Assessor",
            columns="Categoria",
            values="Comissao",
            aggfunc="sum",
            fill_value=0
        )

        df_pivot_fmt = df_pivot.applymap(formata_brl)

        col_ac1, col_ac2 = st.columns([2, 1])

        with col_ac1:
            fig_stack = px.bar(
                df_ass_cat,
                x="Assessor",
                y="Comissao",
                color="Categoria",
                title=f"Composição de receita por categoria para cada assessor ({mes_selecionado})",
                labels={"Comissao": "Receita"}
            )
            fig_stack.update_xaxes(type="category")
            st.plotly_chart(fig_stack, use_container_width=True)

        with col_ac2:
            st.markdown("Tabela (assessor x categoria)")
            st.dataframe(df_pivot_fmt)

    st.markdown("---")

    # =========================
    # PNL do mês
    # =========================

    st.subheader(f"PNL por assessor em {mes_selecionado}")

    df_pnl_mes = df_ass_mes[df_ass_mes["Mes_Ano"] == mes_selecionado].copy()
    if df_pnl_mes.empty:
        st.warning("Nenhum dado para calcular PNL neste mês.")
    else:
        df_pnl_mes["Comissao_Liquida"] = df_pnl_mes["Comissao"] * FATOR_LIQUIDO

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

    # =========================
    # PNL acumulado no ano
    # =========================

    ano_selecionado = int(mes_selecionado.split("-")[0])
    st.subheader(f"PNL acumulado no ano de {ano_selecionado}")

    df_pnl_ytd = df_ass_mes[df_ass_mes["Ano"] == ano_selecionado].copy()
    if df_pnl_ytd.empty:
        st.warning("Nenhum dado para calcular PNL acumulado neste ano.")
    else:
        df_pnl_ytd = df_pnl_ytd.groupby("Assessor", as_index=False)["Comissao"].sum()

        df_pnl_ytd["Comissao_Liquida"] = df_pnl_ytd["Comissao"] * FATOR_LIQUIDO

        df_pnl_ytd["Repasse"] = df_pnl_ytd["Assessor"].apply(get_repasse)
        df_pnl_ytd["Para_Assessor"] = df_pnl_ytd["Comissao_Liquida"] * df_pnl_ytd["Repasse"]
        df_pnl_ytd["Para_Empresa"] = df_pnl_ytd["Comissao_Liquida"] - df_pnl_ytd["Para_Assessor"]

        total_empresa_ano = df_pnl_ytd["Para_Empresa"].sum()

        df_pnl_ytd["Pct_Empresa_sobre_Total"] = (
            df_pnl_ytd["Para_Empresa"] / total_empresa_ano
        )

        df_pnl_ytd = df_pnl_ytd.sort_values("Para_Empresa", ascending=False)

        tabela_pnl_ytd = pd.DataFrame({
            "Assessor": df_pnl_ytd["Assessor"],
            "Comissão bruta": df_pnl_ytd["Comissao"],
            "Comissão líquida": df_pnl_ytd["Comissao_Liquida"],
            "Repasse": df_pnl_ytd["Repasse"],
            "Para assessor": df_pnl_ytd["Para_Assessor"],
            "Para empresa": df_pnl_ytd["Para_Empresa"],
            "% empresa do total anual": df_pnl_ytd["Pct_Empresa_sobre_Total"],
        }).reset_index(drop=True)

        for col in ["Comissão bruta", "Comissão líquida", "Para assessor", "Para empresa"]:
            tabela_pnl_ytd[col] = tabela_pnl_ytd[col].apply(formata_brl)

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
