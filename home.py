import streamlit as st
import home
import cadastro_proj
import consultar_proj
import atualizar_proj
import gera_pdf
import atualizar_medi

def main():
    
    st.set_page_config(layout="wide")

    st.title("Início")
    st.write("Bem-vindo!")

    st.header("Passo a passo para uso da plataforma")
    st.subheader("1. Navegação")



    st.subheader("2. Cadastro de Projeto", cadastro_proj)



    st.subheader("3. Consulta e geração do relatório de medição", consultar_proj)



    st.subheader("4. Atualização de tabela de Planejamento", atualizar_proj)



    st.subheader("5. Atualização de tabela de Medição", atualizar_medi)