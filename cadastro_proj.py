import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import os
from dotenv import load_dotenv
import datetime
import pandas as pd

# Funções e constantes
data_atual = datetime.datetime.now()
ano_seguinte = data_atual.year + 1
jan_1 = datetime.date(2000, 1, 1)
dez_31 = datetime.date(2100, 12, 31)

def main():
    st.set_page_config(layout="wide")
    st.title("Cadastro de Projeto")

    load_dotenv()

    # --- Inicialização do Firebase ---
    try:
        if not firebase_admin._apps:
            FIREBASE_KEY_PATH = os.getenv("FIREBASE_KEY_PATH", "app/firebase_key.json")
            if not os.path.exists(FIREBASE_KEY_PATH):
                st.error(f"Arquivo de chave do Firebase não encontrado em: {FIREBASE_KEY_PATH}")
                st.stop()
            cred = credentials.Certificate(FIREBASE_KEY_PATH)
            firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Erro ao inicializar o Firebase: {e}")
        st.stop()

    db = firestore.client()

    st.header("1. Defina o Prazo do Projeto")
    
    prazo_meses = st.number_input(
        "Prazo do projeto (em meses)", 
        min_value=1, 
        value=12, 
        step=1,
        help="Altere este valor para ajustar o número de colunas na tabela abaixo."
    )

    with st.form("formulario_projeto"):
        st.header("2. Informações Gerais do Projeto")
        
        col1, col2 = st.columns(2)
        with col1:
            n_contrato = st.text_input("Contrato n°:")
            n_os = st.text_input("N° da OS/OFB/NE:")
            contratante = st.text_input("Contratante:")
        with col2:
            periodo_vigencia = st.date_input(
                "Período de Vigência:",
                (data_atual, datetime.date(ano_seguinte, data_atual.month, data_atual.day)),
                min_value=jan_1, max_value=dez_31, format="DD.MM.YYYY"
            )
            valor_bens_receb = st.text_input("Valor dos Bens/Serviços Recebidos:", placeholder="R$ 12.345,67")
            contratada = st.text_input("Contratada:")
        
        objeto = st.text_area("Objeto do Contrato:")

        st.header("3. Tabela de Planejamento")
        st.info("Preencha os itens e os valores mensais. A coluna 'Total por etapa' será calculada automaticamente ao salvar.")

        colunas_meses = [f"Mês {i+1}" for i in range(prazo_meses)]
        colunas_tabela = ['Item', 'Total por etapa'] + colunas_meses
        df_inicial = pd.DataFrame(columns=colunas_tabela)
        
        edited_df = st.data_editor(
            df_inicial,
            num_rows="dynamic",
            width='stretch',
            height=250,
            hide_index=True,
            column_order=colunas_tabela
        )

        enviar = st.form_submit_button("✔️ Salvar Projeto e Tabela")

    if enviar:
        # Verificação de unicidade do contrato
        if not n_contrato.strip():
            st.error("O campo 'Contrato n°' é obrigatório. Por favor, preencha-o.")
            st.stop()

        try:
            projetos_ref = db.collection("projetos")
            query = projetos_ref.where("n_contrato", "==", n_contrato.strip()).limit(1).stream()
            if any(query):
                st.error(f"Erro: Já existe um projeto cadastrado com o Contrato n° '{n_contrato}'.")
                st.stop()
        except Exception as e:
            st.error(f"Ocorreu um erro ao verificar a existência do contrato: {e}")
            st.stop()

        if edited_df.empty or edited_df['Item'].isnull().all():
            st.error("A tabela está vazia ou a coluna 'Item' não foi preenchida. Adicione pelo menos uma linha.")
        else:
            # --- CÁLCULO DA TABELA DE PLANEJAMENTO ---
            df_calculado = edited_df.copy()
            colunas_meses_existentes = [col for col in colunas_meses if col in df_calculado.columns]
            
            for col in colunas_meses_existentes:
                df_calculado[col] = pd.to_numeric(df_calculado[col], errors='coerce').fillna(0)
            
            df_calculado['Total por etapa'] = df_calculado[colunas_meses_existentes].sum(axis=1)

            if not df_calculado.empty:
                total_planejamento = pd.DataFrame(df_calculado[colunas_meses_existentes + ['Total por etapa']].sum()).T
                total_planejamento['Item'] = 'TOTAL'
                df_calculado = pd.concat([df_calculado, total_planejamento], ignore_index=True)
            
            tabela_planejamento_salvar = df_calculado.fillna("").to_dict(orient='records')

            # 1. Copia a estrutura base da tabela de planejamento
            df_medicao = edited_df[['Item']].copy() # Copia apenas os itens originais
            df_medicao['Total por etapa'] = df_calculado['Total por etapa'].iloc[:len(edited_df)] # Pega os totais calculados, sem a linha de total

            # 2. Adiciona as colunas de meses, mas vazias, pois serão preenchidas no futuro
            for col in colunas_meses_existentes:
                df_medicao[col] = 0

            # 3. Adiciona a coluna 'Total' inicializada com 0
            df_medicao['Total'] = 0.0

            # 4. Adiciona a coluna 'Percentual do total da etapa' inicializada com '0.00%'
            df_medicao['Percentual do total da etapa'] = '0.00%'

            # 5. Garante a ordem correta das colunas
            colunas_medicao_ordenadas = ['Item', 'Total por etapa'] + colunas_meses_existentes + ['Total', 'Percentual do total da etapa']
            df_medicao = df_medicao[colunas_medicao_ordenadas]

            if not df_medicao.empty:
                total_medicao = pd.DataFrame(df_medicao[['Total por etapa', 'Total']].sum()).T
                total_medicao['Item'] = 'TOTAL'
                # Preenche as outras colunas da linha de total com valores padrão
                for col in colunas_meses_existentes:
                    total_medicao[col] = 0.0
                total_medicao['Percentual do total da etapa'] = ''
                # Garante a ordem das colunas e concatena
                total_medicao = total_medicao[colunas_medicao_ordenadas]
                df_medicao = pd.concat([df_medicao, total_medicao], ignore_index=True)
            
            # 6. Converte a tabela de medição para o formato de salvamento
            tabela_medicao_salvar = df_medicao.fillna("").to_dict(orient='records')
            
            # --- FIM DA ALTERAÇÃO ---

            dados = {
                "n_contrato": n_contrato.strip(),
                "periodo_vigencia": [str(periodo_vigencia[0]), str(periodo_vigencia[1])],
                "n_os": n_os,
                "objeto": objeto,
                "valor_bens_receb": valor_bens_receb,
                "contratante": contratante,
                "contratada": contratada,
                "prazo_meses": prazo_meses,
                "table": tabela_planejamento_salvar, # Tabela de Planejamento
                "tabela_medicao": tabela_medicao_salvar, # Nova Tabela de Medição
                "medicao_atual": 1
            }

            try:
                doc_ref = db.collection("projetos").add(dados)
                st.success(f"Projeto e tabelas salvos com sucesso! ID do Projeto: `{doc_ref[1].id}`")
                st.write("Tabela de Planejamento salva:")
                st.dataframe(df_calculado)
                st.write("Tabela de Medição inicial criada:")
                st.dataframe(df_medicao)
            except Exception as e:
                st.error(f"Erro ao salvar no Firebase: {e}")

if __name__ == "__main__":
    main()
