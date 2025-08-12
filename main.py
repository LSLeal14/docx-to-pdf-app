import streamlit as st
import home
import cadastro_proj
import consultar_proj
import atualizar_proj
import gera_pdf

st.set_page_config(layout="wide")

# Inicializa o estado
if "page" not in st.session_state:
    st.session_state.page = "home"

# Barra lateral com botões
with st.sidebar:
    st.image("img/logo_ebserh.png", width=200)
    if st.button("Início", type="tertiary"):
        st.session_state.page = "home"
    if st.button("Cadastro de Projeto", type="tertiary"):
        st.session_state.page = "cadastro"
    if st.button("Consulta de Projeto", type="tertiary"):
        st.session_state.page = "consultar"
    if st.button("Atualização de Projeto", type="tertiary"):
        st.session_state.page = "atualizar"
    if st.button("Gera pdf", type="tertiary"):
        st.session_state.page = "gera"

# Mostra a página correspondente
if st.session_state.page == "home":
    home.main()
elif st.session_state.page == "cadastro":
    cadastro_proj.main()
elif st.session_state.page == "consultar":
    consultar_proj.main()
elif st.session_state.page == "atualizar":
    atualizar_proj.main()
elif st.session_state.page == "gera":
    gera_pdf.main()
