import re
import pandas as pd
import streamlit as st

# -------------------------
# Função para extrair códigos, quantidades e preços
# -------------------------
def extrair_produtos(texto):
    """
    Extrai pares de (código, quantidade, preço) de uma string de descrição de pedido.
    Reconhece formatos como:
    - '10x 00101478'
    - '6 UNIDADES 12971'
    - '4 23391'
    - '00011279 - 12 unid / R$ 32,40'
    """
    if not isinstance(texto, str):
        return []

    texto = texto.upper()
    resultados = []

    # --- Extrair pares "quantidade + código"
    padroes = [
        r"(\d+)\s*[X ]\s*(\d{5,})",                      # Ex: 10x 00101478
        r"(\d+)\s*(?:UN|UNID|UND|UNIDADES?)\s*(\d{5,})", # Ex: 6 UNIDADES 12971
        r"(\d+)\s+(\d{5,})",                             # Ex: 4 23391
        r"(\d{5,})\s*-\s*(\d+)\s*(?:UN|UNID|UND)?"       # Ex: 00011279 - 12 unid
    ]

    for padrao in padroes:
        for qtd, cod in re.findall(padrao, texto):
            resultados.append((cod, int(qtd), None))

    # --- Extrair preços
    precos = re.findall(r"R\$\s?([\d.,]+)", texto)
    precos_convertidos = []
    for p in precos:
        try:
            precos_convertidos.append(float(p.replace(".", "").replace(",", ".")))
        except:
            precos_convertidos.append(None)

    # Se já encontramos códigos+quantidades, vincula preços
    if resultados:
        for i in range(min(len(resultados), len(precos_convertidos))):
            cod, qtd, _ = resultados[i]
            resultados[i] = (cod, qtd, precos_convertidos[i])
    else:
        # Caso tenha só preços soltos
        for preco in precos_convertidos:
            resultados.append((None, None, preco))

    return resultados


# -------------------------
# App Streamlit
# -------------------------
st.set_page_config(page_title="Análise de Pedidos", layout="wide")

st.title("📊 Analisador de Pedidos por Estado / Solicitante / Motivo")

uploaded_file = st.file_uploader("Faça upload da planilha Excel", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)

    st.subheader("📌 Prévia dos Dados Originais")
    st.dataframe(df.head())

    # Garantir que a coluna de descrição existe
    if "CODIGO DO PRODUTO,  QUANTIDADE E PREÇO SOLICITADO:" not in df.columns:
        st.error("⚠️ A planilha precisa da coluna: CODIGO DO PRODUTO, QUANTIDADE E PREÇO SOLICITADO:")
    else:
        dados_tratados = []

        for _, row in df.iterrows():
            produtos = extrair_produtos(row["CODIGO DO PRODUTO,  QUANTIDADE E PREÇO SOLICITADO:"])
            for prod, qtd, preco in produtos:
                dados_tratados.append({
                    "Produto": prod,
                    "Quantidade": qtd,
                    "Preco_Solicitado": preco,
                    "Estado": row.get("ESTADO", None),
                    "Solicitante": row.get("SOLICITANTE:", None),
                    "Motivo": row.get("MOTIVO:", None),
                    "Data": row.get("Data", None),
                })

        df_tratado = pd.DataFrame(dados_tratados)

        st.subheader("📌 Dados Tratados (Produtos separados)")
        st.dataframe(df_tratado)

        # -------------------------
        # Análises
        # -------------------------
        st.subheader("📊 Produtos mais solicitados por Estado")
        if not df_tratado.empty:
            mais_solicitados = df_tratado.groupby(["Estado", "Produto"])["Quantidade"].sum().reset_index()
            st.dataframe(mais_solicitados.sort_values(["Estado", "Quantidade"], ascending=[True, False]))

        st.subheader("📊 Solicitantes com mais pedidos")
        if not df_tratado.empty:
            solicitantes = df_tratado.groupby("Solicitante")["Produto"].count().reset_index()
            solicitantes = solicitantes.rename(columns={"Produto": "Total_Solicitacoes"})
            st.dataframe(solicitantes.sort_values("Total_Solicitacoes", ascending=False))

        st.subheader("📊 Motivos mais recorrentes por dia")
        if not df_tratado.empty and "Data" in df_tratado.columns:
            df_tratado["Data"] = pd.to_datetime(df_tratado["Data"], errors="coerce").dt.date
            motivos = df_tratado.groupby(["Data", "Motivo"])["Produto"].count().reset_index()
            motivos = motivos.rename(columns={"Produto": "Qtd"})
            st.dataframe(motivos.sort_values(["Data", "Qtd"], ascending=[True, False]))
