import streamlit as st
import home
import cadastro_proj
import consultar_proj
import atualizar_proj
import gera_pdf
import atualizar_medi

st.set_page_config(layout="wide")

def get_github_icon_link(url):
    return f"""
    <a href="{url}" target="_blank" style="display: inline-flex; align-items: center; text-decoration: none;">
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-github">
            <path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22"></path>
        </svg>
        <span style="margin-left: 8px; color: #FAFAFA;">GitHub</span>
    </a>
    """

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
    if st.button("Atualização de Medições", type="tertiary"):
        st.session_state.page = "medicoes"


# Mostra a página correspondente
if st.session_state.page == "home":
    home.main()
elif st.session_state.page == "cadastro":
    cadastro_proj.main()
elif st.session_state.page == "consultar":
    consultar_proj.main()
elif st.session_state.page == "atualizar":
    atualizar_proj.main()
elif st.session_state.page == "medicoes":
    atualizar_medi.main()

st.sidebar.header("Sobre")
github_url = "https://github.com/LSLeal14/docx-to-pdf-app.git"
st.sidebar.markdown(get_github_icon_link(github_url), unsafe_allow_html=True)
