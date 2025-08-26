import streamlit as st
import os
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv
import pandas as pd

# Inicialização do Firebase (usando cache para evitar reconexões)
@st.cache_resource
def init_firebase():
    """Inicializa a conexão com o Firebase de forma segura."""
    load_dotenv()
    try:
        FIREBASE_KEY_PATH = os.getenv("FIREBASE_KEY_PATH", "app/firebase_key.json")
        if not os.path.exists(FIREBASE_KEY_PATH):
            st.error(f"Arquivo de chave do Firebase não encontrado em: {FIREBASE_KEY_PATH}")
            st.stop()
        
        if not firebase_admin._apps:
            cred = credentials.Certificate(FIREBASE_KEY_PATH)
            firebase_admin.initialize_app(cred)
            
    except Exception as e:
        st.error(f"Erro ao inicializar o Firebase: {e}")
        st.stop()
        
    return firestore.client()

db = init_firebase()

def main():
    st.set_page_config(layout="wide")
    st.title("Atualização da Medição do Projeto")

    # --- Seção de Busca de Projeto ---
    st.header("1. Encontre o Projeto")
    campos_busca = {
        "N° do Contrato": "n_contrato",
        "Contratada": "contratada"
    }
    campo_escolhido = st.selectbox("Buscar projeto por:", list(campos_busca.keys()))
    termo_busca = st.text_input("Digite o termo de busca:")

    if not termo_busca:
        st.info("Digite um termo para iniciar a busca de projetos.")
        st.stop()

    # Consulta no Firestore
    projetos_ref = db.collection("projetos").stream()
    campo_firebase = campos_busca[campo_escolhido]

    projetos_filtrados = []
    for doc in projetos_ref:
        data = doc.to_dict()
        if termo_busca.lower() in str(data.get(campo_firebase, "")).lower():
            projetos_filtrados.append((doc.id, data))

    if not projetos_filtrados:
        st.warning("Nenhum projeto encontrado com os critérios de busca.")
        st.stop()

    # --- Seção de Seleção e Edição ---
    projeto_opcoes = {f"{d.get('n_contrato', 'Sem Contrato')} - {d.get('objeto', 'Sem Objeto')}": (doc_id, d) 
                      for doc_id, d in projetos_filtrados}
    
    nome_projeto_selecionado = st.selectbox("Selecione o projeto para editar:", list(projeto_opcoes.keys()))
    
    if not nome_projeto_selecionado:
        st.stop()

    projeto_id, projeto_data = projeto_opcoes[nome_projeto_selecionado]

    st.header("2. Edite a Tabela de Medição")
    st.info("Preencha os valores medidos para cada mês. O Total e o Percentual serão calculados automaticamente.")

    # Carrega a tabela de medição do projeto
    tabela_medicao_dados = projeto_data.get("tabela_medicao", [])
    if not tabela_medicao_dados:
        st.error("Este projeto não possui uma tabela de medição para editar.")
        st.stop()

    df = pd.DataFrame(tabela_medicao_dados)

    # --- ALTERAÇÃO: GARANTE A ORDEM CORRETA DAS COLUNAS ---
    try:
        # 1. Define a ordem ideal das colunas com base nos dados do projeto
        prazo_meses = int(projeto_data.get("prazo_meses", 12)) # Pega o prazo ou assume 12
        colunas_meses = [f"Mês {i+1}" for i in range(prazo_meses)]
        ordem_ideal = ['Item', 'Total por etapa'] + colunas_meses + ['Total', 'Percentual do total da etapa']

        # 2. Filtra a ordem ideal para incluir apenas colunas que realmente existem no DataFrame
        colunas_existentes_ordenadas = [col for col in ordem_ideal if col in df.columns]

        # 3. Reordena o DataFrame para garantir a consistência da visualização
        df = df[colunas_existentes_ordenadas]
    except Exception as e:
        st.warning(f"Não foi possível reordenar as colunas. Exibindo na ordem padrão. Erro: {e}")
    # --- FIM DA ALTERAÇÃO ---

    # Exibe o editor da tabela
    df_editado = st.data_editor(
        df,
        use_container_width=True,
        hide_index=True,
        # Desabilita a edição de colunas calculadas para evitar erros
        disabled=['Item', 'Total por etapa', 'Total', 'Percentual do total da etapa']
    )

    # --- Seção de Salvamento com Recálculo ---
    if st.button("✔️ Salvar Alterações na Medição"):
        with st.spinner("Calculando e salvando..."):
            try:
                # Identifica as colunas de meses
                colunas_meses = [col for col in df_editado.columns if col.startswith('Mês ')]

                # Converte os valores dos meses para numérico, tratando erros
                for col in colunas_meses:
                    df_editado[col] = pd.to_numeric(df_editado[col], errors='coerce').fillna(0)
                
                # Garante que as colunas de total sejam numéricas
                df_editado['Total por etapa'] = pd.to_numeric(df_editado['Total por etapa'], errors='coerce').fillna(0)

                # Recalcula a coluna 'Total'
                df_editado['Total'] = df_editado[colunas_meses].sum(axis=1)

                # Recalcula a coluna 'Percentual do total da etapa'
                # Evita divisão por zero
                df_editado['Percentual do total da etapa'] = df_editado.apply(
                    lambda row: f"{(row['Total'] / row['Total por etapa'] * 100):.2f}%" if row['Total por etapa'] > 0 else "0.00%",
                    axis=1
                )

                # Converte o DataFrame atualizado para o formato de salvamento
                tabela_medicao_atualizada = df_editado.fillna("").to_dict(orient='records')
                
                # Atualiza apenas o campo 'tabela_medicao' no documento do Firestore
                db.collection("projetos").document(projeto_id).update({
                    "tabela_medicao": tabela_medicao_atualizada
                })
                
                st.success("Tabela de medição atualizada com sucesso!")
                st.write("Dados atualizados:")
                st.dataframe(df_editado)

            except Exception as e:
                st.error(f"Ocorreu um erro ao salvar as alterações: {e}")

if __name__ == "__main__":
    main()
