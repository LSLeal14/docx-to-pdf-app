import streamlit as st
import os
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv
import pandas as pd

# Firebase init
@st.cache_resource
def init_firebase():
    load_dotenv()
    FIREBASE_KEY_PATH = os.getenv("FIREBASE_KEY_PATH", "app/firebase_key.json")
    if not firebase_admin._apps:
        cred = credentials.Certificate(FIREBASE_KEY_PATH)
        firebase_admin.initialize_app(cred)
    return firestore.client()

db = init_firebase()

def main():
    st.set_page_config(layout="wide")
    st.title("Atualização de Projeto")

    # Filtro de busca
    campos = {
        "N° do Contrato": "n_contrato",
        "Contratada": "contratada"
    }

    campo_escolhido = st.selectbox("Buscar projeto por:", list(campos.keys()))
    termo_busca = st.text_input("Digite o termo de busca:")

    if not termo_busca:
        st.info("Digite um termo para iniciar a busca.")
        return

    # Consulta no Firestore
    projetos_ref = db.collection("projetos").stream()
    campo_firebase = campos[campo_escolhido]

    projetos_filtrados = []
    for doc in projetos_ref:
        data = doc.to_dict()
        if termo_busca.lower() in str(data.get(campo_firebase, "")).lower():
            projetos_filtrados.append((doc.id, data))

    if not projetos_filtrados:
        st.warning("Nenhum projeto encontrado.")
        return

    # Seleciona entre os resultados encontrados
    projeto_opcoes = {f"{d.get('n_contrato', '')} - {d.get('contratada', '')}": (doc_id, d) 
                      for doc_id, d in projetos_filtrados}

    nome_projeto_selecionado = st.selectbox("Selecione o projeto:", list(projeto_opcoes.keys()))
    projeto_id, projeto = projeto_opcoes[nome_projeto_selecionado]

    # Carrega a tabela
    linhas = projeto.get("linhas", [])
    colunas = projeto.get("colunas", [])
    tabela_dict = projeto.get("tabela", {})

    df = pd.DataFrame.from_dict(tabela_dict, orient="columns")
    df = df.reindex(index=linhas, columns=colunas)
    df.index.name = "Item"

    st.markdown("## Tabela de Medições")

    # Verifica se precisa crescer colunas
    mes_atual = st.number_input("Informe o mês atual do projeto", min_value=1, value=len(colunas))

    if mes_atual > len(colunas):
        for i in range(len(colunas) + 1, mes_atual + 1):
            df[f"Mês {i}"] = ""
        colunas = list(df.columns)

    # Editor (sem adicionar linhas, sem checkbox)
    df_editado = st.data_editor(
        df,
        use_container_width=True,
        num_rows="fixed",
        hide_index=False
    )

    # Botão de salvar
    if st.button("Salvar alterações"):
        try:
            dados_atualizados = {
                **projeto,
                "colunas": list(df_editado.columns),
                "linhas": list(df_editado.index),
                "tabela": df_editado.fillna("").to_dict(orient="dict")
            }

            db.collection("projetos").document(projeto_id).set(dados_atualizados)
            st.success("Atualizações salvas com sucesso!")
        except Exception as e:
            st.error(f"Erro ao salvar: {e}")

if __name__ == "__main__":
    main()
