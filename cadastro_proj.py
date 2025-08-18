import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import os
from dotenv import load_dotenv
import datetime
import pandas as pd

data_atual = datetime.datetime.now()
ano_seguinte = data_atual.year + 1
jan_1 = datetime.date(2000, 1, 1)
dez_31 = datetime.date(2100, 12, 31)

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

    with st.form("formulario_projeto"):
        # Dados do projeto
        n_contrato       = st.text_input("Contrato n°:")
        periodo_vigencia = st.date_input(
            "Período de Vigência:",
            (data_atual, datetime.date(ano_seguinte, 1, 1)),
            jan_1,
            dez_31,
            format="DD.MM.YYYY"
        )
        n_os             = st.text_input("N° da OS/OFB/NE:")
        objeto           = st.text_input("Objeto:")
        valor_bens_receb = st.text_input(
            "Valor dos Bens/Serviços Recebidos:",
            placeholder="R$ 12.345,67 (exemplo)"
        )
        contratante      = st.text_input("Contratante:")
        contratada       = st.text_input("Contratada:")

        # Tabela de medições
        num_linhas = st.number_input("Quantas linhas (itens) a tabela terá?", min_value=1, step=1)
        prazo_meses = st.number_input("Prazo inicial do projeto (em meses)", min_value=1, step=1)

        st.markdown("### Tabela de Atulizações")
        nomes_linhas = [st.text_input(f"Nome da linha {i+1}", key=f"linha_{i}") for i in range(num_linhas)]

        enviar = st.form_submit_button("Salvar projeto e tabela")

    if enviar:
        # Monta colunas Mês 1 a Mês N
        colunas = [f"Mês {i+1}" for i in range(prazo_meses)]
        df = pd.DataFrame(index=nomes_linhas, columns=colunas)
        df.index.name = "Item"

        # Dados para salvar no Firestore
        dados = {
            "n_contrato": n_contrato,
            "periodo_vigencia": [str(periodo_vigencia[0]), str(periodo_vigencia[1])],
            "n_os": n_os,
            "objeto": objeto,
            "valor_bens_receb": valor_bens_receb,
            "contratante": contratante,
            "contratada": contratada,
            "prazo_meses": prazo_meses,
            "linhas": nomes_linhas,
            "colunas": colunas,
            "table": df.fillna("").to_dict()
        }

        try:
            db.collection("projetos").add(dados)
            st.success("Projeto e tabela salvos com sucesso!")
            st.dataframe(df, use_container_width=True)
        except Exception as e:
            st.error(f"Erro ao salvar no Firebase: {e}")