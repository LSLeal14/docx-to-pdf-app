import pandas as pd
from firebase_admin import firestore
import streamlit as st
import re # Importando a biblioteca de expressões regulares

# A função de gerar a Tabela 1 permanece a mesma, como referência.
def gerar_tabela_percentual(db: firestore.client, project_id: str) -> pd.DataFrame:
    """
    Busca os dados de um projeto no Firestore, calcula o percentual de cada etapa
    em relação ao valor total do projeto e retorna um DataFrame formatado.
    """
    try:
        doc_ref = db.collection("projetos").document(project_id)
        doc = doc_ref.get()

        if not doc.exists:
            st.error(f"Erro: Projeto com ID '{project_id}' não foi encontrado.")
            return None

        project_data = doc.to_dict()
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
        print(f"Ocorreu um erro inesperado ao gerar a tabela para o projeto {project_id}: {e}")
        return None

def gerar_tabela_cumulativa(db: firestore.client, project_id: str) -> pd.DataFrame:
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
        # 1. Buscar o documento único do projeto no Firestore
        doc_ref = db.collection("projetos").document(project_id)
        doc = doc_ref.get()
        if not doc.exists:
            st.error(f"Erro: Projeto com ID '{project_id}' não foi encontrado.")
            return None
        
        project_data = doc.to_dict()
        
        # 2. Extrair dados de PLANEJAMENTO e MEDIÇÃO do mesmo documento
        planejamento_data = project_data.get("table", [])
        medicao_data = project_data.get("tabela_medicao", [])

        if not planejamento_data or not medicao_data:
            st.warning("Tabela de planejamento ou medição não encontrada ou vazia no documento do projeto.")
            return pd.DataFrame()

        df_planejamento = pd.DataFrame(planejamento_data)
        df_medicao = pd.DataFrame(medicao_data)

        # --- LÓGICA DE ANÁLISE CUMULATIVA ---

        # 3. Identificar o último mês com medições
        # Mapeia nomes de meses para números para poder ordená-los corretamente
        ordem_meses = {nome: i for i, nome in enumerate(['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'])}
        
        # Encontra colunas de meses na medição e as ordena cronologicamente
        colunas_meses_medicao = [col for col in df_medicao.columns if col in ordem_meses]
        colunas_meses_medicao.sort(key=lambda mes: ordem_meses[mes])
        
        ultimo_mes_com_dados = None
        for mes in reversed(colunas_meses_medicao):
            if pd.to_numeric(df_medicao[mes], errors='coerce').fillna(0).sum() > 0:
                ultimo_mes_com_dados = mes
                break

        if not ultimo_mes_com_dados:
            st.info("Nenhum dado de medição mensal encontrado para análise cumulativa.")
            return pd.DataFrame()

        # Pega a posição (índice) do último mês medido para saber até onde somar
        indice_ultimo_mes = colunas_meses_medicao.index(ultimo_mes_com_dados)
        st.success(f"Análise gerada com base nos dados acumulados até: {ultimo_mes_com_dados}")

        # 4. Calcular o "Valor Previsto" ACUMULADO
        colunas_planejamento_a_somar = colunas_meses_medicao[:indice_ultimo_mes + 1]
        for col in colunas_planejamento_a_somar:
            df_planejamento[col] = pd.to_numeric(df_planejamento[col], errors='coerce').fillna(0)
        df_planejamento['Valor Previsto'] = df_planejamento[colunas_planejamento_a_somar].sum(axis=1)

        # 5. Calcular o "Valor Realizado" ACUMULADO
        colunas_medicao_a_somar = colunas_meses_medicao[:indice_ultimo_mes + 1]
        for col in colunas_medicao_a_somar:
            df_medicao[col] = pd.to_numeric(df_medicao[col], errors='coerce').fillna(0)
        df_medicao['Valor Realizado'] = df_medicao[colunas_medicao_a_somar].sum(axis=1)

        # 6. Preparar e unir os DataFrames
        df_planejamento_final = df_planejamento[['Item', 'Descrição', 'Valor Previsto']].copy()
        df_medicao['Total por etapa'] = pd.to_numeric(df_medicao['Total por etapa'], errors='coerce').fillna(0)
        df_medicao_final = df_medicao[['Item', 'Total por etapa', 'Valor Realizado']].copy()
        
        df_final = pd.merge(df_planejamento_final, df_medicao_final, on="Item", how="left")
        df_final.fillna(0, inplace=True)

        # 7. Calcular os percentuais e o desvio com base nos valores acumulados
        total_etapa = df_final['Total por etapa']
        df_final['Percentual Previsto'] = (df_final['Valor Previsto'] / total_etapa).where(total_etapa != 0, 0) * 100
        df_final['Percentual Realizado'] = (df_final['Valor Realizado'] / total_etapa).where(total_etapa != 0, 0) * 100
        df_final['Desvio Percentual'] = df_final['Percentual Realizado'] - df_final['Percentual Previsto']

        # 8. Formatar e organizar o DataFrame para exibição
        df_final.rename(columns={'Item': 'Número do Item'}, inplace=True)
        for col in ['Percentual Previsto', 'Percentual Realizado', 'Desvio Percentual']:
            df_final[col] = df_final[col].apply(lambda x: f"{x:.2f}%")

        colunas_finais = [
            'Número do Item', 'Descrição', 'Total por etapa', 
            'Valor Previsto', 'Percentual Previsto', 
            'Valor Realizado', 'Percentual Realizado', 
            'Desvio Percentual'
        ]
        
        return df_final[colunas_finais]

    except Exception as e:
        st.error(f"Ocorreu um erro inesperado ao gerar a tabela cumulativa: {e}")
        return None

# Exemplo de uso no seu App Streamlit:
# if 'db' in st.session_state and 'project_id' in st.session_state:
#     tabela_consolidada = gerar_tabela_cumulativa(st.session_state.db, st.session_state.project_id)
#     if tabela_consolidada is not None:
#         st.dataframe(tabela_consolidada)
