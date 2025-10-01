import re
import pandas as pd
import streamlit as st

# -------------------------
# Função para extrair produtos, quantidades e preços
# -------------------------
def extrair_produtos(texto):
    if not isinstance(texto, str):
        return []

    texto = texto.upper()
    resultados = []

    # Padrões para Produto + Quantidade
    padroes = [
        r"(\d{5,})\s*[- ]\s*(\d+)",                 # 00011279 - 12
        r"(\d+)\s*[X ]\s*(\d{5,})",                 # 10x 00101478
        r"(\d+)\s*(?:UN|UNID|UND|UNIDADES?)\s*(\d{5,})", # 6 UNIDADES 12971
        r"(\d{5,})\s+(\d+)",                        # 23391 4
    ]

    for padrao in padroes:
        for a, b in re.findall(padrao, texto):
            if len(a) >= 5:   # a é código, b é qtd
                resultados.append((a, int(b), None))
            else:             # a é qtd, b é código
                resultados.append((b, int(a), None))

    # Produtos isolados (códigos sem qtd)
    produtos_soltos = re.findall(r"\b\d{5,}\b", texto)
    for cod in produtos_soltos:
        if not any(cod == r[0] for r in resultados):
            resultados.append((cod, None, None))

    # Preços no formato brasileiro (R$ 12,34)
    precos = re.findall(r"R\$\s?([\d.,]+)", texto)
    precos_convertidos = []
    for p in precos:
        try:
            precos_convertidos.append(float(p.replace(".", "").replace(",", ".")))
        except:
            precos_convertidos.append(None)

    # Vincular preços
    if resultados and precos_convertidos:
        for i in range(min(len(resultados), len(precos_convertidos))):
            cod, qtd, _ = resultados[i]
            resultados[i] = (cod, qtd, precos_convertidos[i])
    else:
        for preco in precos_convertidos:
            resultados.append((None, None, preco))

    return resultados


# -------------------------
# App principal
# -------------------------
def main():
    st.set_page_config(page_title="Analisador de Pedidos", layout="wide")
    st.title("📊 Analisador de Pedidos")

    arquivo = st.file_uploader("Carregue a planilha Excel", type=["xlsx"])

    if arquivo:
        # Carregar apenas a aba correta
        df = pd.read_excel(arquivo, sheet_name="Respostas do Formulário 1")

        st.subheader("📂 Base Original")
        st.dataframe(df.head(10))

        dados_tratados = []

        for _, row in df.iterrows():
            texto_produtos = str(row.get("CODIGO DO PRODUTO, QUANTIDADE E PREÇO SOLICITADO:", "")) + " " + str(row.get("ANALISE NEGOCIAÇÃO", ""))
            produtos_extraidos = extrair_produtos(texto_produtos)

            for produto, qtd, preco in produtos_extraidos:
                dados_tratados.append({
                    "Produto": produto,
                    "Quantidade": qtd,
                    "Preco_Solicitado": preco,
                    "Estado": row.get("ESTADO:", None),
                    "Solicitante": row.get("SOLICITANTE:", None),
                    "Motivo": row.get("MOTIVO:", None),
                    "Data": row.get("Data", None),
                })

        df_tratado = pd.DataFrame(dados_tratados)

        st.subheader("📊 Dados Tratados (Produtos separados)")
        st.dataframe(df_tratado)

        # -------------------------
        # Análises
        # -------------------------
        st.subheader("📊 Produtos mais solicitados por Estado")
        if not df_tratado.empty:
            mais_solicitados = (
                df_tratado.groupby(["Estado", "Produto"])["Quantidade"]
                .sum()
                .reset_index()
            )
            st.dataframe(mais_solicitados.sort_values(["Estado", "Quantidade"], ascending=[True, False]))

        st.subheader("📊 Solicitantes com mais pedidos")
        if not df_tratado.empty:
            solicitantes = (
                df_tratado.groupby("Solicitante")["Produto"]
                .count()
                .reset_index()
                .rename(columns={"Produto": "Total_Solicitacoes"})
            )
            st.dataframe(solicitantes.sort_values("Total_Solicitacoes", ascending=False))

        st.subheader("📊 Motivos mais recorrentes por dia")
        if not df_tratado.empty:
            df_tratado["Data"] = pd.to_datetime(df_tratado["Data"], errors="coerce").dt.date
            motivos = (
                df_tratado.groupby(["Data", "Motivo"])["Produto"]
                .count()
                .reset_index()
                .rename(columns={"Produto": "Qtd"})
            )
            st.dataframe(motivos.sort_values(["Data", "Qtd"], ascending=[True, False]))

        # -------------------------
        # Download Excel tratado
        # -------------------------
        excel_final = "dados_tratados.xlsx"
        df_tratado.to_excel(excel_final, index=False)
        with open(excel_final, "rb") as f:
            st.download_button("📥 Baixar Excel Tratado", f, file_name=excel_final)


if __name__ == "__main__":
    main()
