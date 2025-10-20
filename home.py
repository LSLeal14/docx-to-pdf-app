import streamlit as st

def get_github_icon_link(url):
    return f"""
    <a href="{url}" target="_blank" style="display: inline-flex; align-items: center; text-decoration: none;">
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-github">
            <path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22"></path>
        </svg>
        <span style="margin-left: 8px; color: #FAFAFA;">GitHub</span>
    </a>
    """

st.write("Conteúdo do app.")

def main():
    
    st.set_page_config(layout="wide")

    st.title("Início")
    st.write("Bem-vindo!")

    st.header("Passo a passo para uso da plataforma")
    st.subheader("1. Navegação")
    st.image("img/Screenshot from 2025-10-20 10-05-52.png", width=1000)

    st.text("A navegação pela pagina é realizada atravez do menu retratil a esquerda, a partir dele as demais paginas podem ser acessadas. No canto supeior esquerdo o menu de configurações. Ao centro o guia de uso do site.")

    st.subheader("2. Cadastro de Projeto")
    st.image("img/Screenshot from 2025-10-20 09-13-30.png", width=1000)

    st.text("Em cadastro de projeto serão inseridas indormações fixas do projeto, como as que compoem o cabeçalho da ata e a criação das tabelas de planejamento e medição. O fluxo recomendado é o mesmo que se encontra na página. Determinação do prazo do projeto ira atualizar a tabela ao final do formulário. Com exceção do total por etapa, todos os campos devem ser preenchidos.")

    st.subheader("3. Consulta e geração do relatório de medição")
    st.image("img/Screenshot from 2025-10-20 09-15-37.png", width=1000)

    st.text("A Consulta e geração serve dois propositos, o primeiro é buscar informações para que sejam realizadas atualizações de mediçoes ou de projetos e a geração da ata referente a ultima atualização. O site não quarda as atas, sempre que o pdf é gerado todas as informações referentes ao projeto selecionados são solicitadas do banco de dados e processadas novamente.")

    st.subheader("4. Atualização de tabela de Planejamento")
    st.image("img/Screenshot from 2025-10-20 09-16-52.png", width=1000)

    st.text("Para o caso de atrasos ou replanejamentos")

    st.subheader("5. Atualização de tabela de Medição")
    st.image("img/Screenshot from 2025-10-20 09-17-34.png", width=1000)
    
    st.text("A pagina de medições permite a atualização com novas medições e edição de medições anteriores. Aqui a unica tabela editada será a tabela de medições")

    st.sidebar.header("Sobre")
    github_url = "https://github.com/LSLeal14/docx-to-pdf-app.git"
    st.sidebar.markdown(get_github_icon_link(github_url), unsafe_allow_html=True)
