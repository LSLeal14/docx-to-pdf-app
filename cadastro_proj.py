import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import os
from dotenv import load_dotenv
import datetime
import pandas as pd

# Funções e constantes podem ficar fora do main()
data_atual = datetime.datetime.now()
ano_seguinte = data_atual.year + 1
jan_1 = datetime.date(2000, 1, 1)
dez_31 = datetime.date(2100, 12, 31)

def main():

    st.set_page_config(layout="wide")
    st.title("Cadastro de Projeto com Tabela Interativa")

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

    with st.form("formulario_projeto"):
        st.header("1. Informações Gerais do Projeto")
        
        col1, col2 = st.columns(2)
        with col1:
            n_contrato = st.text_input("Contrato n°:")
            n_os = st.text_input("N° da OS/OFB/NE:")
            contratante = st.text_input("Contratante:")
            prazo_meses = st.number_input("Prazo do projeto (em meses)", min_value=1, value=12, step=1)

        with col2:
            periodo_vigencia = st.date_input(
                "Período de Vigência:",
                (data_atual, datetime.date(ano_seguinte, data_atual.month, data_atual.day)),
                min_value=jan_1,
                max_value=dez_31,
                format="DD.MM.YYYY"
            )
            valor_bens_receb = st.text_input("Valor dos Bens/Serviços Recebidos:", placeholder="R$ 12.345,67")
            contratada = st.text_input("Contratada:")
        
        objeto = st.text_area("Objeto do Contrato:")

        st.header("2. Tabela de Medições e Cronograma")
        st.info("Preencha os itens e valores diretamente na tabela abaixo.")

        # <<< MELHORIA: Criação da tabela para edição interativa >>>
        # Monta colunas Mês 1 a Mês N
        colunas_meses = [f"Mês {i+1}" for i in range(prazo_meses)]
        
        # Cria um DataFrame inicial para o editor. O usuário pode adicionar mais linhas.
        df_inicial = pd.DataFrame(
            [{'Item': 'Exemplo: Alvenaria', **{col: "" for col in colunas_meses}}]
        )
        
        # O data_editor permite ao usuário editar a tabela
        edited_df = st.data_editor(
            df_inicial,
            num_rows="dynamic", # Permite adicionar/remover linhas
            use_container_width=True,
            height=250
        )

        enviar = st.form_submit_button("✔️ Salvar Projeto e Tabela")

    if enviar:
        if edited_df.empty or 'Item' not in edited_df.columns or edited_df['Item'].isnull().all():
            st.error("A tabela está vazia ou a coluna 'Item' não foi preenchida. Adicione pelo menos uma linha.")
        else:
            # <<< MUDANÇA CRÍTICA: Convertendo o DataFrame para o formato correto >>>
            # O `st.data_editor` já cria um DataFrame com a coluna 'Item', não precisamos de reset_index.
            # Apenas convertemos para o formato "Array de Mapas" (lista de dicionários)
            tabela_para_salvar = edited_df.fillna("").to_dict(orient='records')
            
            # Converte as datas para um formato que o Firebase entende bem (Timestamp)
            # Isso é mais flexível para consultas futuras do que salvar como string.
            vigencia_inicio = datetime.datetime.combine(periodo_vigencia[0], datetime.time.min)
            vigencia_fim = datetime.datetime.combine(periodo_vigencia[1], datetime.time.max)

            # Dados para salvar no Firestore
            dados = {
                "n_contrato": n_contrato,
                "periodo_vigencia": [vigencia_inicio, vigencia_fim], # Salva como Timestamp
                "n_os": n_os,
                "objeto": objeto,
                "valor_bens_receb": valor_bens_receb,
                "contratante": contratante,
                "contratada": contratada,
                "prazo_meses": prazo_meses,
                # <<< O campo 'tabela' agora tem o nome que seu outro script espera
                # e o formato correto!
                "table": tabela_para_salvar 
            }

            try:
                # Adiciona os dados e obtém a referência do novo documento
                doc_ref = db.collection("projetos").add(dados)
                st.success(f"Projeto e tabela salvos com sucesso! ID do Projeto: `{doc_ref[1].id}`")
                st.write("Dados salvos no formato correto:")
                st.json(tabela_para_salvar) # Mostra o JSON para confirmação
            except Exception as e:
                st.error(f"Erro ao salvar no Firebase: {e}")