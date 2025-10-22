# Gestor de Atas de Medição - Engenharia Hospitalar

[](https://render.com/) Este projeto é uma aplicação web desenvolvida com Streamlit destinada a gerenciar, acompanhar e gerar atas técnicas de medição para projetos de infraestrutura e engenharia. A plataforma foi criada para apoiar o setor de infraestrutura da EBSERH (Empresa Brasileira de Serviços Hospitalares), especificamente no Hospital de Clínicas da Universidade Federal de Uberlândia (HC-UFU).

A aplicação centraliza o cadastro de contratos, o planejamento físico-financeiro e o registro de medições mensais, culminando na geração automática de um relatório técnico (Ata) em formato PDF, baseado em um template Word (`.docx`).

## Funcionalidades Principais

O sistema é organizado em uma navegação multi-página:

  * **Início:** Apresenta um guia visual e passo a passo de como utilizar todas as funcionalidades da plataforma.
  * **Cadastro de Projeto:** Permite o registro de um novo projeto, incluindo informações gerais do contrato (número, objeto, contratante, valores, vigência) e a criação da "Tabela de Planejamento" inicial.
  * **Consulta de Projeto:** Funcionalidade de busca que permite localizar projetos existentes no banco de dados e, o mais importante, **gerar a Ata de Medição em PDF** correspondente.
  * **Atualização de Projeto:** Permite editar a "Tabela de Planejamento" de um projeto existente, sendo útil para replanejamentos ou para estender o prazo de obras atrasadas.
  * **Atualização de Medições:** A página principal para o acompanhamento da obra. O fiscal pode buscar um projeto e lançar os valores medidos em um determinado mês na "Tabela de Medição".

## Como Funciona: Geração de Relatórios

A funcionalidade central de geração de PDF segue um fluxo de trabalho robusto:

1.  **Consulta (Frontend):** O usuário seleciona um projeto na página "Consulta de Projetos".
2.  **Processamento (Backend):** A aplicação busca todos os dados do projeto no **Firestore**, incluindo as tabelas de planejamento e medição.
3.  **Análise de Dados:** O módulo `processamento.py` e `data_gen/graphs.py` (usando `pandas` e `matplotlib`) geram todas as tabelas de resumo (Tabela 1 a 5) e os gráficos de desempenho (como a Curva S).
4.  **Preenchimento do Template:** Os dados e gráficos gerados são usados para preencher os placeholders (ex: `{{n_contrato}}`, `{{table}}`, `{{grafico_1}}`) do template `template/Template_ata_ebserh.docx` usando a biblioteca `python-docx`.
5.  **Conversão para PDF:** O arquivo `.docx` preenchido é salvo temporariamente e, em seguida, o **LibreOffice (soffice)** é invocado via `subprocess` (no modo *headless*) para converter o documento em um PDF.
6.  **Download:** O PDF final é disponibilizado para download no navegador do usuário.

## Tecnologias Utilizadas

  * **Frontend:** [Streamlit](https://streamlit.io/)
  * **Banco de Dados:** [Google Firebase (Firestore)](https://firebase.google.com/products/firestore)
  * **Análise de Dados:** [Pandas](https://pandas.pydata.org/) & [Numpy](https://numpy.org/)
  * **Geração de Gráficos:** [Matplotlib](https://matplotlib.org/)
  * **Manipulação de Documentos:** [python-docx](https://python-docx.readthedocs.io/en/latest/)
  * **Conversão DOCX para PDF:** [LibreOffice](https://www.libreoffice.org/)
  * **Contêiner:** [Docker](https://www.docker.com/)

## Configuração e Instalação

A forma mais recomendada de executar este projeto é via Docker, pois ele lida com a instalação complexa do LibreOffice.

### Pré-requisitos

1.  **Conta de Serviço do Firebase:**

      * Crie um projeto no [Firebase Console](https://console.firebase.google.com/).
      * Habilite o **Firestore**.
      * Vá para "Configurações do Projeto" \> "Contas de Serviço".
      * Gere uma nova chave privada. Isso fará o download de um arquivo `.json`.
      * Renomeie este arquivo para `firebase_key.json` e coloque-o na raiz do projeto. (Este arquivo está no `.gitignore` e não deve ser enviado ao repositório).

2.  **Docker:**

      * Instale o [Docker Desktop](https://www.docker.com/products/docker-desktop/) ou o Docker Engine na sua máquina.

### Método 1: Executando com Docker (Localmente)

O `Dockerfile` fornecido já instala o Python, o LibreOffice e todas as dependências do `requirements.txt`.

1.  **Construa a imagem Docker:**

    ```bash
    docker build -t gestor-atas .
    ```

2.  **Execute o contêiner:**
    Você precisa "montar" seu arquivo de chave do Firebase dentro do contêiner.

    ```bash
    # Certifique-se de que o 'firebase_key.json' está no mesmo local
    # onde você está executando este comando.

    docker run -p 8501:8501 \
           -v "$(pwd)/firebase_key.json:/app/firebase_key.json" \
           -e "FIREBASE_KEY_PATH=firebase_key.json" \
           gestor-atas
    ```

    *Nota: O `Dockerfile` copia o `.env` que aponta para `firebase_key.json`, mas definir a variável de ambiente `-e` garante que ele seja encontrado.*

3.  Acesse o aplicativo em `http://localhost:8501`.

### Método 2: Deploy no Render.com (Recomendado para Produção)

Esta é a abordagem recomendada para deploy, pois o Render suporta `Dockerfiles`, permitindo a instalação do **LibreOffice**.

1.  **Configure o Serviço no Render:**

      * No seu dashboard do Render, clique em **"New"** \> **"Web Service"**.
      * Conecte seu repositório GitHub/GitLab.
      * Defina o **Runtime** como **"Docker"**. O Render detectará automaticamente seu `Dockerfile`.

2.  **Configure o Comando de Início:**

      * **Start Command:** `streamlit run main.py --server.address=0.0.0.0`
        *(O parâmetro `--server.address=0.0.0.0` é vital para o Render se conectar ao contêiner).*

3.  **Configure a Chave do Firebase (Secrets):**

      * Vá para a aba **"Environment"** do seu serviço.
      * Adicione uma Variável de Ambiente:
          * **Key:** `FIREBASE_KEY_PATH`
          * **Value:** `app/firebase_key.json` (Este é o caminho *dentro* do contêiner onde o Render colocará o arquivo).
      * Role para baixo até **"Secret Files"** e clique em **"Add Secret File"**:
          * **Mount Path:** `app/firebase_key.json` (Deve ser idêntico ao valor da variável de ambiente acima).
          * **Contents:** Abra seu arquivo `firebase_key.json` local, copie todo o conteúdo JSON e cole-o nesta caixa.

4.  **Faça o Deploy:**

      * Selecione um plano (o plano "Free" pode ser lento para iniciar e gerar PDFs devido ao uso de memória do LibreOffice; considere um plano pago se houver problemas de desempenho).
      * Clique em **"Create Web Service"**.

O Render irá construir a imagem Docker, injetar seu arquivo secreto e iniciar o serviço.
