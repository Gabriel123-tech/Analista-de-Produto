import re
import pandas as pd
import streamlit as st
import plotly.express as px
from datetime import datetime
import unicodedata # Importação necessária para remover acentos

# -------------------------
# Configuração inicial do Streamlit
# -------------------------
st.set_page_config(
    page_title="Analisador de Produtos e Pedidos", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# -------------------------
# Função para extrair produtos, quantidades e preços
# -------------------------
def extrair_produtos(texto):
    """Extrai código, quantidade e preço de um texto usando diversos padrões."""
    if not isinstance(texto, str):
        return []

    texto = texto.upper()
    resultados = []

    # Padrões para código (5+ dígitos) e quantidade
    padroes = [
        r"(\d{5,})\s*[- ]\s*(\d+)",
        r"(\d+)\s*[X ]\s*(\d{5,})",
        r"(\d+)\s*(?:UN|UNID|UND|UNIDADES?)\s*(\d{5,})",
        r"(\d{5,})\s+(\d+)",
    ]

    for padrao in padroes:
        for a, b in re.findall(padrao, texto):
            if len(a) >= 5:
                # a é o código, b é a quantidade
                resultados.append((a, int(b), None))
            else:
                # b é o código, a é a quantidade
                resultados.append((b, int(a), None))

    # Captura códigos soltos (5+ dígitos) sem quantidade
    produtos_soltos = re.findall(r"\b\d{5,}\b", texto)
    for cod in produtos_soltos:
        if not any(cod == r[0] for r in resultados):
            resultados.append((cod, None, None))

    # Extrai preços R$
    precos = re.findall(r"R\$\s?([\d.,]+)", texto)
    precos_convertidos = []
    for p in precos:
        try:
            # Converte R$ 1.234,56 para 1234.56
            precos_convertidos.append(float(p.replace(".", "").replace(",", ".")))
        except:
            precos_convertidos.append(None)

    # Associa preços às extrações de produtos na ordem em que aparecem
    if resultados and precos_convertidos:
        for i in range(min(len(resultados), len(precos_convertidos))):
            cod, qtd, _ = resultados[i]
            resultados[i] = (cod, qtd, precos_convertidos[i])

    return resultados

# -------------------------
# Funções auxiliares de padronização
# -------------------------
def extrair_campos(texto):
    """Extrai campos como solicitante, estado e motivo do texto da negociação."""
    solicitantes = re.search(r'solicitante[s]?\s*:\s*(.*)', texto, re.IGNORECASE)
    estado = re.search(r'estado\s*:\s*(.*)', texto, re.IGNORECASE)
    motivo = re.search(r'motivo\s*:\s*(.*)', texto, re.IGNORECASE)
    return {
        'Solicitante': formatar_texto(solicitantes.group(1)) if solicitantes else None,
        'Estado': formatar_texto(estado.group(1)) if estado else None,
        'Motivo': formatar_texto(motivo.group(1)) if motivo else None
    }

def formatar_texto(texto):
    """Remove espaços e capitaliza a primeira letra de cada palavra."""
    if not isinstance(texto, str):
        return texto
    texto = texto.strip()
    return texto.title() if texto else None

def remover_acentos(texto):
    """NOVA FUNÇÃO: Remove acentos de uma string, transformando 'Paraná' em 'Parana' para a comparação."""
    if not isinstance(texto, str):
        return texto
    # Normaliza para forma D (separando caractere e acento) e filtra o acento (categoria 'Mn')
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')


def padronizar_estado(estado):
    """FUNÇÃO ATUALIZADA: Padroniza nomes de estados, usando a versão sem acento como chave para mapeamento."""
    if not isinstance(estado, str):
        return estado
        
    # Usa a versão sem acento e minúscula como chave de comparação
    estado_chave = remover_acentos(estado).strip().lower() 
    
    # O valor do mapa é a versão final que queremos exibir (com acento correto)
    mapa = {
        "ms": "Mato Grosso do Sul",
        "mato grosso do sul": "Mato Grosso do Sul",
        "sc": "Santa Catarina",
        "rs": "Rio Grande do Sul",
        "pr": "Paraná", # 'pr' (sem acento) ou 'parana' (sem acento) padronizam para 'Paraná'
        "parana": "Paraná",
        "sp": "São Paulo", # 'sp' (sem acento) ou 'sao paulo' (sem acento) padronizam para 'São Paulo'
        "sao paulo": "São Paulo",
    }
    
    # Tenta encontrar no mapa. Se não encontrar, retorna o texto original formatado.
    return mapa.get(estado_chave, formatar_texto(estado))

def padronizar_produto(prod):
    """FUNÇÃO ATUALIZADA: Remove zeros à esquerda (ex: '00012026' -> '12026')."""
    if not isinstance(prod, str):
        prod = str(prod)
    
    prod = prod.strip()
    
    # Remove zeros à esquerda se for um código numérico
    try:
        if prod.isdigit():
            # Converte para inteiro (remove zeros) e depois para string
            return str(int(prod))
    except ValueError:
        pass # Caso não seja um número (embora isdigit() já garanta isso), mantém a string original

    return prod.strip()

def padronizar_motivo(motivo):
    """Agrupa variações de motivos de negociação em categorias mais amplas."""
    if not isinstance(motivo, str):
        return 'Não Informado'
    motivo = motivo.strip().lower()
    if not motivo:
        return 'Não Informado'

    # Agrupamento de motivos
    if 'desconto' in motivo or 'promocao' in motivo:
        return 'Solicitou Desconto/Promoção'
    if 'volume' in motivo or 'quantidade' in motivo or 'aumentar' in motivo:
        return 'Aumento Volume / Quantidade'
    if 'negociacao' in motivo or 'melhorar' in motivo or 'melhores condicoes' in motivo or 'preço' in motivo or 'preco' in motivo:
        return 'Negociação / Melhor Condição de Preço'
    if 'pagou' in motivo or 'ultima vez' in motivo:
        return 'Cliente Pagou da Última Vez'
    if 'manter os valores' in motivo:
        return 'Manter Valores'
    if 'cliente solicitou' in motivo or 'cliente pediu' in motivo or 'solicitou' in motivo or 'pedido' in motivo:
        return 'Outra Solicitação do Cliente'

    return motivo.title()

# -------------------------
# App principal
# -------------------------
def main():
    st.title("📦📈 Análise de Solicitações de Produtos")
    st.markdown("---")

    arquivo = st.file_uploader("Carregue a planilha Excel", type=["xlsx"], help="A planilha deve conter os dados de resposta do formulário.")

    if arquivo:
        # Carregar dados
        try:
            # Assumindo que a coluna de data se chama "Data" ou similar.
            df = pd.read_excel(arquivo, sheet_name="Respostas do Formulário 1")
        except:
            st.error("Erro ao carregar a aba 'Respostas do Formulário 1'. Verifique o nome da aba no seu arquivo.")
            return

        df.columns = df.columns.str.strip()

        # -------------------------
        # Tratamento de Dados
        # -------------------------
        dados_tratados = []
        coluna_produto_preco = "CODIGO DO PRODUTO, QUANTIDADE E PREÇO SOLICITADO:"
        coluna_analise = "ANALISE NEGOCIAÇÃO"

        coluna_produto_preco = coluna_produto_preco if coluna_produto_preco in df.columns else None
        coluna_analise = coluna_analise if coluna_analise in df.columns else None
        coluna_estado = "ESTADO:" if "ESTADO:" in df.columns else None
        coluna_solicitante = "SOLICITANTE:" if "SOLICITANTE:" in df.columns else None
        coluna_motivo = "MOTIVO:" if "MOTIVO:" in df.columns else None
        
        for index, row in df.iterrows():
            # Concatena os textos para extrair o máximo de informação
            texto_produtos = str(row.get(coluna_produto_preco, "")) + " " + str(row.get(coluna_analise, ""))
            
            produtos_extraidos = extrair_produtos(texto_produtos)
            campos_extras = extrair_campos(texto_produtos)

            estado = formatar_texto(row.get(coluna_estado, None)) or campos_extras['Estado']
            solicitante = formatar_texto(row.get(coluna_solicitante, None)) or campos_extras['Solicitante']
            motivo = formatar_texto(row.get(coluna_motivo, None)) or campos_extras['Motivo']

            for produto, qtd, preco in produtos_extraidos:
                dados_tratados.append({
                    "Data": row.get("Data", None),
                    "Produto": str(produto).strip() if produto else None,
                    "Quantidade": qtd if qtd is not None else 1,
                    "Preco_Solicitado": preco,
                    "Estado": estado,
                    "Solicitante": solicitante,
                    "Motivo": motivo,
                })

        df_tratado = pd.DataFrame(dados_tratados)

        # 4. Limpeza e criação de colunas de tempo
        df_tratado["Data"] = pd.to_datetime(df_tratado["Data"], errors="coerce")
        df_tratado["AnoMes"] = df_tratado["Data"].dt.to_period("M").astype(str)
        df_tratado["AnoSemana"] = df_tratado["Data"].dt.strftime("%Y-%W") 

        # 5. Filtragem de dados nulos/inválidos
        df_tratado = df_tratado.dropna(subset=["Produto"])
        df_tratado = df_tratado[df_tratado["Produto"].str.lower() != "none"]

        # 6. Padronização final (Utiliza as funções ATUALIZADAS)
        df_tratado["Produto"] = df_tratado["Produto"].apply(padronizar_produto)
        df_tratado["Estado"] = df_tratado["Estado"].apply(padronizar_estado)
        df_tratado["Solicitante"] = df_tratado["Solicitante"].astype(str).apply(formatar_texto)
        df_tratado["Motivo_Agrupado"] = df_tratado["Motivo"].apply(padronizar_motivo)
        
        # -------------------------
        # Filtros Interativos (Sidebar) - Adicionando Filtro de Data
        # -------------------------
        st.sidebar.header("Filtros de Análise")
        
        # 1. Filtro de Data
        data_validas = df_tratado["Data"].dropna().dt.date
        min_date = data_validas.min() if not data_validas.empty else datetime.now().date()
        max_date = data_validas.max() if not data_validas.empty else datetime.now().date()

        st.sidebar.markdown("##### 📅 Filtro por Período")
        col_data1, col_data2 = st.sidebar.columns(2)
        with col_data1:
            data_inicio = st.date_input("De", value=min_date, min_value=min_date, max_value=max_date, key='data_inicio')
        with col_data2:
            data_fim = st.date_input("Até", value=max_date, min_value=min_date, max_value=max_date, key='data_fim')

        # 2. Outros Filtros
        estado_sel = st.sidebar.multiselect("📍 Estado", sorted(df_tratado["Estado"].dropna().astype(str).unique()))
        produto_sel = st.sidebar.multiselect("📦 Produto", sorted(df_tratado["Produto"].dropna().astype(str).unique()))
        solicitante_sel = st.sidebar.multiselect("🧑 Solicitante", sorted(df_tratado["Solicitante"].dropna().astype(str).unique()))
        motivo_sel = st.sidebar.multiselect("📝 Motivo Agrupado", sorted(df_tratado["Motivo_Agrupado"].dropna().astype(str).unique()))

        # Aplicação dos Filtros
        df_filtros = df_tratado.copy()
        
        # Filtro de Data
        df_filtros = df_filtros[
            (df_filtros["Data"].dt.date >= data_inicio) & 
            (df_filtros["Data"].dt.date <= data_fim)
        ]

        if estado_sel:
            df_filtros = df_filtros[df_filtros["Estado"].isin(estado_sel)]
        if produto_sel:
            df_filtros = df_filtros[df_filtros["Produto"].isin(produto_sel)]
        if solicitante_sel:
            df_filtros = df_filtros[df_filtros["Solicitante"].isin(solicitante_sel)]
        if motivo_sel:
            df_filtros = df_filtros[df_filtros["Motivo_Agrupado"].isin(motivo_sel)]
            
        if df_filtros.empty:
            st.warning("Nenhum dado encontrado com os filtros selecionados.")
            return

        # -------------------------
        # Métricas Chave
        # -------------------------
        # Contagem de solicitações (linhas) no DF filtrado
        total_solicitacoes = df_filtros.shape[0] 
        total_quantidade = df_filtros["Quantidade"].sum()
        media_preco = df_filtros["Preco_Solicitado"].mean()
        
        col_metrica1, col_metrica2, col_metrica3, col_metrica4 = st.columns(4)
        
        with col_metrica1:
            st.metric("Total de Solicitações (Contagem)", f"{total_solicitacoes:,}".replace(",", "."))
        with col_metrica2:
            st.metric("Volume Total de Itens", f"{total_quantidade:,.0f}".replace(",", "X").replace(".", ",").replace("X", "."))
        with col_metrica3:
            # Garante que 'media_preco' não seja NaN antes de formatar
            display_preco = f"R$ {media_preco:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if not pd.isna(media_preco) else "N/A"
            st.metric("Média de Preço Solicitado", display_preco)
        with col_metrica4:
            st.metric("Total de Produtos Únicos", df_filtros["Produto"].nunique())

        st.markdown("---")

        st.subheader("Análises e Visualizações")
        
        # -------------------------
        # GRÁFICO 1: Produtos mais solicitados (Volume Total)
        # -------------------------
        col_g1, col_g2 = st.columns(2)
        
        with col_g1:
            st.markdown("##### 📦 Top 10 Produtos por Volume Total (Todos os Estados)")
            
            # Agrupa o volume por Produto, independente do Estado
            top_produtos = df_filtros.groupby("Produto")["Quantidade"].sum().sort_values(ascending=False).head(10).reset_index()
            top_produtos.columns = ["Produto", "Quantidade Total"]
            
            fig_top_produtos = px.bar(
                top_produtos,
                x="Produto",
                y="Quantidade Total",
                title="Volume Total dos 10 Produtos Mais Solicitados",
                template="plotly_white",
                text="Quantidade Total"
            )
            # Formatação para remover o 'K' e usar separador de milhar (ponto)
            fig_top_produtos.update_yaxes(tickformat=',.') 
            fig_top_produtos.update_xaxes(title_text="Produto (Códigos)")
            fig_top_produtos.update_traces(texttemplate='%{text:,.0f}', textposition='outside', marker_color='#1f77b4')
            st.plotly_chart(fig_top_produtos, use_container_width=True)

        # -------------------------
        # GRÁFICO 2: Solicitantes com mais solicitações (Contagem)
        # -------------------------
        with col_g2:
            st.markdown("##### 🧑 Solicitantes com Maior Frequência de Solicitações (Top 15)")
            
            # Contagem da frequência (size)
            solicitantes_contagem = df_filtros.groupby("Solicitante").size().reset_index(name='Contagem').sort_values("Contagem", ascending=True).tail(15)
            
            fig_solicitantes = px.bar(
                solicitantes_contagem, 
                x="Contagem",
                y="Solicitante", 
                orientation='h', 
                title="Top 15 Solicitantes por Frequência",
                template="plotly_white",
                text="Contagem"
            )
            # Formatação
            fig_solicitantes.update_xaxes(tickformat=',.')
            fig_solicitantes.update_traces(texttemplate='%{text:,.0f}', textposition='outside', marker_color='#2ca02c')
            fig_solicitantes.update_layout(yaxis={'categoryorder':'total ascending'}, xaxis_title="Número de Solicitações")
            st.plotly_chart(fig_solicitantes, use_container_width=True)

        st.markdown("---")
        
        # -------------------------
        # GRÁFICO 3: Evolução Temporal Dinâmica (Visualização Simples)
        # -------------------------
        st.subheader("Evolução Temporal: Frequência de Solicitações")
        
        # Seletor dinâmico de granularidade
        granularidade = st.radio(
            "Visualizar Contagem de Solicitações por:",
            ('Semana', 'Mês'),
            index=1,
            horizontal=True,
            key='gran_select'
        )

        coluna_tempo = "AnoSemana" if granularidade == 'Semana' else "AnoMes"
        titulo_tempo = f"Evolução {granularidade} do Número Total de Solicitações"
        
        # Pré-processamento: Agrupa por período e conta a frequência
        df_evolucao = df_filtros.groupby(coluna_tempo).size().reset_index(name='Contagem')
        
        # Cria lista de tempo ordenada para o Plotly
        ordem_tempo = sorted(df_evolucao[coluna_tempo].unique().tolist())

        fig_tempo = px.line(
            df_evolucao, 
            x=coluna_tempo, 
            y="Contagem", 
            markers=True, 
            title=titulo_tempo,
            template="plotly_white",
            color_discrete_sequence=['#ff7f0e']
        )
        
        # Formatação
        fig_tempo.update_yaxes(tickformat=',.') 
        fig_tempo.update_xaxes(
            categoryorder='array', 
            categoryarray=ordem_tempo,
            title_text=coluna_tempo
        )
        fig_tempo.update_layout(showlegend=False)
        
        st.plotly_chart(fig_tempo, use_container_width=True)
            
        st.markdown("---")

        # -------------------------
        # GRÁFICO 4: Motivos Agrupados (Contagem de Solicitações)
        # -------------------------
        st.markdown("##### 📝 Contagem de Solicitações por Motivo Agrupado (Top 10)")
        
        # Alteração: Conta a frequência (size) por Motivo Agrupado
        motivos_contagem = df_filtros.groupby("Motivo_Agrupado").size().reset_index(name='Contagem').sort_values("Contagem", ascending=False)
        
        fig_motivos = px.bar(
            motivos_contagem.head(10), 
            x="Motivo_Agrupado",
            y="Contagem",
            title="Frequência de Solicitações por Motivo",
            template="plotly_white",
            text="Contagem"
        )
        # Formatação
        fig_motivos.update_yaxes(tickformat=',.') 
        fig_motivos.update_xaxes(title_text="Motivo Agrupado", categoryorder='total descending')
        fig_motivos.update_traces(texttemplate='%{text:,.0f}', textposition='outside', marker_color='#d62728')
        fig_motivos.update_layout(yaxis_title="Número de Solicitações")
        st.plotly_chart(fig_motivos, use_container_width=True)

        st.markdown("---")
        
        # -------------------------
        # Exportar Excel Filtrado
        # -------------------------
        excel_filtrado = "dados_filtrados.xlsx"
        df_filtros.to_excel(excel_filtrado, index=False)
        
        with open(excel_filtrado, "rb") as f:
            st.download_button(
                "📥 Baixar Dados Filtrados (Excel)", 
                f, 
                file_name=excel_filtrado, 
                help="Baixa a planilha com todos os dados após o tratamento e aplicação dos filtros."
            )

if __name__ == "__main__":
    main()
