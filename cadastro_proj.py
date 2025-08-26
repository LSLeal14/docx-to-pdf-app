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
            use_container_width=True,
            height=250,
            hide_index=True,
            column_order=colunas_tabela
        )

        enviar = st.form_submit_button("✔️ Salvar Projeto e Tabela")

    if enviar:
        # --- ALTERAÇÃO PRINCIPAL: Verificação de unicidade do contrato ---
        # 1. Valida se o campo de contrato não está vazio
        if not n_contrato.strip():
            st.error("O campo 'Contrato n°' é obrigatório. Por favor, preencha-o.")
            st.stop() # Para a execução

        # 2. Verifica se o contrato já existe no banco de dados
        try:
            projetos_ref = db.collection("projetos")
            # Cria uma query para buscar documentos com o mesmo número de contrato
            query = projetos_ref.where("n_contrato", "==", n_contrato.strip()).limit(1).stream()
            
            # Se a query retornar qualquer resultado, o contrato já existe
            if any(query):
                st.error(f"Erro: Já existe um projeto cadastrado com o Contrato n° '{n_contrato}'.")
                st.stop() # Para a execução
        except Exception as e:
            st.error(f"Ocorreu um erro ao verificar a existência do contrato: {e}")
            st.stop()
        # --- FIM DA ALTERAÇÃO ---

        if edited_df.empty or edited_df['Item'].isnull().all():
            st.error("A tabela está vazia ou a coluna 'Item' não foi preenchida. Adicione pelo menos uma linha.")
        else:
            df_calculado = edited_df.copy()
            colunas_meses_existentes = [col for col in colunas_meses if col in df_calculado.columns]
            
            for col in colunas_meses_existentes:
                df_calculado[col] = pd.to_numeric(df_calculado[col], errors='coerce').fillna(0)
            
            df_calculado['Total por etapa'] = df_calculado[colunas_meses_existentes].sum(axis=1)
            
            tabela_para_salvar = df_calculado.fillna("").to_dict(orient='records')

            dados = {
                "n_contrato": n_contrato.strip(),
                "periodo_vigencia": [str(periodo_vigencia[0]), str(periodo_vigencia[1])],
                "n_os": n_os,
                "objeto": objeto,
                "valor_bens_receb": valor_bens_receb,
                "contratante": contratante,
                "contratada": contratada,
                "prazo_meses": prazo_meses,
                "table": tabela_para_salvar 
            }

            try:
                # Se o código chegou até aqui, o contrato é único e pode ser salvo.
                doc_ref = db.collection("projetos").add(dados)
                st.success(f"Projeto e tabela salvos com sucesso! ID do Projeto: `{doc_ref[1].id}`")
                st.write("Tabela final salva (com totais calculados):")
                st.dataframe(df_calculado)
            except Exception as e:
                st.error(f"Erro ao salvar no Firebase: {e}")

if __name__ == "__main__":
    main()
