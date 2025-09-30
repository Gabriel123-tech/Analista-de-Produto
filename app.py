import streamlit as st
import pandas as pd
import plotly.express as px

# ========================
# 1. Configuração do app
# ========================
st.set_page_config(page_title="Diferença de Preços", layout="wide")
st.title("📊 Comparação de preços por produto e estado")

# ========================
# 2. Upload do arquivo
# ========================
uploaded_file = st.file_uploader("📂 Faça upload do arquivo Excel", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)

    # ========================
    # 3. Filtro de Produto
    # ========================
    produtos = df["Produto"].unique().tolist()
    produtos.insert(0, "Todos")  # adiciona opção "Todos"
    produto_selecionado = st.selectbox("🔎 Selecione um produto", produtos)

    # ========================
    # 4. Gráfico de Barras
    # ========================
    if produto_selecionado == "Todos":
        st.subheader("Produtos mais solicitados em cada Estado")

        # Encontrar o produto mais frequente por estado
        mais_vendidos = (
            df.groupby(["UF Cliente", "Produto"])
            .size()
            .reset_index(name="Qtde")
        )

        # Selecionar o mais solicitado de cada estado
        mais_vendidos = mais_vendidos.loc[
            mais_vendidos.groupby("UF Cliente")["Qtde"].idxmax()
        ]

        # Juntar com os preços médios
        df_merge = df.merge(
            mais_vendidos[["UF Cliente", "Produto"]],
            on=["UF Cliente", "Produto"],
            how="inner"
        )

        df_group = (
            df_merge.groupby(["UF Cliente", "Produto"])["Preço Médio Venda"]
            .mean()
            .reset_index()
        )

        fig_bar = px.bar(
            df_group,
            x="UF Cliente",
            y="Preço Médio Venda",
            color="Produto",
            barmode="group",
            title="Preço médio do produto mais solicitado em cada estado"
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    else:
        # Filtrar os dados para o produto escolhido
        df_filtrado = df[df["Produto"] == produto_selecionado]

        fig_bar = px.bar(
            df_filtrado,
            x="UF Cliente",
            y="Preço Médio Venda",
            color="UF Cliente",
            barmode="group",
            title=f"Preço médio por estado - Produto {produto_selecionado}"
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    # ========================
    # 5. Heatmap de todos os produtos
    # ========================
    st.subheader("Mapa de calor - Preços por produto e estado")

    # Criar tabela pivoteada (Produto x Estado)
    pivot = df.pivot_table(
        index="Produto",
        columns="UF Cliente",
        values="Preço Médio Venda",
        aggfunc="mean"
    )

    # Converter Produto em string (para aparecer como rótulo no eixo Y)
    pivot.index = pivot.index.astype(str)

    # Criar heatmap com preços dentro das células
    fig_heatmap = px.imshow(
        pivot,
        aspect="auto",
        color_continuous_scale="RdBu",
        title="Mapa de calor - Preços por produto e estado",
        text_auto=True  # mostra valores dentro das células
    )

    # Forçar eixo Y categórico
    fig_heatmap.update_yaxes(type="category")

    # Personalizar tooltip
    fig_heatmap.update_traces(
        hovertemplate="UF: %{x}<br>Produto: %{y}<br>Preço Médio: R$ %{z:.2f}<extra></extra>"
    )

    st.plotly_chart(fig_heatmap, use_container_width=True)

else:
    st.info("⬆️ Faça upload de um arquivo Excel para começar.")