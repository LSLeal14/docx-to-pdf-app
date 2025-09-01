import pandas as pd
from firebase_admin import firestore
import streamlit as st
import re # Importando a biblioteca de expressões regulares

# Manteremos a função original como referência e para uso, se necessário.
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

def gerar_tabela_previsto_realizado(db: firestore.client, project_id: str) -> pd.DataFrame:
    """
    Busca dados de planejamento e medição de um projeto no Firestore,
    consolida as informações e calcula as diferenças entre previsto e realizado.

    Args:
        db (firestore.client): O cliente do Firestore já inicializado.
        project_id (str): O ID do documento do projeto a ser processado.

    Returns:
        pd.DataFrame: Um DataFrame consolidado com análises de previsto vs. realizado.
                      Retorna None se os dados não forem encontrados ou ocorrer um erro.
    """
    try:
        doc_ref = db.collection("projetos").document(project_id)
        doc = doc_ref.get()

        if not doc.exists:
            st.error(f"Erro: Projeto com ID '{project_id}' não foi encontrado.")
            return None
        
        project_data = doc.to_dict()
        planejamento_data = project_data.get("table", [])

        if not planejamento_data:
            st.warning(f"A tabela de planejamento para o projeto '{project_id}' está vazia.")
            return pd.DataFrame()
        
        df_planejamento = pd.DataFrame(planejamento_data)

        # 2. Buscar dados da tabela de MEDIÇÃO
            
        project_data = doc.to_dict()
        medicao_data = project_data.get("tabela_medicao", [])
        if not medicao_data:
            st.warning(f"A tabela de medição para o projeto '{project_id}' está vazia.")
            return pd.DataFrame()

        df_medicao = pd.DataFrame(medicao_data)

        # 3. Processar DataFrame de PLANEJAMENTO
        # Identificar colunas de meses (ex: Jan, Fev, Mar, etc.)
        colunas_meses_planejamento = [col for col in df_planejamento.columns if re.match(r'^(Jan|Fev|Mar|Abr|Mai|Jun|Jul|Ago|Set|Out|Nov|Dez)$', col, re.I)]
        
        # Converter colunas de meses para numérico e somar para obter o 'Valor Previsto'
        for col in colunas_meses_planejamento:
            df_planejamento[col] = pd.to_numeric(df_planejamento[col], errors='coerce').fillna(0)
        df_planejamento['Valor Previsto'] = df_planejamento[colunas_meses_planejamento].sum(axis=1)
        
        # Selecionar colunas de interesse do planejamento
        df_planejamento_final = df_planejamento[['Item', 'Descrição', 'Valor Previsto']].copy()

        # 4. Processar DataFrame de MEDIÇÃO
        # Garantir que as colunas de valores são numéricas
        df_medicao['Total por etapa'] = pd.to_numeric(df_medicao['Total por etapa'], errors='coerce').fillna(0)
        df_medicao['Total Realizado'] = pd.to_numeric(df_medicao['Total Realizado'], errors='coerce').fillna(0)
        
        # Selecionar colunas de interesse da medição
        df_medicao_final = df_medicao[['Item', 'Total por etapa', 'Total Realizado']].copy()

        # 5. Unir as duas tabelas usando a coluna 'Item' como chave
        df_final = pd.merge(df_planejamento_final, df_medicao_final, on="Item", how="left")
        # Preencher com 0 caso um item planejado ainda não tenha medição
        df_final.fillna(0, inplace=True)

        # 6. Calcular os percentuais e o desvio
        # Evitar divisão por zero
        total_etapa = df_final['Total por etapa']
        
        # Cálculo do Percentual Previsto
        df_final['Percentual Previsto'] = (df_final['Valor Previsto'] / total_etapa).where(total_etapa != 0, 0) * 100
        
        # Cálculo do Percentual Realizado
        df_final['Percentual Realizado'] = (df_final['Total Realizado'] / total_etapa).where(total_etapa != 0, 0) * 100
        
        # Cálculo do Desvio
        df_final['Desvio Percentual'] = df_final['Percentual Realizado'] - df_final['Percentual Previsto']

        # 7. Formatar e organizar o DataFrame final
        df_final.rename(columns={
            'Item': 'Número do Item',
            'Total Realizado': 'Valor Realizado'
        }, inplace=True)
        
        # Formatação das colunas de percentual para exibição
        df_final['Percentual Previsto'] = df_final['Percentual Previsto'].apply(lambda x: f"{x:.2f}%")
        df_final['Percentual Realizado'] = df_final['Percentual Realizado'].apply(lambda x: f"{x:.2f}%")
        df_final['Desvio Percentual'] = df_final['Desvio Percentual'].apply(lambda x: f"{x:.2f}%")

        # Selecionar e reordenar as colunas para a tabela final
        colunas_finais = [
            'Número do Item', 'Descrição', 'Total por etapa', 
            'Valor Previsto', 'Percentual Previsto', 
            'Valor Realizado', 'Percentual Realizado', 
            'Desvio Percentual'
        ]
        
        return df_final[colunas_finais]

    except Exception as e:
        st.error(f"Ocorreu um erro inesperado ao gerar a tabela consolidada para o projeto {project_id}: {e}")
        return None

# Exemplo de como você poderia chamar a função em seu app Streamlit
# (requer que o Firebase já esteja inicializado e o 'db' e 'project_id' estejam disponíveis)
#
# if 'db' in st.session_state and 'project_id' in st.session_state:
#     tabela_consolidada = gerar_tabela_previsto_realizado(st.session_state.db, st.session_state.project_id)
#     if tabela_consolidada is not None:
#         st.dataframe(tabela_consolidada)
