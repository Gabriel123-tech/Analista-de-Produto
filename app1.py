import re
import pandas as pd
import streamlit as st

# -------------------------
# Função para extrair produtos, quantidades e preços
# -------------------------
def extrair_produtos(texto):
    """
    Extrai corretamente pares (Produto, Quantidade, Preço) de uma string.
    Agora diferencia códigos de produtos (>=5 dígitos) de quantidades (<=4 dígitos).
    """
    if not isinstance(texto, str):
        return []

    texto = texto.upper()
    resultados = []

    # ---------------------
    # 1. Captura pares "quantidade + produto"
    # ---------------------
    padroes = [
        r"(\d+)\s*[X ]\s*(\d{5,})",                      # Ex: 10x 00101478
        r"(\d+)\s*(?:UN|UNID|UND|UNIDADES?)\s*(\d{5,})", # Ex: 6 UNIDADES 12971
        r"(\d{5,})\s*-\s*(\d+)\s*(?:UN|UNID|UND)?",      # Ex: 00011279 - 12 unid
    ]

    for padrao in padroes:
        for qtd, cod in re.findall(padrao, texto):
            resultados.append((cod, int(qtd), None))

    # ---------------------
    # 2. Captura "produto + quantidade solta"
    # ---------------------
    pares = re.findall(r"(\d{5,})\s+(\d{1,4})", texto)  # Ex: 12971 6
    for cod, qtd in pares:
        resultados.append((cod, int(qtd), None))

    # ---------------------
    # 3. Produtos soltos (>=5 dígitos sem quantidade)
    # ---------------------
    produtos_soltos = re.findall(r"\b\d{5,}\b", texto)
    for cod in produtos_soltos:
        if not any(cod == r[0] for r in resultados):
            resultados.append((cod, None, None))

    # ---------------------
    # 4. Captura preços
    # ---------------------
    precos = re.findall(r"R\$\s?([\d.,]+)", texto)
    precos_convertidos = []
    for p in precos:
        try:
            precos_convertidos.append(float(p.replace(".", "").replace(",", ".")))
        except:
            precos_convertidos.append(None)

    # Vincula preços se houver
    if resultados and precos_convertidos:
        for i in range(min(len(resultados), len(precos_convertidos))):
            cod, qtd, _ = resultados[i]
            resultados[i] = (cod, qtd, precos_convertidos[i])
    else:
        for preco in precos_convertidos:
            resultados.append((None, None, preco))

    return resultados


# -------------------------
# Função principal do Streamlit
# -------------------------
def main():
    st.title("📌 Tratamento de Pedidos - Produtos Separados")

    # Upload de arquivo
    arquivo = st.file_uploader("Carregue um arquivo Excel com os pedidos", type=["xlsx"])

    if arquivo:
        df = pd.read_excel(arquivo)

        st.subheader("📂 Base Original")
        st.dataframe(df)

        # Lista onde os dados tratados serão armazenados
        dados_tratados = []

        for _, row in df.iterrows():
            produtos_extraidos = extrair_produtos(str(row.get("Observação", "")))

            if produtos_extraidos:
                for produto, qtd, preco in produtos_extraidos:
                    dados_tratados.append({
                        "Produto": produto,
                        "Quantidade": qtd,
                        "Preco_Solicitado": preco,
                        "Estado": row.get("Estado", None),
                        "Solicitante": row.get("Solicitante", None),
                        "Motivo": row.get("Motivo", None),
                    })
            else:
                dados_tratados.append({
                    "Produto": None,
                    "Quantidade": None,
                    "Preco_Solicitado": None,
                    "Estado": row.get("Estado", None),
                    "Solicitante": row.get("Solicitante", None),
                    "Motivo": row.get("Motivo", None),
                })

        df_tratado = pd.DataFrame(dados_tratados)

        st.subheader("📊 Dados Tratados (Produtos separados)")
        st.dataframe(df_tratado)

        # Opção para baixar Excel
        excel_final = "dados_tratados.xlsx"
        df_tratado.to_excel(excel_final, index=False)
        with open(excel_final, "rb") as f:
            st.download_button("📥 Baixar Excel Tratado", f, file_name=excel_final)


if __name__ == "__main__":
    main()
