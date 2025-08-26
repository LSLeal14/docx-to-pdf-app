import pandas as pd
from firebase_admin import firestore
import streamlit as st
# Se você for usar esta função em um script que não seja o principal do Streamlit,
# pode ser necessário inicializar o Firebase aqui também.
# No entanto, o ideal é passar o cliente 'db' já inicializado como argumento.

def gerar_tabela_percentual(db: firestore.client, project_id: str) -> pd.DataFrame:
    """
    Busca os dados de um projeto no Firestore, calcula o percentual de cada etapa
    em relação ao valor total do projeto e retorna um DataFrame formatado.

    Esta função é projetada para ser a "Tabela 1".

    Args:
        db (firestore.client): O cliente do Firestore já inicializado.
        project_id (str): O ID do documento do projeto a ser processado.

    Returns:
        pd.DataFrame: Um DataFrame com as colunas 'Item', 'Total por etapa', e
                      'Percentual da etapa no total'. Retorna None se o projeto
                      não for encontrado ou ocorrer um erro.
    """
    try:
        # 1. Buscar o documento do projeto específico no Firestore
        doc_ref = db.collection("projetos").document(project_id)
        doc = doc_ref.get()

        if not doc.exists:
            st.error(f"Erro: Projeto com ID '{project_id}' não foi encontrado.")
            return None

        # 2. Extrair os dados da tabela de dentro do documento
        project_data = doc.to_dict()
        tabela_dados = project_data.get("table", [])

        # Se a tabela estiver vazia, retorna um DataFrame vazio com as colunas certas
        if not tabela_dados:
            return pd.DataFrame(columns=['Item', 'Total por etapa', 'Percentual da etapa no total'])

        # 3. Converter os dados extraídos para um DataFrame do Pandas
        df = pd.DataFrame(tabela_dados)

        # 4. Garantir que a coluna 'Total por etapa' seja numérica para o cálculo
        #    Valores que não são números serão convertidos para 0.
        df['Total por etapa'] = pd.to_numeric(df['Total por etapa'], errors='coerce').fillna(0)

        # 5. Calcular o valor total do projeto somando todos os totais de etapa
        valor_total_projeto = df['Total por etapa'].sum()

        # 6. Calcular a nova coluna de percentual
        if valor_total_projeto > 0:
            # A fórmula é (valor da etapa / valor total) * 100
            df['Percentual da etapa no total'] = (df['Total por etapa'] / valor_total_projeto) * 100
            # Formata a coluna para exibir como um texto com duas casas decimais e o símbolo '%'
            df['Percentual da etapa no total'] = df['Percentual da etapa no total'].apply(lambda x: f"{x:.2f}%")
        else:
            # Caso o total seja 0, define o percentual como "0.00%" para evitar divisão por zero
            df['Percentual da etapa no total'] = "0.00%"

        # 7. Selecionar e reordenar as colunas para criar a "Tabela 1" final
        tabela_1 = df[['Item', 'Total por etapa', 'Percentual da etapa no total']].copy()

        return tabela_1

    except Exception as e:
        print(f"Ocorreu um erro inesperado ao gerar a tabela para o projeto {project_id}: {e}")
        # Em um app real, você poderia usar st.error(e) se esta função for chamada de dentro do Streamlit
        return None