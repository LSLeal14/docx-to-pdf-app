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
        """Substitui placeholders de texto mesmo quando quebrados em vários runs.
        (isso recria o conteúdo do parágrafo, perdendo formatação parcial)"""
        original = p.text
        new_text = original
        for k, v in mapping_text.items():
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

    def insert_table_after_paragraph(doc, p, records):
        if not records:
            return
        cols = list(records[0].keys())
        table = doc.add_table(rows=1 + len(records), cols=len(cols))
        # Cabeçalho
        for j, c in enumerate(cols):
            table.cell(0, j).text = str(c)
        # Linhas
        for i, row in enumerate(records, start=1):
            for j, c in enumerate(cols):
                table.cell(i, j).text = "" if row.get(c) is None else str(row.get(c))
        # Insere a tabela logo depois do parágrafo
        p._element.addnext(table._element)

    # Separa os tipos de dados
    dados_texto, dados_imagem, dados_tabela = {}, {}, {}
    for k, v in dados.items():
        if is_image(v):
            dados_imagem[k] = v
        elif is_table(v):
            dados_tabela[k] = normalize_table(v)
        else:
            dados_texto[k] = v

    # --- Processa imagens e tabelas ---
    for p in doc.paragraphs:
        for k, img in dados_imagem.items():
            ph = f"{{{{{k}}}}}"
            if ph in p.text:
                if paragraph_only_placeholder(p, ph):
                    insert_image_at_paragraph(p, img)
                else:
                    replace_text_in_paragraph(p, {k: ""})
                    p.add_run().add_picture(str(img), width=Inches(2))
        for k, rows in dados_tabela.items():
            ph = f"{{{{{k}}}}}"
            if ph in p.text:
                replace_text_in_paragraph(p, {k: ""})
                insert_table_after_paragraph(doc, p, rows)

    # --- Processa texto ---
    for p in doc.paragraphs:
        replace_text_in_paragraph(p, dados_texto)

    # --- Processa também células de tabelas já existentes ---
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for k, img in dados_imagem.items():
                    ph = f"{{{{{k}}}}}"
                    for p in cell.paragraphs:
                        if ph in p.text:
                            if paragraph_only_placeholder(p, ph):
                                insert_image_at_paragraph(p, img)
                            else:
                                replace_text_in_paragraph(p, {k: ""})
                                p.add_run().add_picture(str(img), width=Inches(2))
                for p in cell.paragraphs:
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
        "Período de Vigência": "periodo_vigencia",
        "N° da OS/OFB/NE": "n_os",
        "Objeto": "objeto",
        "Valor dos Bens/Serviços Recebidos": "valor_bens_receb",
        "Contratante": "contratante",
        "Contratada": "contratada"
    }

    campo_escolhido = st.selectbox("Selecione o campo para buscar:", list(campos.keys()))
    termo_busca = st.text_input("Digite o termo para busca:")

    projetos_ref = db.collection("projetos")
    docs = projetos_ref.stream()

    st.subheader("Projetos encontrados:")
    campo_firebase = campos[campo_escolhido]
    resultados = []

    for doc in docs:
        data = doc.to_dict()
        if termo_busca.lower() in str(data.get(campo_firebase, "")).lower():
            resultados.append((doc.id, data))

    if resultados:
        for doc_id, data in resultados:
            df_info = pd.DataFrame({
                "Item": list(campos.keys()),
            "Info": [str(data.get(campos[campo], "")) for campo in campos]
            })

            st.dataframe(df_info, use_container_width=True)

            if st.button(f"Gerar PDF", key=f"gerar_pdf_{doc_id}"):
                try:
                    # Copiar template fixo para temporário
                    caminho_fixo = "template/Template_ata_ebserh.docx"
                    if not os.path.exists(caminho_fixo):
                        st.error(f"Template não encontrado: {caminho_fixo}")
                        return
                    temp_docx = tempfile.NamedTemporaryFile(delete=False, suffix=".docx")
                    shutil.copyfile(caminho_fixo, temp_docx.name)

                    # Preencher
                    docx_obj = Document(temp_docx.name)
                    preencher_campos(docx_obj, data)

                    preenchido_path = tempfile.NamedTemporaryFile(delete=False, suffix=".docx").name
                    docx_obj.save(preenchido_path)

                    # Converter e salvar em Downloads
                    pdf_path = converter_para_pdf(preenchido_path)

                    with open(pdf_path, "rb") as pdf_file:
                        st.download_button(
                            label="Baixar PDF",
                            data=pdf_file,
                            file_name=f"projeto_{doc_id}.pdf",
                            mime="application/pdf"
                        )

                    st.success(f"PDF gerado e salvo em: {pdf_path}")
                except Exception as e:
                    st.error(f"Erro ao gerar PDF: {e}")
    else:
        st.info("Nenhum projeto encontrado.")

if __name__ == "__main__":
    main()
