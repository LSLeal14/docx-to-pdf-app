import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import os
from dotenv import load_dotenv


def main():

    st.set_page_config(layout="wide")

    st.title("Cadastro de Projeto")

    load_dotenv()

    FIREBASE_KEY_PATH = os.getenv("FIREBASE_KEY_PATH", "app/firebase_key.json")

    # Inicializar Firebase (executa só uma vez)
    if not firebase_admin._apps:
        cred = credentials.Certificate(FIREBASE_KEY_PATH)
        firebase_admin.initialize_app(cred)

    db = firestore.client()

    with st.form("formulario"):
        n_contrato       = st.text_input("Contrato n°:")
        periodo_vigencia = st.text_input("Período da Vigência:")
        n_os             = st.text_input("N° da OS/OFB/NE:")
        objeto           = st.text_input("Objeto:")
        valor_bens_receb = st.text_input("Valor dos Bens/Serviços Recebidos:")
        contratante      = st.text_input("Contratante:")
        contratada       = st.text_input("Contratada:")
        
        enviar = st.form_submit_button("Enviar")

    if enviar:
        dados = {
            "n_contrato": n_contrato,
            "periodo_vigencia": periodo_vigencia,
            "n_os": n_os,
            "objeto": objeto,
            "valor_bens_receb": valor_bens_receb,
            "contratante": contratante,
            "contratada": contratada
        }
        db.collection("projeto").add(dados)
        st.success("Dados salvos!")
