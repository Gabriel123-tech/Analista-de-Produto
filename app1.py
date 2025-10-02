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

    padroes = [
        r"(\d{5,})\s*[- ]\s*(\d+)",
        r"(\d+)\s*[X ]\s*(\d{5,})",
        r"(\d+)\s*(?:UN|UNID|UND|UNIDADES?)\s*(\d{5,})",
        r"(\d{5,})\s+(\d+)",
    ]

    for padrao in padroes:
        for a, b in re.findall(padrao, texto):
            if len(a) >= 5:
                resultados.append((a, int(b), None))
            else:
                resultados.append((b, int(a), None))

    # Produtos sem quantidade (apenas código solto)
    produtos_soltos = re.findall(r"\b\d{5,}\b", texto)
    for cod in produtos_soltos:
        if not any(cod == r[0] for r in resultados):
            resultados.append((cod, None, None))

    # Preços encontrados
    precos = re.findall(r"R\$\s?([\d.,]+)", texto)
    precos_convertidos = []
    for p in precos:
        try:
            precos_convertidos.append(float(p.replace(".", "").replace(",", ".")))
        except:
            precos_convertidos.append(None)

    # Associar preços aos produtos quando possível
    if resultados and precos_convertidos:
        for i in range(min(len(resultados), len(precos_convertidos))):
            cod, qtd, _ = resultados[i]
            resultados[i] = (cod, qtd, precos_convertidos[i])
    else:
        for preco in precos_convertidos:
            resultados.append((None, None, preco))

    return resultados

# -------------------------
# Função para extrair campos de texto livre
# -------------------------
def extrair_campos(texto):
    solicitantes = re.search(r'solicitante[s]?\s*:\s*(.*)', texto, re.IGNORECASE)
    estado = re.search(r'estado\s*:\s*(.*)', texto, re.IGNORECASE)
    motivo = re.search(r'motivo\s*:\s*(.*)', texto, re.IGNORECASE)
    return {
        'Solicitante': formatar_texto(solicitantes.group(1)) if solicitantes else None,
        'Estado': formatar_texto(estado.group(1)) if estado else None,
        'Motivo': formatar_texto(motivo.group(1)) if motivo else None
    }

# -------------------------
# Função para formatar texto (Maiúscula Inicial)
# -------------------------
def formatar_texto(texto):
    if not isinstance(texto, str):
        return texto
    texto = texto.strip()
    return texto.capitalize() if texto else None

# -------------------------
# App principal
# -------------------------
def main():
    st.set_page_config(page_title="Analisador de Produtos", layout="wide")
    st.title("📊 Analisador de Produtos")
    st.write("✅ App iniciado com sucesso")

    arquivo = st.file_uploader("Carregue a planilha Excel", type=["xlsx"])

    if arquivo:
        df = pd.read_excel(arquivo, sheet_name="Respostas do Formulário 1")
        df.columns = df.columns.str.strip()

        st.subheader("📂 Base Original")
        st.dataframe(df.head(10))

        dados_tratados = []

        for _, row in df.iterrows():
            texto_produtos = str(row.get("CODIGO DO PRODUTO, QUANTIDADE E PREÇO SOLICITADO:", "")) + " " + str(row.get("ANALISE NEGOCIAÇÃO", ""))
            produtos_extraidos = extrair_produtos(texto_produtos)
            campos_extras = extrair_campos(texto_produtos)

            estado = formatar_texto(row.get("ESTADO:", None)) or campos_extras['Estado']
            solicitante = formatar_texto(row.get("SOLICITANTE:", None)) or campos_extras['Solicitante']
            motivo = formatar_texto(row.get("MOTIVO:", None)) or campos_extras['Motivo']

            for produto, qtd, preco in produtos_extraidos:
                dados_tratados.append({
                    "Data": row.get("Data", None),
                    "Produto": str(produto).strip(),
                    "Quantidade": qtd,
                    "Preco_Solicitado": preco,
                    "Estado": estado,
                    "Solicitante": solicitante,
                    "Motivo": motivo,
                })

        df_tratado = pd.DataFrame(dados_tratados)
        df_tratado["Data"] = pd.to_datetime(df_tratado["Data"], errors="coerce").dt.date

        st.subheader("📊 Dados Tratados (Produtos separados)")
        st.dataframe(df_tratado)

        # 🔍 Filtro por intervalo de datas com slider
        datas_validas = df_tratado["Data"].dropna()
        if not datas_validas.empty:
            data_min = min(datas_validas)
            data_max = max(datas_validas)

            intervalo = st.slider(
                "📆 Selecione o intervalo de datas",
                min_value=data_min,
                max_value=data_max,
                value=(data_min, data_max),
                format="DD/MM/YYYY"
            )

            df_filtrado = df_tratado[(df_tratado["Data"] >= intervalo[0]) & (df_tratado["Data"] <= intervalo[1])]
        else:
            st.warning("Nenhuma data válida encontrada na base.")
            df_filtrado = df_tratado.copy()

        # 🔧 Padronizar colunas para filtragem
        df_padronizado = df_filtrado.copy()
        for col in ["Estado", "Produto", "Solicitante", "Motivo"]:
            if col in df_padronizado.columns:
                df_padronizado[col] = df_padronizado[col].astype(str).str.strip().str.title()

        # 🔍 Filtros interativos
        col1, col2, col3 = st.columns(3)
        with col1:
            estado_selecionado = st.multiselect("📍 Filtrar por Estado", options=sorted(df_padronizado["Estado"].dropna().unique()))
        with col2:
            produto_selecionado = st.multiselect("📦 Filtrar por Produto", options=sorted(df_padronizado["Produto"].dropna().unique()))
        with col3:
            solicitante_selecionado = st.multiselect("🧑 Filtrar por Solicitante", options=sorted(df_padronizado["Solicitante"].dropna().unique()))

        if "Motivo" in df_padronizado.columns:
            motivo_selecionado = st.multiselect("📝 Filtrar por Motivo", options=sorted(df_padronizado["Motivo"].dropna().unique()))
        else:
            motivo_selecionado = []
            st.warning("Coluna 'Motivo' não encontrada nos dados.")

        # Aplicar filtros
        if estado_selecionado:
            df_padronizado = df_padronizado[df_padronizado["Estado"].isin(estado_selecionado)]
        if produto_selecionado:
            df_padronizado = df_padronizado[df_padronizado["Produto"].isin(produto_selecionado)]
        if solicitante_selecionado:
            df_padronizado = df_padronizado[df_padronizado["Solicitante"].isin(solicitante_selecionado)]
        if motivo_selecionado:
            df_padronizado = df_padronizado[df_padronizado["Motivo"].isin(motivo_selecionado)]

        # 📊 Produtos mais solicitados por Estado
        st.subheader("📊 Produtos mais solicitados por Estado")
        if not df_padronizado.empty:
            mais_solicitados = (
                df_padronizado.groupby(["Data", "Estado", "Produto"])["Quantidade"]
                .sum()
                .reset_index()
            )
            st.dataframe(mais_solicitados.sort_values(["Data", "Estado", "Quantidade"], ascending=[True, True, False]))

        # 📊 Solicitantes com mais pedidos
        st.subheader("📊 Solicitantes com mais pedidos")
        if not df_padronizado.empty:
            solicitantes = (
                df_padronizado.groupby(["Data", "Solicitante"])["Produto"]
                .count()
                .reset_index()
                .rename(columns={"Produto": "Total_Solicitacoes"})
            )
            st.dataframe(solicitantes.sort_values(["Data", "Total_Solicitacoes"], ascending=[True, False]))

        # 📊 Motivos mais recorrentes
        st.subheader("📊 Motivos mais recorrentes por dia")
        if not df_padronizado.empty and "Motivo" in df_padronizado.columns:
            motivos = (
                df_padronizado.groupby(["Data", "Motivo"])["Produto"]
                .count()
                .reset_index()
                .rename(columns={"Produto": "Qtd"})
            )
            st.dataframe(motivos.sort_values(["Data", "Qtd"], ascending=[True, False]))

        # 📥 Exportar Excel filtrado
        excel_filtrado = "dados_filtrados.xlsx"
        df_padronizado.to_excel(excel_filtrado, index=False)
        with open(excel_filtrado, "rb") as f:
            st.download_button("📥 Baixar Excel Filtrado", f, file_name=excel_filtrado)

        # 📥 Exportar Excel completo tratado
        excel_completo = "dados_completos.xlsx"
        df_tratado.to_excel(excel_completo, index=False)
        with open(excel_completo, "rb") as f:
            st.download_button("📥 Baixar Excel Completo", f, file_name=excel_completo)

    else:
        st.info("📁 Carregue uma planilha Excel para começar a análise.")

if __name__ == "__main__":
    main()
