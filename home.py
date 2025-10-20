import streamlit as st


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

