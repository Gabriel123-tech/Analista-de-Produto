import re
import pandas as pd
import streamlit as st
import plotly.express as px
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
# CSS (Mantido)
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
    Formata um número financeiro grande em formato métrico (K, M, B) para exibição compacta, 
    usando R$ e vírgula decimal (padrão BR).
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

# VERSÃO FINAL: Função para formatar Quantidade/Volume em K/M/B (sem R$)
def formatar_quantidade_metrica(numero):
    """
    Formata um número grande (volume ou contagem) em notação métrica (K, M, B)
    com vírgula como separador decimal (padrão BR) OU retorna o inteiro formatado (se < 1000).
    """
    if pd.isna(numero) or numero is None:
        return "0"

    numero_original = round(numero) # Arredonda para inteiro para contagem de itens
    
    bilhao = 1_000_000_000
    milhao = 1_000_000
    mil = 1_000

    prefixo = ""
    divisor = 1
    casas_decimais = 2
    
    if numero_original >= bilhao:
        prefixo = " B"
        divisor = bilhao
    elif numero_original >= milhao:
        prefixo = " M"
        divisor = milhao
    elif numero_original >= mil:
        prefixo = " K"
        divisor = mil
    else:
        # Se for menor que mil, retorna o próprio valor inteiro como string 
        # Formata com separador de milhar para facilitar a leitura (Ex: "9.876")
        return f"{numero_original:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")
        
    # Lógica de formatação para K, M, B
    valor_na_unidade = numero_original / divisor
    
    formato = "{:,." + str(casas_decimais) + "f}"
    valor_formatado = formato.format(valor_na_unidade)
    
    # Faz a substituição do separador decimal: Ponto(EUA) -> Vírgula(BR)
    valor_formatado_br = valor_formatado.replace(",", "X").replace(".", ",").replace("X", ".")
    
    return f"{valor_formatado_br}{prefixo}".strip()
# ------------------------------------


# -------------------------
# Funções auxiliares de extração e padronização 
# -------------------------
def extrair_produtos(texto):
    """
    Extrai código, quantidade e preço de um texto usando diversos padrões,
    com lógica aprimorada para distinguir CÓDIGO (5+ dígitos) de QUANTIDADE 
    e mitigar a atribuição de grandes volumes.
    """
    if not isinstance(texto, str):
        return []

    texto = texto.upper()
    resultados = []
    codigos_extraidos = set() # Conjunto para rastrear códigos já encontrados

    # --- REGEX 1: PADRÕES CLAROS (CÓDIGO X QUANTIDADE) ---
    # Prioriza padrões explícitos como '23131 X 4', '4 - 23131', '4UN 23131'
    padroes_com_qtd_separador = [
        # Padrão: CÓDIGO (5+) seguido por separador e QTD (1+)
        r"(\d{5,})\s*[X-]\s*(\d{1,})", 
        # Padrão: QTD (1+) seguido por separador e CÓDIGO (5+)
        r"(\d{1,})\s*[X-]\s*(\d{5,})", 
        # Padrão: QTD (1+) seguida de UN/UNID e CÓDIGO (5+)
        r"(\d{1,})\s*(?:UN|UNID|UND|UNIDADES?)\s*(\d{5,})",
    ]

    # Limite de sanidade para a Quantidade (ex: 5000 itens é um volume razoável)
    LIMITE_QTD_MAXIMA = 5000

    for padrao in padroes_com_qtd_separador:
        for a, b in re.findall(padrao, texto):
            
            # --- LÓGICA DE DEFINIÇÃO DE CÓDIGO E QUANTIDADE ---
            cod, qtd_str = None, None
            
            # Caso 1: A é CÓDIGO (5+) e B é QTD (menos de 5 dígitos)
            if len(a) >= 5 and len(b) < 5:
                cod = padronizar_produto(a)
                qtd_str = b
            # Caso 2: B é CÓDIGO (5+) e A é QTD (menos de 5 dígitos)
            elif len(b) >= 5 and len(a) < 5:
                cod = padronizar_produto(b)
                qtd_str = a
            else:
                 # Se ambos tiverem 5+ dígitos, ignora (evita falsos positivos em números grandes)
                continue
            
            # --- CONVERSÃO E VALIDAÇÃO DE QUANTIDADE ---
            try:
                qtd = int(qtd_str)
            except ValueError:
                continue 
                
            if cod and qtd > 0 and qtd <= LIMITE_QTD_MAXIMA:
                if cod not in codigos_extraidos:
                    resultados.append((cod, qtd, None))
                    codigos_extraidos.add(cod)

    # --- REGEX 2: CÓDIGOS SOLTOS (5+ dígitos, sem quantidade clara) ---
    # Só adiciona se o código NÃO foi encontrado com quantidade explícita antes
    produtos_soltos = re.findall(r"\b\d{5,}\b", texto)
    for cod in produtos_soltos:
        cod_padronizado = padronizar_produto(cod)
        
        if cod_padronizado not in codigos_extraidos:
            # Adiciona com quantidade 1 como padrão
            resultados.append((cod_padronizado, 1, None))
            codigos_extraidos.add(cod_padronizado)


    # --- REGEX 3: EXTRAÇÃO DE PREÇOS (Opcional) ---
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
    if not isinstance(texto, str):
        return texto
    chave = remover_acentos(texto).strip().lower()
    mapa = {
        'griele': 'Griele',
        'grieli': 'Griele',
        'bianca': 'Bianca',
        'bianca nunes': 'Bianca',
        'bianca silva': 'Bianca',
        'sarah': 'Sarah',
        'sara': 'Sarah',
        'sarah macieski': 'Sarah',
        'renata rodrigues': 'Rodrigues',
        'renata soares': 'Rodrigues',
        'renata jesus': 'Jesus',
        'ms': 'MS',
        'mato grosso do sul': 'MS',
        'mato': 'MS',
        'sc': 'SC',
        'santa catarina': 'SC',
        'rs': 'RS',
        'rio grande do sul': 'RS',
        'pr': 'PR',
        'parana': 'PR',
        'sp': 'SP',
        'sao paulo': 'SP'
    }
    if chave == 'renata':
        return None
    if chave.startswith('renata'):
        if 'rodrigues' in chave or 'soares' in chave:
            return 'Rodrigues'
        elif 'jesus' in chave:
            return 'Jesus'
        else:
            return texto.split()[-1].title()
    return mapa.get(chave, texto.split()[0].title())
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

# ------------------------------------
# Função de Carregamento e Tratamento (Com Cache e Spinner)
# ------------------------------------

@st.cache_data
def load_data(arquivo):
    """
    Carrega o arquivo, trata e padroniza os dados.
    Esta função usa o cache para evitar reprocessamento desnecessário.
    """
    try:
        # Tenta carregar a aba correta
        df = pd.read_excel(arquivo, sheet_name="Respostas do Formulário 1")
    except ValueError:
        st.error("Erro: A planilha 'Respostas do Formulário 1' não foi encontrada. Verifique o nome da aba.")
        return pd.DataFrame() 
    except Exception as e:
        st.error(f"Erro ao carregar o arquivo: {e}")
        return pd.DataFrame()

    df.columns = df.columns.str.strip()

    # Mapeamento de Colunas (para maior flexibilidade e evitar KeyError)
    # A coluna de data de formulários do Google/Microsoft é frequentemente "Carimbo de data/hora"
    coluna_data = "Carimbo de data/hora" 
    coluna_produto_preco = "CODIGO DO PRODUTO, QUANTIDADE E PREÇO SOLICITADO:"
    coluna_analise = "ANALISE NEGOCIAÇÃO"
    coluna_estado = "ESTADO:"
    coluna_solicitante = "SOLICITANTE:"
    coluna_motivo = "MOTIVO:"
    
    # Verifica a existência das colunas
    coluna_data = coluna_data if coluna_data in df.columns else (
        "Data" if "Data" in df.columns else None
    )
    coluna_produto_preco = coluna_produto_preco if coluna_produto_preco in df.columns else None
    coluna_analise = coluna_analise if coluna_analise in df.columns else None
    coluna_estado = coluna_estado if coluna_estado in df.columns else None
    coluna_solicitante = coluna_solicitante if coluna_solicitante in df.columns else None
    coluna_motivo = coluna_motivo if coluna_motivo in df.columns else None

    # Se a coluna principal de extração não existir, emite um aviso e interrompe
    if not (coluna_produto_preco or coluna_analise):
        st.warning("Não foi possível encontrar as colunas de texto para extração (ex: 'CODIGO DO PRODUTO, QUANTIDADE E PREÇO SOLICITADO:'). Verifique o nome das colunas.")
        return pd.DataFrame()
    
    dados_tratados = []

    for index, row in df.iterrows():
        # Combina as duas colunas de texto para maximizar a extração
        texto_produtos = str(row.get(coluna_produto_preco, "")) + " " + str(row.get(coluna_analise, ""))
        
        produtos_extraidos = extrair_produtos(texto_produtos)
        campos_extras = extrair_campos(texto_produtos)

        # Prioriza colunas diretas da planilha, depois a extração do texto
        estado = formatar_texto(row.get(coluna_estado, None)) or campos_extras.get('Estado')
        solicitante = formatar_texto(row.get(coluna_solicitante, None)) or campos_extras.get('Solicitante')
        motivo = formatar_texto(row.get(coluna_motivo, None)) or campos_extras.get('Motivo')

        for produto, qtd, preco in produtos_extraidos:
            dados_tratados.append({
                "Data": row.get(coluna_data, None), 
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
    df_tratado = df_tratado.dropna(subset=["Data"]) # Remove linhas sem data válida

    df_tratado["Data_Dia"] = df_tratado["Data"].dt.strftime("%Y-%m-%d") 
    df_tratado["AnoMes"] = df_tratado["Data"].dt.to_period("M").astype(str)
    df_tratado["AnoSemana"] = df_tratado["Data"].dt.strftime("%Y-%W") 

    # Filtragem de dados nulos/inválidos de Produto
    df_tratado = df_tratado.dropna(subset=["Produto"])
    df_tratado = df_tratado[df_tratado["Produto"].str.lower() != "none"]

    # Ajuste: Garantir que Quantidade é um número inteiro ANTES DA AGREGAÇÃO
    df_tratado["Quantidade"] = pd.to_numeric(df_tratado["Quantidade"], errors='coerce').fillna(0).astype(int) 

    # Padronização
    df_tratado["Produto"] = df_tratado["Produto"].apply(padronizar_produto)
    df_tratado["Estado"] = df_tratado["Estado"].apply(padronizar_estado)
    df_tratado["Solicitante"] = df_tratado["Solicitante"].apply(padronizar_solicitante)
    df_tratado["Motivo_Agrupado"] = df_tratado["Motivo"].apply(padronizar_motivo)
    
    # Cálculo do Valor Total do Item
    df_tratado["Valor_Total_Item"] = df_tratado["Quantidade"] * df_tratado["Preco_Solicitado"]

    return df_tratado

# -------------------------
# App principal
# -------------------------
def main():
    st.title("📦📈 Dashboard Estratégico de Solicitações de Negociação")
    
    # -------------------------
    # LAYOUT DE FILTRO PRINCIPAL (Estado)
    # -------------------------
    st.markdown("---") # Linha divisória
    
    # Carregador de Arquivo
    arquivo = st.file_uploader("Carregue a planilha Excel", type=["xlsx"], help="A planilha deve conter os dados de resposta do formulário.")
    
    st.markdown("---") # Linha divisória

    if arquivo:
        # -------------------------
        # Carregar e Tratar Dados com Cache
        # -------------------------
        # Força o recarregamento dos dados se o arquivo mudar
        if 'arquivo_hash' not in st.session_state or st.session_state['arquivo_hash'] != hash(arquivo.read()):
            # Atualiza o hash e limpa o cache para forçar o load_data a rodar
            st.session_state['arquivo_hash'] = hash(arquivo.read())
            load_data.clear()
            arquivo.seek(0) # Volta o ponteiro do arquivo para o início

        with st.spinner('Processando e limpando os dados. Isso pode levar alguns segundos...'):
            # Passa o objeto arquivo, não o hash
            df_tratado = load_data(arquivo) 
        
        if df_tratado.empty:
            return

        # -------------------------
        # Filtros Interativos (Sidebar) 
        # -------------------------
        st.sidebar.header("Filtros de Análise Secundários")
        
        # 1. Filtro de Data
        data_validas = df_tratado["Data"].dropna().dt.date
        if data_validas.empty:
            min_date = datetime.now().date()
            max_date = datetime.now().date()
        else:
            min_date = data_validas.min()
            max_date = data_validas.max()

        # Ajuste: Usar colunas na sidebar para dar mais espaço ao date_input
        st.sidebar.markdown("##### 📅 Filtro por Período")
        col_data1, col_data2 = st.sidebar.columns(2)
        with col_data1:
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
        # CARTÃO DE FILTRO DE ESTADO (Área Principal) 
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
            st.warning(f"Nenhum dado encontrado para o Estado: **{estado_selecionado}**.")
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
            st.metric("Total de Solicitações", f"{total_solicitacoes:,.0f}".replace(",", "X").replace(".", ",").replace("X", "."))
        
        # Métrica 2: Volume Total de Itens (Usa a função de K/M/B)
        with col_metrica2:
            display_total_quantidade_short = formatar_quantidade_metrica(total_quantidade)
            
            display_total_quantidade_long = f"{total_quantidade:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")

            st.metric(
                "Volume Total de Itens", 
                display_total_quantidade_short,
                help=f"Volume exato: {display_total_quantidade_long}. Valores são formatados com K (Mil), M (Milhão) ou B (Bilhão)."
            )
        
        # Métrica 3: Valor Total Negociado (Usa a função de R$ K/M/B)
        with col_metrica3:
            display_total_valor_short = formatar_valor_metrica(total_valor_negociado)

            if not pd.isna(total_valor_negociado) and total_valor_negociado is not None:
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
        # Configuração de Template do Plotly 
        # -------------------------
        PLOTLY_TEMPLATE = "plotly_dark" 
        
        # Definição de Cores
        COLOR_VOLUME = '#1f77b4' # Azul corporativo
        COLOR_FREQUENCIA = '#ff7f0e' # Laranja para contraste
        COLOR_SOLICITANTE = '#2ca02c' # Verde
        COLOR_MOTIVO = '#d62728' # Vermelho/Tijolo
        
        # -------------------------
        # SEÇÃO 1: Análise Comparativa de Produtos
        # -------------------------
        st.subheader("Análise 1: Comparativo de Produtos (Volume de Itens vs. Frequência de Solicitação)")
        
        col_g1, col_g2 = st.columns(2, gap='medium')
        
        # --- COLUNA 1: GRÁFICO 1 (VOLUME) ---
        with col_g1:
            st.markdown("##### 📦 Volume Total de Itens por Produto (Top 10)")
            
            # Cálculo de Volume: SOMA da coluna Quantidade
            top_produtos_volume = df_filtros.groupby("Produto")["Quantidade"].sum().sort_values(ascending=False).head(10).reset_index()
            top_produtos_volume.columns = ["Produto", "Quantidade Total"]
            
            fig_top_produtos_volume = px.bar(
                top_produtos_volume,
                x="Produto",
                y="Quantidade Total",
                title="Top 10 Produtos por Volume de Itens",
                template=PLOTLY_TEMPLATE, 
            )
            
            # Formatação: Usa a função formatar_quantidade_metrica para exibir o valor em K/M/B
            fig_top_produtos_volume.update_traces(
                text=top_produtos_volume["Quantidade Total"].apply(formatar_quantidade_metrica), 
                texttemplate='%{text}', 
                textposition='outside', 
                marker_color=COLOR_VOLUME
            ) 
            fig_top_produtos_volume.update_yaxes(tickformat=".2s", title_text="Quantidade Total (Mil/Milhão)") 
            fig_top_produtos_volume.update_xaxes(title_text="Produto (Códigos)")
            st.plotly_chart(fig_top_produtos_volume, use_container_width=True)

        # --- COLUNA 2: GRÁFICO 2 (CONTAGEM DE SOLICITAÇÕES POR PRODUTO) ---
        with col_g2:
            st.markdown("##### 📈 Frequência de Solicitações por Produto (Top 10)")
            
            # Cálculo de Frequência: CONTAGEM de linhas (solicitações)
            top_produtos_contagem = df_filtros.groupby("Produto").size().reset_index(name='Contagem de Solicitações').sort_values("Contagem de Solicitações", ascending=False).head(10)
            
            fig_top_produtos_contagem = px.bar(
                top_produtos_contagem,
                x="Produto",
                y="Contagem de Solicitações",
                title="Top 10 Produtos por Frequência de Solicitação",
                template=PLOTLY_TEMPLATE, 
            )
            
            # Formatação: Exibe o número inteiro da contagem (Ex: 5)
            fig_top_produtos_contagem.update_traces(
                # Garante que o número seja exibido sem separador decimal (apenas separador de milhar se > 1000)
                text=top_produtos_contagem["Contagem de Solicitações"].apply(lambda x: f"{x:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")),
                texttemplate='%{text}', 
                textposition='outside', 
                marker_color=COLOR_FREQUENCIA
            ) 
            fig_top_produtos_contagem.update_yaxes(tickformat=',.', title_text="Número de Solicitações") 
            fig_top_produtos_contagem.update_xaxes(title_text="Produto (Códigos)")
            st.plotly_chart(fig_top_produtos_contagem, use_container_width=True)


        st.markdown("---")
        
        # -------------------------
        # SEÇÃO 2: Solicitantes e Motivos 
        # -------------------------
        st.subheader("Análise 2: Solicitantes e Motivos de Negociação")
        
        col_g3, col_g4 = st.columns(2, gap='medium')

        # --- COLUNA 1: GRÁFICO 3 (SOLICITANTES) ---
        with col_g3:
            st.markdown("##### 🧑 Solicitantes com Maior Frequência de Solicitações (Top 15)")
            
            # Ordena ascendentemente para que o gráfico de barras horizontais fique do maior para o menor
            solicitantes_contagem = df_filtros.groupby("Solicitante").size().reset_index(name='Contagem').sort_values("Contagem", ascending=True).tail(15)
            
            fig_solicitantes = px.bar(
                solicitantes_contagem, 
                x="Contagem",
                y="Solicitante", 
                orientation='h', 
                title="Top 15 Solicitantes",
                template=PLOTLY_TEMPLATE, 
            )
            
            # Formatação 
            fig_solicitantes.update_traces(
                text=solicitantes_contagem["Contagem"].apply(formatar_quantidade_metrica), 
                texttemplate='%{text}', 
                textposition='outside', 
                marker_color=COLOR_SOLICITANTE
            )
            # Mantém tickformat compacto para o Plotly cuidar do eixo
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
                template=PLOTLY_TEMPLATE, 
            )
            
            # Formatação 
            fig_motivos.update_traces(
                # Garante que o número seja exibido sem separador decimal (apenas separador de milhar se > 1000)
                text=motivos_contagem["Contagem"].head(10).apply(lambda x: f"{x:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")),
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
    # Adiciona o estado de sessão para controle de cache
    if 'arquivo_hash' not in st.session_state:
        st.session_state['arquivo_hash'] = None
        
    main()

