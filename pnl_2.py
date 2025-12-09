import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Dashboard de Comissões por Assessor",
    layout="wide"
)

st.title("Dashboard de Comissões por Assessor")

st.markdown(
    """
Este painel consolida as comissões de **Agente Autônomo (AA)** e **Corban**
por assessor e por mês.  
A comissão final considerada é: **comissão total = AA + Corban**.
"""
)

# ============================================================
# CONFIGURAÇÃO DE COLUNAS DOS RELATÓRIOS
# Ajuste estes nomes de acordo com os arquivos reais
# ============================================================

# Relatório de Agente Autônomo (B2B)
COL_ASSESSOR_AA = "Assessor"          # nome da coluna de assessor no relatório AA
COL_MES_AA = "Competencia"           # coluna de mês ou competência no AA
COL_VALOR_AA = "Comissao AA"         # coluna de valor de comissão AA

# Relatório de Corban
COL_ASSESSOR_CORBAN = "Assessor"     # nome da coluna de assessor no relatório Corban
COL_MES_CORBAN = "Competencia"       # coluna de mês ou competência no Corban
COL_VALOR_CORBAN = "Comissao Corban" # coluna de valor de comissão Corban

# Dicionário de repasse percentual por assessor para cálculo de PNL
# Preencha com os nomes exatamente como aparecem na base consolidada
repasse_por_assessor = {
    # "NOME DO ASSESSOR": 0.70,
    # "OUTRO ASSESSOR": 0.60,
}


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def load_any(file):
    """Lê arquivos CSV ou Excel com separador padrão dos relatórios B2B."""
    name = file.name.lower()
    if name.endswith(".csv"):
        return pd.read_csv(file, sep=";", decimal=",")
    return pd.read_excel(file)


def trata_base_aa(files):
    """Trata e consolida a base de Agente Autônomo."""
    if not files:
        return pd.DataFrame(columns=["assessor", "mes", "comissao_aa"])

    dfs = []
    for f in files:
        df = load_any(f)

        # Validação básica
        faltando = [
            c for c in [COL_ASSESSOR_AA, COL_MES_AA, COL_VALOR_AA]
            if c not in df.columns
        ]
        if faltando:
            st.error(f"No arquivo {f.name} faltam as colunas: {faltando}")
            st.stop()

        df = df.rename(columns={
            COL_ASSESSOR_AA: "assessor",
            COL_MES_AA: "mes",
            COL_VALOR_AA: "comissao_aa",
        })

        df["comissao_aa"] = pd.to_numeric(df["comissao_aa"], errors="coerce").fillna(0)
        df["assessor"] = df["assessor"].astype(str).str.strip()
        df["mes"] = df["mes"].astype(str).str.strip()

        dfs.append(df[["assessor", "mes", "comissao_aa"]])

    base = pd.concat(dfs, ignore_index=True)

    base_group = (
        base.groupby(["assessor", "mes"])["comissao_aa"]
        .sum()
        .reset_index()
    )
    return base_group


def trata_base_corban(files):
    """Trata e consolida a base de Corban."""
    if not files:
        return pd.DataFrame(columns=["assessor", "mes", "comissao_corban"])

    dfs = []
    for f in files:
        df = load_any(f)

        faltando = [
            c for c in [COL_ASSESSOR_CORBAN, COL_MES_CORBAN, COL_VALOR_CORBAN]
            if c not in df.columns
        ]
        if faltando:
            st.error(f"No arquivo {f.name} faltam as colunas: {faltando}")
            st.stop()

        df = df.rename(columns={{
            COL_ASSESSOR_CORBAN: "assessor",
            COL_MES_CORBAN: "mes",
            COL_VALOR_CORBAN: "comissao_corban",
        })

        df["comissao_corban"] = pd.to_numeric(df["comissao_corban"], errors="coerce").fillna(0)
        df["assessor"] = df["assessor"].astype(str).str.strip()
        df["mes"] = df["mes"].astype(str).str.strip()

        dfs.append(df[["assessor", "mes", "comissao_corban"]])

    base = pd.concat(dfs, ignore_index=True)

    base_group = (
        base.groupby(["assessor", "mes"])["comissao_corban"]
        .sum()
        .reset_index()
    )
    return base_group


def formata_moeda(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# ============================================================
# UPLOAD DOS ARQUIVOS
# ============================================================

st.sidebar.header("Upload de relatórios")

files_aa = st.sidebar.file_uploader(
    "Relatórios de Agente Autônomo (AA)",
    type=["xlsx", "xls", "csv"],
    accept_multiple_files=True
)

files_corban = st.sidebar.file_uploader(
    "Relatórios de Corban",
    type=["xlsx", "xls", "csv"],
    accept_multiple_files=True
)

if not files_aa and not files_corban:
    st.info("Envie pelo menos um relatório de AA ou de Corban para iniciar.")
    st.stop()

# ============================================================
# TRATAMENTO E CONSOLIDAÇÃO
# ============================================================

df_aa = trata_base_aa(files_aa)
df_corban = trata_base_corban(files_corban)

df_total = pd.merge(
    df_aa,
    df_corban,
    on=["assessor", "mes"],
    how="outer"
).fillna(0)

df_total["comissao_aa"] = pd.to_numeric(df_total["comissao_aa"], errors="coerce").fillna(0)
df_total["comissao_corban"] = pd.to_numeric(df_total["comissao_corban"], errors="coerce").fillna(0)
df_total["comissao_total"] = df_total["comissao_aa"] + df_total["comissao_corban"]

# Calcula repasse e PNL se houver dicionário preenchido
df_total["repasse_percentual"] = df_total["assessor"].map(repasse_por_assessor).fillna(0.0)
df_total["repasse_assessor"] = df_total["comissao_total"] * df_total["repasse_percentual"]
df_total["pnl_empresa"] = df_total["comissao_total"] - df_total["repasse_assessor"]

# Ordenação padrão
df_total = df_total.sort_values(["mes", "assessor"]).reset_index(drop=True)

# ============================================================
# FILTROS BÁSICOS
# ============================================================

st.sidebar.header("Filtros")

meses_disponiveis = sorted(df_total["mes"].unique())
mes_selecionado = st.sidebar.selectbox(
    "Filtrar por mês",
    options=["Todos"] + meses_disponiveis,
    index=0
)

if mes_selecionado != "Todos":
    df_view = df_total[df_total["mes"] == mes_selecionado].copy()
else:
    df_view = df_total.copy()

# ============================================================
# VISÃO GERAL
# ============================================================

st.markdown("## Visão geral")

total_aa = df_view["comissao_aa"].sum()
total_corban = df_view["comissao_corban"].sum()
total_geral = df_view["comissao_total"].sum()
total_pnl = df_view["pnl_empresa"].sum()

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("Comissão AA", formata_moeda(total_aa))
with c2:
    st.metric("Comissão Corban", formata_moeda(total_corban))
with c3:
    st.metric("Comissão total", formata_moeda(total_geral))
with c4:
    st.metric("PNL empresa", formata_moeda(total_pnl))

st.divider()

# ============================================================
# TABELA DETALHADA POR ASSESSOR E MÊS
# ============================================================

st.markdown("### Comissões consolidadas por assessor e mês")

st.dataframe(
    df_view.style.format({
        "comissao_aa": formata_moeda,
        "comissao_corban": formata_moeda,
        "comissao_total": formata_moeda,
        "repasse_percentual": "{:.0%}".format,
        "repasse_assessor": formata_moeda,
        "pnl_empresa": formata_moeda,
    }),
    use_container_width=True
)

# ============================================================
# RANKING DE COMISSÃO POR ASSESSOR
# ============================================================

st.markdown("### Ranking de comissão total por assessor")

ranking = (
    df_view.groupby("assessor")["comissao_total"]
    .sum()
    .reset_index()
    .sort_values("comissao_total", ascending=False)
)

st.bar_chart(
    ranking.set_index("assessor")["comissao_total"],
    use_container_width=True
)

st.markdown("### Detalhe do ranking")
st.dataframe(
    ranking.style.format({"comissao_total": formata_moeda}),
    use_container_width=True
)

