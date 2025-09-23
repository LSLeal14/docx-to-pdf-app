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
    
    # Carrega a tabela de medição e o prazo original
    tabela_medicao_dados = projeto_data.get("tabela_medicao", [])
    prazo_meses_original = int(projeto_data.get("prazo_meses", 12))
    medicao_atual = int(projeto_data.get("medicao_atual", 1))
    
    if not tabela_medicao_dados:
        st.error("Este projeto não possui uma tabela de medição para editar.")
        st.stop()

    df = pd.DataFrame(tabela_medicao_dados)
    # Remove a linha de total antes de editar para não ser alterada pelo usuário
    df = df[df['Item'] != 'Total por Mês']
    df = df[df['Item'] != 'TOTAL']


    # --- ALTERAÇÃO 1: CAMPO PARA INFORMAR MÊS ATUAL E LIDAR COM ATRASOS ---
    mes_medicao_atual = st.number_input(
        "Informe o mês da medição a ser atualizada:",
        min_value=1,
        value=medicao_atual, 
        step=1,
        help="Se o mês informado for maior que o prazo atual, a tabela será expandida."
    )

    # Verifica se o projeto está atrasado e adiciona novas colunas se necessário
    if mes_medicao_atual > prazo_meses_original:
        atraso_meses = mes_medicao_atual - prazo_meses_original
        st.warning(f"Atenção: Projeto atrasado em {atraso_meses} {'mês' if atraso_meses == 1 else 'meses'}. A tabela foi expandida.")
        
        # Adiciona as colunas dos meses extras ao DataFrame
        for i in range(prazo_meses_original + 1, mes_medicao_atual + 1):
            if f"Mês {i}" not in df.columns:
                df[f"Mês {i}"] = "" # Inicializa a nova coluna vazia

    # --- Garante a ordem correta das colunas, considerando os possíveis novos meses ---
    try:
        prazo_a_considerar = max(prazo_meses_original, mes_medicao_atual)
        colunas_meses = [f"Mês {i+1}" for i in range(prazo_a_considerar)]
        ordem_ideal = ['Item', 'Total por etapa'] + colunas_meses + ['Total', 'Percentual do total da etapa']
        
        colunas_existentes_ordenadas = [col for col in ordem_ideal if col in df.columns]
        df = df[colunas_existentes_ordenadas]
    except Exception as e:
        st.warning(f"Não foi possível reordenar as colunas. Exibindo na ordem padrão. Erro: {e}")

    st.info("Preencha os valores medidos para cada mês. O Total e o Percentual serão calculados automaticamente ao salvar.")
    
    # Exibe o editor da tabela (agora com as possíveis novas colunas)
    df_editado = st.data_editor(
        df,
        width=True,
        hide_index=True,
        disabled=['Item', 'Total por etapa', 'Total', 'Percentual do total da etapa']
    )

    # --- Seção de Salvamento com Recálculo ---
    if st.button("✔️ Salvar Alterações na Medição"):
        with st.spinner("Calculando e salvando..."):
            try:
                # Faz uma cópia para evitar alterar o dataframe em exibição diretamente
                df_para_salvar = df_editado.copy()
                
                # --- RECALCULA TOTAIS DAS LINHAS ---
                colunas_meses = [col for col in df_para_salvar.columns if col.startswith('Mês ')]
                for col in colunas_meses:
                    df_para_salvar[col] = pd.to_numeric(df_para_salvar[col], errors='coerce').fillna(0)
                
                df_para_salvar['Total por etapa'] = pd.to_numeric(df_para_salvar['Total por etapa'], errors='coerce').fillna(0)
                df_para_salvar['Total'] = df_para_salvar[colunas_meses].sum(axis=1)
                df_para_salvar['Percentual do total da etapa'] = df_para_salvar.apply(
                    lambda row: f"{(row['Total'] / row['Total por etapa'] * 100):.2f}%" if row['Total por etapa'] > 0 else "0.00%",
                    axis=1
                )

                # --- NOVO: ADICIONA A LINHA DE TOTAIS POR MÊS ---
                somas_colunas = df_para_salvar[colunas_meses + ['Total por etapa', 'Total']].sum()
                linha_total = pd.DataFrame([somas_colunas], columns=somas_colunas.index)
                linha_total['Item'] = 'Total por Mês'
                
                # Calcula o percentual geral
                total_geral_etapa = linha_total['Total por etapa'].iloc[0]
                total_geral_medido = linha_total['Total'].iloc[0]
                if total_geral_etapa > 0:
                    percentual_geral = (total_geral_medido / total_geral_etapa * 100)
                    linha_total['Percentual do total da etapa'] = f"{percentual_geral:.2f}%"
                else:
                    linha_total['Percentual do total da etapa'] = "0.00%"
                
                # Concatena a linha de totais ao final do DataFrame
                df_final = pd.concat([df_para_salvar, linha_total], ignore_index=True)
                
                # --- FIM DO NOVO CÓDIGO ---

                tabela_medicao_atualizada = df_final.fillna("").to_dict(orient='records')
                
                # ATUALIZA O PRAZO E O MÊS ATUAL DO PROJETO SE NECESSÁRIO
                dados_para_atualizar = {
                    "tabela_medicao": tabela_medicao_atualizada,
                    "medicao_atual": int(mes_medicao_atual)
                }
                if mes_medicao_atual > prazo_meses_original:
                    dados_para_atualizar["prazo_meses"] = mes_medicao_atual
                
                db.collection("projetos").document(projeto_id).update(dados_para_atualizar)
                
                st.success("Tabela de medição atualizada com sucesso!")
                st.write("Dados atualizados (com totais por mês):")
                st.dataframe(df_final)

            except Exception as e:
                st.error(f"Ocorreu um erro ao salvar as alterações: {e}")

if __name__ == "__main__":
    main()
