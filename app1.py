import re
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import unicodedata 

# ----------------------------------------------------
# Configuração inicial do Streamlit e Layout
# ----------------------------------------------------
st.set_page_config(
    page_title="Analisador de Produtos e Pedidos", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# ----------------------------------------------------
# Novo CSS para tema profissional (DARK MODE, Cards e Tipografia)
# ----------------------------------------------------
st.markdown(
    """
    <style>
    /* 1. Ajuste de Padding Lateral (Menos espaço vazio nas laterais) */
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 0rem;
        padding-left: 2.5rem;
        padding-right: 2.5rem;
    }
    
    /* 2. Alteração da cor de fundo (se o tema for claro) e fontes */
    body {
        font-family: 'Inter', sans-serif;
    }

    /* 3. Estilização Profissional das Métricas (Cards) */
    [data-testid="stMetric"] {
        background-color: #333333; /* Fundo cinza escuro para cards */
        padding: 15px;
        border-radius: 10px;
        color: white; /* Cor do texto principal */
        border-left: 5px solid #00BFFF; /* Linha de destaque em azul claro */
        box-shadow: 2px 2px 8px rgba(0, 0, 0, 0.4);
    }

    /* Título da Métrica */
    [data-testid="stMetricLabel"] > div {
        color: #B0C4DE; /* Cor mais suave para o título da métrica */
        font-weight: 500;
    }

    /* Valor da Métrica */
    [data-testid="stMetricValue"] {
        font-size: 1.8rem;
        font-weight: 700;
        color: #00BFFF; /* Cor de destaque para os valores */
    }
    
    /* 4. Títulos (Headers) com cor de destaque */
    h1, h2, h3, h4, h5, h6 {
        color: #D3D3D3; /* Cinza claro para títulos */
    }

    /* 5. Linhas separadoras */
    hr {
        margin-top: 1rem;
        margin-bottom: 1rem;
        border-top: 2px solid #555555;
    }

    /* 6. Cor do seletor de estado principal (para contraste no tema escuro) */
    [data-testid="stSelectbox"] div[role="combobox"] {
        background-color: #444444; 
    }

    /* 7. Sidebar com visual mais limpo e ALARGADA (Mantido) */
    .css-1d391kg {
        background-color: #222222; /* Fundo escuro para sidebar */
        width: 300px; /* Ajuste para alargar a sidebar e corrigir o corte da data */
    }
    
    /* 8. Ajuste para o widget de data na sidebar (Mantido) */
    .css-1l2st0e, .css-1dp5if4, .css-7ym5gk {
        width: 100% !important;
    }
    
    /* 9. Ajuste para o widget de data na sidebar, permitindo o calendário ser exibido corretamente */
    /* Este é um truque para garantir que o date_input funcione bem com a sidebar alargada */
    [data-testid="stSidebar"] [data-testid="stDateInput"] {
        z-index: 1000;
    }


    </style>
    """,
    unsafe_allow_html=True
)

# -------------------------
# Funções auxiliares de formatação (Formato Power BI: X,XX M)
# -------------------------

def formatar_valor_metrica(numero):
    """
    Formata um número grande em formato métrico (K, M, B) para exibição compacta, 
    usando até duas casas decimais, conforme o estilo Power BI.
    """
    if pd.isna(numero) or numero is None:
        return "R$ N/A"

    numero_original = numero
    numero = abs(numero)
    
    # Define os limites
    bilhao = 1_000_000_000
    milhao = 1_000_000
    mil = 1_000

    prefixo = ""
    divisor = 1
    
    # Determina o prefixo e o divisor
    if numero >= bilhao:
        prefixo = " B"
        divisor = bilhao
    elif numero >= milhao:
        prefixo = " M"
        divisor = milhao
    elif numero >= mil:
        prefixo = " K"
        divisor = mil
    else:
        # Se for menor que mil, retorna no formato BR normal (ex: R$ 482,23)
        return f"R$ {numero_original:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        
    # Calcula o valor na nova unidade
    valor_na_unidade = numero_original / divisor
    
    # Formata o número resultante para ter apenas 2 casas decimais e usa o formato BR (vírgula decimal)
    valor_formatado = f"{valor_na_unidade:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    
    return f"R$ {valor_formatado}{prefixo}"


# -------------------------
# Função para extrair produtos, quantidades e preços (Mantido)
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
            # Adiciona com quantidade 1 como padrão se não foi encontrado com quantidade
            if not any(r[0] == cod and r[1] is not None for r in resultados):
                 resultados.append((cod, 1, None)) 


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
# Funções auxiliares de padronização (Mantido)
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
    """Remove acentos de uma string, transformando 'Paraná' em 'Parana' para a comparação."""
    if not isinstance(texto, str):
        return texto
    # Normaliza para forma D (separando caractere e acento) e filtra o acento (categoria 'Mn')
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')


def padronizar_entidade(texto, mapeamento_personalizado=None):
    """
    Padroniza um campo de texto (Solicitante, Estado) removendo acentos e usando um mapeamento.
    """
    if not isinstance(texto, str):
        return texto
        
    # 1. Normaliza para minúsculas e remove acentos para criar a chave de comparação
    chave = remover_acentos(texto).strip().lower() 
    
    # 2. Mapeamento padrão para o Dashboard (Você pode expandir isso aqui!)
    mapa = {
        # --- Padronização de ESTADOS ---
        "ms": "Mato Grosso do Sul",
        "mato grosso do sul": "Mato Grosso do Sul",
        "sc": "Santa Catarina",
        "rs": "Rio Grande do Sul",
        "pr": "Paraná",
        "parana": "Paraná",
        "sp": "São Paulo",
        "sao paulo": "São Paulo",
        
        # --- Padronização de NOMES / SOLICITANTES ---
        "griele": "Grieli", 
        "bianca nunes": "Bianca", 
        "sarah macieski": "Sarah", 
        "renata jesus": "Renata",
        "renata rodrigues": "Renata",
        
        # O mapeamento personalizado (se fornecido) tem prioridade
        **(mapeamento_personalizado if mapeamento_personalizado else {})
    }
    
    # 3. Retorna o valor padronizado se encontrado, senão retorna o texto original formatado (Title Case)
    return mapa.get(chave, formatar_texto(texto))


def padronizar_estado(estado):
    """Aplica a padronização para o campo Estado."""
    return padronizar_entidade(estado)

def padronizar_solicitante(solicitante):
    """Aplica a padronização para o campo Solicitante, usando o mapeamento de nomes."""
    return padronizar_entidade(solicitante)

def padronizar_produto(prod):
    """Remove zeros à esquerda (ex: '00012026' -> '12026')."""
    if not isinstance(prod, str):
        prod = str(prod)
    
    prod = prod.strip()
    
    # Remove zeros à esquerda se for um código numérico
    try:
        if prod.isdigit():
            # Converte para inteiro (remove zeros) e depois para string
            return str(int(prod))
    except ValueError:
        pass 

    return prod.strip()

def padronizar_motivo(motivo):
    """Agrupa variações de motivos de negociação em categorias mais amplas."""
    if not isinstance(motivo, str):
        return 'Não Informado'
    motivo = motivo.strip().lower()
    if not motivo:
        return 'Não Informado'

    # Agrupamento de motivos 
    
    if 'desconto' in motivo or 'promocao' in motivo or 'solicitou desconto' in motivo:
        return 'Solicitou Desconto / Promoção'
        
    if 'volume' in motivo or 'quantidade' in motivo or 'aumentar' in motivo or 'quer preco para quantidade' in motivo:
        return 'Aumento Volume / Quantidade'
        
    if 'negociacao' in motivo or 'melhorar' in motivo or 'melhores condicoes' in motivo or 'preço' in motivo or 'preco' in motivo or 'cliente pedido negociacao' in motivo or 'cliente pedido p melhorar' in motivo:
        return 'Negociação / Melhor Condição de Preço'
        
    if 'pagou' in motivo or 'ultima vez' in motivo:
        return 'Cliente Pagou da Última Vez'
    if 'manter' in motivo or 'manter os valores' in motivo or 'cliente pedindo para manter os valores' in motivo:
        return 'Manter Valores'
    if 'solicitou' in motivo or 'pedido' in motivo or 'cliente solicitou' in motivo or 'cliente pediu' in motivo:
        return 'Outra Solicitação do Cliente'

    return formatar_texto(motivo)

# -------------------------
# App principal
# -------------------------
def main():
    st.title("📦📈 Dashboard Estratégico de Solicitações de Produtos")
    
    # -------------------------
    # LAYOUT DE FILTRO PRINCIPAL (Estado)
    # -------------------------
    st.markdown("---") # Linha divisória
    
    # Carregador de Arquivo
    arquivo = st.file_uploader("Carregue a planilha Excel", type=["xlsx"], help="A planilha deve conter os dados de resposta do formulário.")
    
    st.markdown("---") # Linha divisória

    if arquivo:
        # Carregar dados
        try:
            df = pd.read_excel(arquivo, sheet_name="Respostas do Formulário 1")
        except:
            st.error("Erro ao carregar a aba 'Respostas do Formulário 1'. Verifique o nome da aba no seu arquivo.")
            return

        df.columns = df.columns.str.strip()

        # -------------------------
        # Tratamento de Dados (Mantido)
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
                    "Contagem_Solicitacao": 1, 
                })

        df_tratado = pd.DataFrame(dados_tratados)

        # Limpeza e criação de colunas de tempo
        df_tratado["Data"] = pd.to_datetime(df_tratado["Data"], errors="coerce")
        df_tratado["Data_Dia"] = df_tratado["Data"].dt.strftime("%Y-%m-%d") # Nova coluna para Dia (chave do heatmap)
        df_tratado["AnoMes"] = df_tratado["Data"].dt.to_period("M").astype(str)
        df_tratado["AnoSemana"] = df_tratado["Data"].dt.strftime("%Y-%W") 

        # Filtragem de dados nulos/inválidos
        df_tratado = df_tratado.dropna(subset=["Produto"])
        df_tratado = df_tratado[df_tratado["Produto"].str.lower() != "none"]

        # Padronização
        df_tratado["Produto"] = df_tratado["Produto"].apply(padronizar_produto)
        df_tratado["Estado"] = df_tratado["Estado"].apply(padronizar_estado)
        df_tratado["Solicitante"] = df_tratado["Solicitante"].apply(padronizar_solicitante)
        df_tratado["Motivo_Agrupado"] = df_tratado["Motivo"].apply(padronizar_motivo)
        
        # Cálculo do Valor Total do Item
        df_tratado["Valor_Total_Item"] = df_tratado["Quantidade"] * df_tratado["Preco_Solicitado"]
        
        # -------------------------
        # Filtros Interativos (Sidebar)
        # -------------------------
        st.sidebar.header("Filtros de Análise Secundários")
        
        # 1. Filtro de Data
        data_validas = df_tratado["Data"].dropna().dt.date
        if data_validas.empty:
            # Caso não haja datas válidas, usa a data de hoje como fallback
            min_date = datetime.now().date()
            max_date = datetime.now().date()
        else:
            min_date = data_validas.min()
            max_date = data_validas.max()

        # Ajuste: Usar colunas na sidebar para dar mais espaço ao date_input
        st.sidebar.markdown("##### 📅 Filtro por Período")
        col_data1, col_data2 = st.sidebar.columns(2)
        with col_data1:
            # Ajuste de tamanho implícito devido ao CSS .css-1d391kg (width: 300px) e colunas
            data_inicio = st.date_input("De", value=min_date, min_value=min_date, max_value=max_date, key='data_inicio')
        with col_data2:
            data_fim = st.date_input("Até", value=max_date, min_value=min_date, max_value=max_date, key='data_fim')

        # 2. Outros Filtros Secundários
        produto_sel = st.sidebar.multiselect("📦 Produto", sorted(df_tratado["Produto"].dropna().astype(str).unique()))
        solicitante_sel = st.sidebar.multiselect("🧑 Solicitante", sorted(df_tratado["Solicitante"].dropna().astype(str).unique()))
        motivo_sel = st.sidebar.multiselect("📝 Motivo Agrupado", sorted(df_tratado["Motivo_Agrupado"].dropna().astype(str).unique()))

        # Aplicação dos Filtros Secundários
        df_filtros = df_tratado.copy()
        
        # Filtro de Data
        df_filtros = df_filtros[
            (df_filtros["Data"].dt.date >= data_inicio) & 
            (df_filtros["Data"].dt.date <= data_fim)
        ]

        if produto_sel:
            df_filtros = df_filtros[df_filtros["Produto"].isin(produto_sel)]
        if solicitante_sel:
            df_filtros = df_filtros[df_filtros["Solicitante"].isin(solicitante_sel)]
        if motivo_sel:
            df_filtros = df_filtros[df_filtros["Motivo_Agrupado"].isin(motivo_sel)]
            
        if df_filtros.empty:
            st.warning("Nenhum dado encontrado com os filtros de data/secundários selecionados.")
            return

        # -------------------------
        # CARTÃO DE FILTRO DE ESTADO (Área Principal) - Movido para o topo da área principal
        # -------------------------
        lista_estados = sorted(df_filtros["Estado"].dropna().astype(str).unique())
        opcoes_estados = ["Todos"] + lista_estados
        
        estado_selecionado = st.selectbox(
            "📍 **Filtrar por Estado (Card Principal)**", 
            opcoes_estados, 
            index=0,
            help="Selecione um único estado para refinar as análises no dashboard."
        )

        # Aplicar o filtro de Estado principal
        if estado_selecionado != "Todos":
            df_filtros = df_filtros[df_filtros["Estado"] == estado_selecionado]
        
        # Checagem final após filtro de estado
        if df_filtros.empty:
            st.warning(f"Nenhum dado encontrado para o Estado: {estado_selecionado}.")
            return
            
        st.markdown("---")
        
        # -------------------------
        # Métricas Chave (Cards Profissionais)
        # -------------------------
        total_solicitacoes = df_filtros.shape[0] 
        total_quantidade = df_filtros["Quantidade"].sum()
        total_valor_negociado = df_filtros["Valor_Total_Item"].sum()
        
        # Usando um layout de coluna para os cards de métricas
        col_metrica1, col_metrica2, col_metrica3, col_metrica4 = st.columns(4, gap='large')
        
        # Métrica 1: Total de Solicitações
        with col_metrica1:
            st.metric("Total de Solicitações", f"{total_solicitacoes:,}".replace(",", "."))
        
        # Métrica 2: Volume Total de Itens
        with col_metrica2:
            display_total_quantidade_short = formatar_valor_metrica(total_quantidade).replace("R$ ", "")
            display_total_quantidade_long = f"{total_quantidade:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")

            st.metric(
                "Volume Total de Itens", 
                display_total_quantidade_short,
                help=f"Volume exato: {display_total_quantidade_long}. Valores são formatados com K (Mil), M (Milhão) ou B (Bilhão)."
            )
        
        # Métrica 3: Valor Total Negociado
        with col_metrica3:
            display_total_valor_short = formatar_valor_metrica(total_valor_negociado)

            if not pd.isna(total_valor_negociado):
                display_total_valor_long = f"R$ {total_valor_negociado:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            else:
                display_total_valor_long = "R$ 0,00"
                
            st.metric(
                "Valor Total Negociado", 
                display_total_valor_short, 
                help=f"Valor exato negociado: {display_total_valor_long}. Valores são formatados com K (Mil), M (Milhão) ou B (Bilhão)."
            )
            
        # Métrica 4: Total de Produtos Únicos
        with col_metrica4:
            st.metric("Total de Produtos Únicos", df_filtros["Produto"].nunique())

        st.markdown("---")

        # -------------------------
        # Configuração de Template do Plotly (Visuais Profissionais)
        # -------------------------
        PLOTLY_TEMPLATE = "plotly_dark" 
        
        # Definição de Cores
        COLOR_VOLUME = '#1f77b4'  # Azul corporativo
        COLOR_FREQUENCIA = '#ff7f0e' # Laranja para contraste
        COLOR_SOLICITANTE = '#2ca02c' # Verde
        COLOR_MOTIVO = '#d62728' # Vermelho/Tijolo
        
        # -------------------------
        # SEÇÃO 1: Análise Comparativa de Produtos (Mantido)
        # -------------------------
        st.subheader("Análise 1: Comparativo de Produtos (Volume vs. Frequência)")
        
        col_g1, col_g2 = st.columns(2, gap='medium')
        
        # --- COLUNA 1: GRÁFICO 1 (VOLUME) ---
        with col_g1:
            st.markdown("##### 📦 Volume Total de Itens por Produto (Top 10)")
            
            top_produtos_volume = df_filtros.groupby("Produto")["Quantidade"].sum().sort_values(ascending=False).head(10).reset_index()
            top_produtos_volume.columns = ["Produto", "Quantidade Total"]
            
            fig_top_produtos_volume = px.bar(
                top_produtos_volume,
                x="Produto",
                y="Quantidade Total",
                title="Top 10 Produtos por Volume",
                template=PLOTLY_TEMPLATE, # Aplicando o template escuro
            )
            
            # Formatação
            fig_top_produtos_volume.update_traces(
                text=top_produtos_volume["Quantidade Total"].apply(lambda x: f"{x:,.0f}".replace(",", ".")), # Formatação BR no texto
                texttemplate='%{text}', 
                textposition='outside', 
                marker_color=COLOR_VOLUME
            ) 
            fig_top_produtos_volume.update_yaxes(tickformat=".2s", title_text="Quantidade Total (Mil/Milhão)") 
            fig_top_produtos_volume.update_xaxes(title_text="Produto (Códigos)")
            st.plotly_chart(fig_top_produtos_volume, use_container_width=True)

        # --- COLUNA 2: GRÁFICO 2 (CONTAGEM DE SOLICITAÇÕES POR PRODUTO) ---
        with col_g2:
            st.markdown("##### 📈 Frequência de Solicitações por Produto (Contagem - Top 10)")
            
            top_produtos_contagem = df_filtros.groupby("Produto").size().reset_index(name='Contagem de Solicitações').sort_values("Contagem de Solicitações", ascending=False).head(10)
            
            fig_top_produtos_contagem = px.bar(
                top_produtos_contagem,
                x="Produto",
                y="Contagem de Solicitações",
                title="Top 10 Produtos por Frequência",
                template=PLOTLY_TEMPLATE, # Aplicando o template escuro
            )
            
            # Formatação
            fig_top_produtos_contagem.update_traces(
                text=top_produtos_contagem["Contagem de Solicitações"].apply(lambda x: f"{x:,.0f}".replace(",", ".")),
                texttemplate='%{text}', 
                textposition='outside', 
                marker_color=COLOR_FREQUENCIA
            ) 
            fig_top_produtos_contagem.update_yaxes(tickformat=',.') 
            fig_top_produtos_contagem.update_xaxes(title_text="Produto (Códigos)")
            st.plotly_chart(fig_top_produtos_contagem, use_container_width=True)


        st.markdown("---")
        
        # -------------------------
        # SEÇÃO 2: Solicitantes e Motivos (Mantido)
        # -------------------------
        st.subheader("Análise 2: Solicitantes e Motivos de Negociação")
        
        col_g3, col_g4 = st.columns(2, gap='medium')

        # --- COLUNA 1: GRÁFICO 3 (SOLICITANTES) ---
        with col_g3:
            st.markdown("##### 🧑 Solicitantes com Maior Frequência de Solicitações (Top 15)")
            
            solicitantes_contagem = df_filtros.groupby("Solicitante").size().reset_index(name='Contagem').sort_values("Contagem", ascending=True).tail(15)
            
            fig_solicitantes = px.bar(
                solicitantes_contagem, 
                x="Contagem",
                y="Solicitante", 
                orientation='h', 
                title="Top 15 Solicitantes",
                template=PLOTLY_TEMPLATE, # Aplicando o template escuro
            )
            
            # Formatação
            fig_solicitantes.update_traces(
                text=solicitantes_contagem["Contagem"].apply(lambda x: f"{x:,.0f}".replace(",", ".")),
                texttemplate='%{text}', 
                textposition='outside', 
                marker_color=COLOR_SOLICITANTE
            )
            fig_solicitantes.update_xaxes(tickformat=".2s", title_text="Número de Solicitações (Mil/Milhão)")
            fig_solicitantes.update_layout(yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_solicitantes, use_container_width=True)

        # --- COLUNA 2: GRÁFICO 4 (MOTIVOS AGRUPADOS) ---
        with col_g4:
            st.markdown("##### 📝 Frequência de Solicitações por Motivo Agrupado (Top 10)")
            
            motivos_contagem = df_filtros.groupby("Motivo_Agrupado").size().reset_index(name='Contagem').sort_values("Contagem", ascending=False)
            
            fig_motivos = px.bar(
                motivos_contagem.head(10), 
                x="Motivo_Agrupado",
                y="Contagem",
                title="Top 10 Motivos",
                template=PLOTLY_TEMPLATE, # Aplicando o template escuro
            )
            
            # Formatação
            fig_motivos.update_traces(
                text=motivos_contagem["Contagem"].head(10).apply(lambda x: f"{x:,.0f}".replace(",", ".")),
                texttemplate='%{text}', 
                textposition='outside', 
                marker_color=COLOR_MOTIVO
            )
            fig_motivos.update_yaxes(tickformat=',.') 
            fig_motivos.update_xaxes(title_text="Motivo Agrupado", categoryorder='total descending')
            fig_motivos.update_layout(yaxis_title="Número de Solicitações")
            st.plotly_chart(fig_motivos, use_container_width=True)
            
        st.markdown("---")

if __name__ == '__main__':
    main()
