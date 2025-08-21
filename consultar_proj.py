import streamlit as st
import os
import tempfile
import shutil
import re
import subprocess
from pathlib import Path
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
from docx import Document
from docx.shared import Inches

# ==== Funções auxiliares ====
def get_downloads_folder():
    home = Path.home()
    return home / "Downloads"

def extrair_campos(doc):
    campos = set()
    for p in doc.paragraphs:
        campos.update(re.findall(r"\{\{(.*?)\}\}", p.text))
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    campos.update(re.findall(r"\{\{(.*?)\}\}", p.text))
    return list(campos)

def preencher_campos(doc, dados):
    """
    Substitui placeholders {{chave}} no documento por:
      - Texto (str/int/float)
      - Imagem (caminho .png/.jpg/.jpeg)
      - Tabela (list[dict] ou pandas.DataFrame)
    """
    def is_image(v):
        return isinstance(v, (str, Path)) and str(v).lower().endswith((".png", ".jpg", ".jpeg"))

    def is_table(v):
        if isinstance(v, pd.DataFrame):
            return True
        if isinstance(v, list) and v and all(isinstance(r, dict) for r in v):
            return True
        return False

    def normalize_table(v):
        if isinstance(v, pd.DataFrame):
            return v.to_dict(orient="records")
        return v

    def replace_text_in_paragraph(p, mapping_text):
        original = p.text
        new_text = original
        # Apenas substitui se o valor não for uma lista/dicionário para evitar erros
        for k, v in mapping_text.items():
            if not isinstance(v, (list, dict)):
                 new_text = new_text.replace(f"{{{{{k}}}}}", str(v))
        if new_text != original:
            for r in p.runs:
                r.text = ""
            if p.runs:
                p.runs[0].text = new_text
            else:
                p.add_run(new_text)

    def paragraph_only_placeholder(p, placeholder):
        return p.text.strip() == placeholder

    def insert_image_at_paragraph(p, img_path):
        for r in p.runs:
            r.text = ""
        p.add_run().add_picture(str(img_path), width=Inches(2))

    # <<< MUDANÇA 1: A FUNÇÃO DA TABELA AGORA RECEBE OS DADOS COMPLETOS >>>
    # Isso é necessário para que ela possa ler o campo 'prazo_meses'
    def insert_table_after_paragraph(doc, p, records, dados_completos):
        if not records:
            return

        # <<< MUDANÇA 2: ORDENAÇÃO EXPLÍCITA DAS COLUNAS >>>
        # Usa o campo 'prazo_meses' para garantir a ordem correta das colunas
        prazo = dados_completos.get('prazo_meses')
        if prazo:
            cols_ordenadas = ['Item'] + [f"Mês {i+1}" for i in range(int(prazo))]
        else:
            # Se 'prazo_meses' não existir, usa a ordem padrão (pode não ser a correta)
            cols_ordenadas = list(records[0].keys())

        table = doc.add_table(rows=1, cols=len(cols_ordenadas))
        
        # <<< MUDANÇA 3: ADICIONA AS BORDAS (GRID) À TABELA >>>
        table.style = 'Table Grid'
        
        # Cabeçalho
        for j, col_name in enumerate(cols_ordenadas):
            table.cell(0, j).text = str(col_name)

        # Linhas
        for row_data in records:
            row = table.add_row()
            for j, col_name in enumerate(cols_ordenadas):
                # Usa .get() para buscar o valor com segurança
                cell_value = row_data.get(col_name, "") 
                row.cells[j].text = str(cell_value)
        
        # Remove o parágrafo do placeholder e insere a tabela
        p.clear() 
        p._element.addprevious(table._element)


    # Separa os tipos de dados
    dados_texto, dados_imagem, dados_tabela = {}, {}, {}
    for k, v in dados.items():
        if is_image(v):
            dados_imagem[k] = v
        elif is_table(v):
            # <<< MUDANÇA 4: ATRIBUINDO O NOME CORRETO DA TABELA >>>
            # Garante que a tabela do Firebase seja mapeada para o placeholder correto
            if 'tabela_faturamento' in dados:
                 dados_tabela['tabela_faturamento'] = normalize_table(dados['tabela_faturamento'])
        else:
            dados_texto[k] = v

    # --- Processa imagens e tabelas ---
    # É melhor iterar por uma cópia dos parágrafos, pois vamos modificar o documento
    for p in list(doc.paragraphs):
        # Itera sobre os placeholders de tabela primeiro
        for k, rows in dados_tabela.items():
            ph = f"{{{{{k}}}}}"
            if paragraph_only_placeholder(p, ph):
                # <<< MUDANÇA 5: CHAMA A FUNÇÃO MODIFICADA PASSANDO OS DADOS COMPLETOS >>>
                insert_table_after_paragraph(doc, p, rows, dados)
        
        # Processa placeholders de imagem
        for k, img in dados_imagem.items():
            ph = f"{{{{{k}}}}}"
            if paragraph_only_placeholder(p, ph):
                insert_image_at_paragraph(p, img)
            elif ph in p.text: # Lida com imagens no meio do texto
                replace_text_in_paragraph(p, {k: ""})
                p.add_run().add_picture(str(img), width=Inches(2))

    # --- Processa texto em todo o documento (parágrafos e tabelas existentes) ---
    all_paragraphs = list(doc.paragraphs)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                all_paragraphs.extend(cell.paragraphs)

    for p in all_paragraphs:
        replace_text_in_paragraph(p, dados_texto)


def converter_para_pdf(caminho_docx):
    downloads_dir = get_downloads_folder()
    os.makedirs(downloads_dir, exist_ok=True)
    comando = [
        "soffice",
        "--headless",
        "--convert-to", "pdf",
        "--outdir", str(downloads_dir),
        caminho_docx
    ]
    result = subprocess.run(comando, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Erro na conversão para PDF:\n{result.stderr}")

    arquivos = os.listdir(downloads_dir)
    pdfs = [f for f in arquivos if f.lower().endswith(".pdf")]
    if not pdfs:
        raise FileNotFoundError(f"Nenhum arquivo PDF encontrado na pasta {downloads_dir}")
    pdfs = sorted(pdfs, key=lambda f: os.path.getmtime(os.path.join(downloads_dir, f)), reverse=True)
    return os.path.join(downloads_dir, pdfs[0])

# ==== App principal ====
def main():
    st.set_page_config(layout="wide")
    st.title("Consulta de Projetos e Geração de PDF")

    FIREBASE_KEY_PATH = os.getenv("FIREBASE_KEY_PATH", "app/firebase_key.json")
    if not firebase_admin._apps:
        cred = credentials.Certificate(FIREBASE_KEY_PATH)
        firebase_admin.initialize_app(cred)

    db = firestore.client()

    campos = {
        "N° do Contrato": "n_contrato",
        "Objeto": "objeto",
    }

    campo_escolhido = st.selectbox("Selecione o campo para buscar:", list(campos.keys()))
    termo_busca = st.text_input("Digite o termo para busca:")

    if st.button("Buscar Projetos"):
        projetos_ref = db.collection("projetos")
        campo_firebase = campos[campo_escolhido]
        
        # Query mais eficiente no Firebase
        docs = projetos_ref.where(campo_firebase, '>=', termo_busca).where(campo_firebase, '<=', termo_busca + '\uf8ff').stream()
        
        resultados = [(doc.id, doc.to_dict()) for doc in docs]

        st.subheader("Projetos encontrados:")
        if resultados:
            for doc_id, data in resultados:
                st.markdown(f"---")
                st.write(f"**ID:** {doc_id} | **Objeto:** {data.get('objeto', 'N/A')}")

                if st.button(f"Gerar PDF para {data.get('n_contrato', doc_id)}", key=f"gerar_pdf_{doc_id}"):
                    with st.spinner("Gerando documento..."):
                        try:
                            # Copiar template fixo para temporário
                            caminho_fixo = "template/Template_ata_ebserh.docx"
                            if not os.path.exists(caminho_fixo):
                                st.error(f"Template não encontrado: {caminho_fixo}")
                                return
                            
                            doc_obj = Document(caminho_fixo)
                            
                            # Preencher o documento com os dados do Firebase
                            preencher_campos(doc_obj, data)

                            # Salvar o documento preenchido em um arquivo temporário
                            with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as preenchido_path:
                                doc_obj.save(preenchido_path.name)
                                
                                # Converter e salvar em Downloads
                                pdf_path = converter_para_pdf(preenchido_path.name)

                            with open(pdf_path, "rb") as pdf_file:
                                st.download_button(
                                    label="Baixar PDF",
                                    data=pdf_file,
                                    file_name=f"projeto_{doc_id}.pdf",
                                    mime="application/pdf"
                                )
                            st.success(f"PDF gerado com sucesso!")
                        except Exception as e:
                            st.error(f"Erro ao gerar PDF: {e}")
                            st.exception(e) # Mostra o traceback do erro para depuração
        else:
            st.info("Nenhum projeto encontrado.")

if __name__ == "__main__":
    main()