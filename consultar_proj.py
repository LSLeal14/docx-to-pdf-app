import streamlit as st
import os
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd

def main():

    st.set_page_config(layout="wide")

    st.title("Consulta de Projetos")

    st.write("Consulte os dados do projeto aqui...")

    FIREBASE_KEY_PATH = os.getenv("FIREBASE_KEY_PATH", "app/firebase_key.json")

    # Inicializar Firebase (executa só uma vez)
    if not firebase_admin._apps:
        cred = credentials.Certificate(FIREBASE_KEY_PATH)
        firebase_admin.initialize_app(cred)

    db = firestore.client()

    # Campos disponíveis para busca
    campos = {
        "N° do Contrato": "n_contrato",
        "Período de Vigência": "periodo_vigencia",
        "N° da OS/OFB/NE": "n_os",
        "Objeto": "objeto",
        "Valor dos Bens/Serviços Recebidos": "valor_bens_receb",
        "Contratante": "contratante",
        "Contratada": "contratada"
    }

    # Interface de filtro
    campo_escolhido = st.selectbox("Selecione o campo para buscar:", list(campos.keys()))
    termo_busca = st.text_input("Digite o termo para busca:")

    # Consulta no Firebase (coleção 'projetos')
    projetos_ref = db.collection("projetos")
    docs = projetos_ref.stream()

    st.subheader("Projetos encontrados:")

    campo_firebase = campos[campo_escolhido]
    resultados = []

    for doc in docs:
        data = doc.to_dict()
        doc_id = doc.id
        valor_campo = str(data.get(campo_firebase, "")).lower()
        if termo_busca.lower() in valor_campo:
            resultados.append((doc_id, data))

    if resultados:
        for doc_id, data in resultados:
            dados = {
                "Item": list(campos.keys()),
                "Info": [data.get(campos[campo], "") for campo in campos]
            }
            df_info = pd.DataFrame(dados)
            st.dataframe(df_info, use_container_width=True)

            # Botão para expandir a tabela
            with st.expander(f"Expandir andamento do projeto"):
                try:
                    linhas = data.get("linhas", [])
                    colunas = data.get("colunas", [])
                    tabela_dict = data.get("tabela", {})

                    df_tabela = pd.DataFrame.from_dict(tabela_dict, orient="columns")
                    df_tabela = df_tabela.reindex(columns=colunas)
                    df_tabela.index.name = "Item"

                    st.dataframe(df_tabela, use_container_width=True)
                except Exception as e:
                    st.error(f"Erro ao carregar tabela: {e}")
    else:
        st.info("Nenhum projeto encontrado com o critério informado.")

if __name__ == "__main__":
    main()
