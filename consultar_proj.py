import streamlit as st
import os
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd

def main():

    st.set_page_config(layout="wide")
    
    st.title("Consulta de Projeto")
    st.write("Consulte os dados do projeto aqui...")

    FIREBASE_KEY_PATH = os.getenv("FIREBASE_KEY_PATH", "app/firebase_key.json")

    # Inicializar Firebase (executa só uma vez)
    if not firebase_admin._apps:
        cred = credentials.Certificate(FIREBASE_KEY_PATH)
        firebase_admin.initialize_app(cred)

    db = firestore.client()

    # Consultar dados da coleção 'projetos'
    projetos_ref = db.collection('projeto')
    docs = projetos_ref.stream()

    st.subheader("Projetos cadastrados:")
    for doc in docs:
        data = doc.to_dict()
        dados = {
            "Item": [
                "Contrato n°:",
                "Período de Vigência:",
                "N° da OS/OFB/NE:",
                "Objeto:",
                "Valor dos Bens/Serviços Recebidos",
                "Contratente",
                "Contratada"
            ],
            "Info": [
                data.get('n_contrato'),
                data.get('periodo_vigencia'),
                data.get('n_os'),
                data.get('objeto'),
                data.get('valor_bens_receb'),
                data.get('contratante'),
                data.get('contratada')
            ]
        }

        df = pd.DataFrame(dados)
        st.dataframe(df)