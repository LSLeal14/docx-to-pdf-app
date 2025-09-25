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
    Gera uma tabela comparativa mês a mês entre o planejamento e a medição, usando a linha de totais.

    Args:
        db (firestore.client): O cliente do Firestore já inicializado.
        project_id (str): O ID do documento do projeto a ser processado.

    Returns:
        pd.DataFrame: DataFrame consolidado com a análise mês a mês, ou None em caso de erro.
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

        if not planejamento_data or not medicao_data:
            st.warning("Tabela de planejamento ou medição não encontrada ou vazia no documento do projeto.")
            return pd.DataFrame()

        df_planejamento = pd.DataFrame(planejamento_data)
        df_medicao = pd.DataFrame(medicao_data)

        total_planejamento_row = df_planejamento[df_planejamento['Item'] == 'TOTAL']
        total_medicao_row = df_medicao[df_medicao['Item'] == 'Total por Mês']


        if total_planejamento_row.empty or total_medicao_row.empty:
            st.warning("Linha de totais não encontrada nas tabelas de planejamento ou medição.")
            return pd.DataFrame()
        
        # Calcular o valor total do projeto para os percentuais
        valor_total_projeto = pd.to_numeric(total_planejamento_row['Total por etapa'], errors='coerce').sum()

        # 4. Preparar a tabela final
        tabela_final = []
        
        # 5. Iterar por cada mês e calcular os totais e percentuais
        for i in range(1, medicao_atual+1):
            mes_col = f"Mês {i}"

            # Coletar os valores do mês, tratando valores não numéricos
            total_previsto = pd.to_numeric(total_planejamento_row[mes_col], errors='coerce').fillna(0).iloc[0]
            total_realizado = pd.to_numeric(total_medicao_row[mes_col], errors='coerce').fillna(0).iloc[0]

            # Calcular os percentuais em relação ao valor total do projeto
            percentual_previsto = (total_previsto / valor_total_projeto) * 100 
            percentual_realizado = (total_realizado / valor_total_projeto) * 100

            # Calcular o desvio
            total_desvio = total_realizado - total_previsto
            percentual_desvio = percentual_realizado - percentual_previsto

            # Adicionar os dados do mês à lista
            tabela_final.append({
                'Mês': i,
                'Total Previsto': total_previsto,
                'Percentual Previsto': f"{percentual_previsto:.2f}%",
                'Total Realizado': total_realizado,
                'Percentual Realizado': f"{percentual_realizado:.2f}%",
                'Total Desvio': total_desvio,
                'Percentual Desvio': f"{percentual_desvio:.2f}%"
            })
        
        # 6. Criar o DataFrame final
        tabela_3 = pd.DataFrame(tabela_final)

        return tabela_3
    
    except Exception as e:
        st.error(f"Ocorreu um erro inesperado ao gerar a tabela mês a mês: {e}")
        return None
    
def gerar_tabela_contratual(db: firestore.client, project_id: str) -> pd.DataFrame:
    """
    Gera uma tabela com valores de contrato, realizado, saldo contratual e respectivos percentuais.
    """
    try:
        # 1. Buscar o documento do projeto no Firestore
        doc_ref = db.collection("projetos").document(project_id)
        doc = doc_ref.get()

        if not doc.exists:
            st.error(f"Erro: Projeto com ID '{project_id}' não foi encontrado.")
            return None

        project_data = doc.to_dict()

        # 2. Extrair dados das tabelas de planejamento e medição
        planejamento_data = project_data.get("table", [])
        medicao_data = project_data.get("tabela_medicao", [])

        if not planejamento_data or not medicao_data:
            st.warning("Tabela de planejamento ou medição não encontrada ou vazia no documento do projeto.")
            return pd.DataFrame()
        
        # 3. Criar DataFrames e remover as linhas de totais para trabalhar apenas com os itens
        df_planejamento = pd.DataFrame(planejamento_data)
        df_medicao = pd.DataFrame(medicao_data)
        
        df_planejamento = df_planejamento[df_planejamento['Item'] != 'TOTAL']
        df_medicao = df_medicao[df_medicao['Item'] != 'Total por Mês']

        # 4. Mesclar os DataFrames com base no 'Item'
        df_planejamento['Total por etapa'] = pd.to_numeric(df_planejamento['Total por etapa'], errors='coerce').fillna(0)
        df_medicao['Total'] = pd.to_numeric(df_medicao['Total'], errors='coerce').fillna(0)
        
        df_merged = pd.merge(df_planejamento[['Item', 'Total por etapa']],
                             df_medicao[['Item', 'Total']],
                             on='Item',
                             how='left')
        df_merged.rename(columns={'Total': 'Valor Realizado'}, inplace=True)
        df_merged.fillna(0, inplace=True)

        # 5. Fazer os cálculos solicitados
        df_merged['Saldo Contratual'] = df_merged['Total por etapa'] - df_merged['Valor Realizado']
        
        total_geral_contrato = df_merged['Total por etapa'].sum()
        total_geral_realizado = df_merged['Valor Realizado'].sum()
        
        df_merged['Percentual Realizado'] = (df_merged['Valor Realizado'] / total_geral_contrato) * 100
        df_merged['Percentual Saldo'] = (df_merged['Saldo Contratual'] / total_geral_contrato) * 100

        # 6. Formatar as colunas de percentual
        for col in ['Percentual Realizado', 'Percentual Saldo']:
            df_merged[col] = df_merged[col].apply(lambda x: f"{x:.2f}%")

        # 7. Organizar as colunas para o resultado final
        tabela_4 = df_merged[[
            'Item',
            'Total por etapa',
            'Valor Realizado',
            'Percentual Realizado',
            'Saldo Contratual',
            'Percentual Saldo'
        ]].copy()
        
        st.table(tabela_4)
        return tabela_4
    
    except Exception as e:
        st.error(f"Ocorreu um erro inesperado ao gerar a tabela contratual: {e}")
        return None
    
def gerar_tabela_contratual_item(db: firestore.client, project_id: str) -> pd.DataFrame:
    """
    Gera uma tabela com valores de contrato, realizado, saldo contratual e percentuais por item.
    """
    try:
        # 1. Buscar o documento do projeto no Firestore
        doc_ref = db.collection("projetos").document(project_id)
        doc = doc_ref.get()

        if not doc.exists:
            st.error(f"Erro: Projeto com ID '{project_id}' não foi encontrado.")
            return None

        project_data = doc.to_dict()

        # 2. Extrair dados das tabelas de planejamento e medição
        planejamento_data = project_data.get("table", [])
        medicao_data = project_data.get("tabela_medicao", [])

        if not planejamento_data or not medicao_data:
            st.warning("Tabela de planejamento ou medição não encontrada ou vazia no documento do projeto.")
            return pd.DataFrame()
        
        # 3. Criar DataFrames e remover as linhas de totais para trabalhar apenas com os itens
        df_planejamento = pd.DataFrame(planejamento_data)
        df_medicao = pd.DataFrame(medicao_data)
        
        df_planejamento = df_planejamento[df_planejamento['Item'] != 'TOTAL']
        df_medicao = df_medicao[df_medicao['Item'] != 'Total por Mês']
        df_medicao = df_medicao[df_medicao['Item'] != 'TOTAL']
        
        # 4. Mesclar os DataFrames com base no 'Item'
        df_planejamento['Total por etapa'] = pd.to_numeric(df_planejamento['Total por etapa'], errors='coerce').fillna(0)
        df_medicao['Total'] = pd.to_numeric(df_medicao['Total'], errors='coerce').fillna(0)

        df_merged = pd.merge(df_planejamento[['Item', 'Total por etapa']],
                             df_medicao[['Item', 'Total']],
                             on='Item',
                             how='left')
        df_merged.rename(columns={'Total': 'Valor Realizado'}, inplace=True)
        df_merged.fillna(0, inplace=True)

        # 5. Fazer os cálculos solicitados
        df_merged['Saldo Contratual'] = df_merged['Total por etapa'] - df_merged['Valor Realizado']
        
        # O percentual é calculado em relação ao Total por etapa do item
        df_merged['Percentual Realizado'] = df_merged.apply(
            lambda row: (row['Valor Realizado'] / row['Total por etapa']) * 100 if row['Total por etapa'] > 0 else 0,
            axis=1
        )
        df_merged['Percentual Saldo'] = df_merged.apply(
            lambda row: (row['Saldo Contratual'] / row['Total por etapa']) * 100 if row['Total por etapa'] > 0 else 0,
            axis=1
        )

        # 6. Formatar as colunas de percentual
        for col in ['Percentual Realizado', 'Percentual Saldo']:
            df_merged[col] = df_merged[col].apply(lambda x: f"{x:.2f}%")

        # 7. Organizar as colunas para o resultado final
        tabela_5 = df_merged[[
            'Item',
            'Total por etapa',
            'Valor Realizado',
            'Percentual Realizado',
            'Saldo Contratual',
            'Percentual Saldo'
        ]].copy()

        st.table(tabela_5)
        
        return tabela_5
    
    except Exception as e:
        st.error(f"Ocorreu um erro inesperado ao gerar a tabela contratual por item: {e}")
        return None


