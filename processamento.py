import pandas as pd
from firebase_admin import firestore
import streamlit as st

# A função de gerar a Tabela 1 permanece a mesma, como referência.
def gerar_tabela_percentual(db: firestore.client, project_id: str) -> pd.DataFrame:
    """
    Busca os dados de um projeto no Firestore, calcula o percentual de cada etapa
    em relação ao valor total do projeto e retorna um DataFrame formatado.
    """
    try:
        # 1. Buscar no documento do projeto no Firestore 
        doc_ref = db.collection("projetos").document(project_id)
        doc = doc_ref.get()

        if not doc.exists:
            st.error(f"Erro: Projeto com ID '{project_id}' não foi encontrado.")
            return None

        project_data = doc.to_dict()

        # 2. Extrai dados 
        tabela_dados = project_data.get("table", [])

        if not tabela_dados:
            return pd.DataFrame(columns=['Item', 'Total por etapa', 'Percentual da etapa no total'])

        df = pd.DataFrame(tabela_dados)
        df['Total por etapa'] = pd.to_numeric(df['Total por etapa'], errors='coerce').fillna(0)
        valor_total_projeto = df['Total por etapa'].sum()

        if valor_total_projeto > 0:
            df['Percentual da etapa no total'] = (df['Total por etapa'] / valor_total_projeto) * 100
            df['Percentual da etapa no total'] = df['Percentual da etapa no total'].apply(lambda x: f"{x:.2f}%")
        else:
            df['Percentual da etapa no total'] = "0.00%"

        tabela_1 = df[['Item', 'Total por etapa', 'Percentual da etapa no total']].copy()
        return tabela_1

    except Exception as e:
        st.error(f"Ocorreu um erro inesperado ao gerar a tabela para o projeto {project_id}: {e}")
        return None

def gerar_tabela_previsto_realizado(db: firestore.client, project_id: str) -> pd.DataFrame:
    """
    Gera uma tabela comparativa acumulada entre o planejamento e a medição.

    A função identifica o último mês com dados na tabela de medição e calcula
    os totais previstos e realizados acumulados até esse mês específico.

    Args:
        db (firestore.client): O cliente do Firestore já inicializado.
        project_id (str): O ID do documento do projeto a ser processado.

    Returns:
        pd.DataFrame: DataFrame consolidado com a análise acumulada, ou None em caso de erro.
    """
    try:
        # 1. Buscar o documento do projeto no Firestore
        doc_ref = db.collection("projetos").document(project_id)
        doc = doc_ref.get()

        if not doc.exists:
            st.error(f"Erro: Projeto com ID '{project_id}' não foi encontrado.")
            return None
        
        project_data = doc.to_dict()
        
        # 2. Extrair dados de PLANEJAMENTO e MEDIÇÃO do mesmo documento
        planejamento_data = project_data.get("table", [])
        medicao_data = project_data.get("tabela_medicao", [])
        medicao_atual = project_data.get("medicao_atual")
        medicao_atual = medicao_atual - 1

        if not planejamento_data or not medicao_data:
            st.warning("Tabela de planejamento ou medição não encontrada ou vazia no documento do projeto.")
            return pd.DataFrame()

        df_planejamento = pd.DataFrame(planejamento_data)
        df_medicao = pd.DataFrame(medicao_data)

        # 3. Logica de analise cumulativa

        col_mes_cumulativo_planejemnto = 0
        col_mes_cumulativo_medicao = 0

        for i in range(1, medicao_atual):
            col_mes_cumulativo_planejemnto = col_mes_cumulativo_planejemnto + df_planejamento[f'Mês {i}']
            col_mes_cumulativo_medicao     = col_mes_cumulativo_medicao     + df_planejamento[f'Mês {i}']

        df_planejamento_final = df_planejamento[['Item', 'Total por etapa', f'Mês {medicao_atual}']].copy()
        df_planejamento_final.rename(columns={f'Mês {medicao_atual}': 'Valor Previsto'}, inplace=True)
        df_medicao['Total por etapa'] = pd.to_numeric(df_medicao['Total por etapa'], errors='coerce').fillna(0)
        df_medicao_final      = df_medicao     [['Item', f'Mês {medicao_atual}']].copy()
        df_medicao_final.rename(columns={f'Mês {medicao_atual}': 'Valor Realizado'}, inplace=True)
        
        df_final = pd.merge(df_planejamento_final, df_medicao_final, on="Item", how="left")
        df_final.fillna(0, inplace=True)

        total_etapa = df_final['Total por etapa']
        df_final['Percentual Previsto'] = (df_final['Valor Previsto'] / total_etapa).where(total_etapa != 0, 0) * 100
        df_final['Percentual Realizado'] = (df_final['Valor Realizado'] / total_etapa).where(total_etapa != 0, 0) * 100
        df_final['Desvio Percentual'] = df_final['Percentual Realizado'] - df_final['Percentual Previsto']

        for col in ['Percentual Previsto', 'Percentual Realizado', 'Desvio Percentual']:
            df_final[col] = df_final[col].apply(lambda x: f"{x:.2f}%")
        
        tabela_2 = df_final[[
            'Item', 'Total por etapa', 
            'Valor Previsto', 'Percentual Previsto', 
            'Valor Realizado', 'Percentual Realizado', 
            'Desvio Percentual'
        ]].copy()

        return tabela_2
    

    except Exception as e:
        st.error(f"Ocorreu um erro inesperado ao gerar a tabela cumulativa: {e}")
        return None
    
def gerar_tabela_previsto_realizado_mes(db: firestore.client, project_id: str) -> pd.DataFrame:
    """
        
        
    """
    try:
        # 1. Buscar o documento único do projeto no Firestore
        doc_ref = db.collection("projetos").document(project_id)
        doc = doc_ref.get()

        if not doc.exists:
            st.error(f"Erro: Projeto com ID '{project_id}' não foi encontrado.")
            return None
        
        project_data = doc.to_dict()

        # 2. Extrai dados do projeto

    except Exception as e:
        st.error(f"Ocorreu um erro inesperado ao gerar a tabela cumulativa: {e}")
        return None


