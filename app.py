import streamlit as st
import convertapi
import os
import tempfile
import traceback
import io
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

st.set_page_config(page_title="Scanner OCR IRPF", layout="centered")

# --- 1. CONFIGURAÇÃO ---
def configurar_apis():
    if "convertapi" not in st.secrets or "secret" not in st.secrets["convertapi"]:
        st.error("❌ ERRO: Falta o segredo do ConvertAPI nos Secrets.")
        return False
    
    chave = st.secrets["convertapi"]["secret"]
    convertapi.api_secret = chave
    convertapi.api_credentials = chave 
    return True

# --- 2. A MÁGICA (OCR EM PORTUGUÊS) ---
def converter_para_pdf_pesquisavel(arquivo_upload):
# --- VERSÃO TURBO: LIMPA A IMAGEM ANTES DE LER ---
def converter_na_nuvem(arquivo_upload):
    try:
        nome_arquivo = arquivo_upload.name
        extensao = os.path.splitext(nome_arquivo)[1].lower() or ".jpg"

        # Salva temporário
        with tempfile.NamedTemporaryFile(delete=False, suffix=extensao) as temp_input:
            temp_input.write(arquivo_upload.getvalue())
            input_path = temp_input.name

        # --- PARÂMETROS DE ELITE ---
        # Aqui a gente obriga o robô a tratar a imagem
        parametros = {
            'File': input_path,
            'Ocr': 'true',               # Ligar Leitura
            'OcrLanguage': 'pt',         # Português
            'OcrMode': 'Force',          # <--- OBRIGA a ler mesmo se estiver ruim
            'ImagePreprocessing': 'true',# <--- LIMPA a imagem antes (essencial pra cupom)
            'RemoveNoise': 'true',       # Tira sujeira do papel
            'Deskew': 'true',            # Desentorta
            'ScaleImage': 'true',        # Melhora a resolução
            'StoreFile': 'true'
        }

        # Envia pra API
        result = convertapi.convert('pdf', parametros)
        
        # Baixa o PDF
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_output:
            result.save_files(temp_output.name)
            output_path = temp_output.name
            
        with open(output_path, 'rb') as f:
            pdf_bytes = f.read()
            
        # Limpa sujeira
        if os.path.exists(input_path): os.remove(input_path)
        if os.path.exists(output_path): os.remove(output_path)
        
        return io.BytesIO(pdf_bytes)

    except Exception as e:
        # Se der erro, mostra no Streamlit pra gente saber
        st.error(f"Erro na conversão: {e}")
        return None


def upload_drive(service, file_obj, name, folder_id, mime):
    try:
        meta = {'name': name, 'parents': [folder_id]}
        media = MediaIoBaseUpload(file_obj, mimetype=mime, resumable=True)
        service.files().create(body=meta, media_body=media, fields='id').execute()
        return True
    except Exception as e:
        st.error(f"Erro Upload: {e}")
        return False

# --- 4. TELA ---
st.title("📄 Digitalizador OCR (Português)")

FOLDER_ID_RAIZ = "1hxtNpuLtMiwfahaBRQcKrH6w_2cN_YFQ" 

if configurar_apis():
    if "cpf_atual" not in st.session_state: st.session_state["cpf_atual"] = ""

    if not st.session_state["cpf_atual"]:
        cpf = st.text_input("CPF do Cliente:", max_chars=14)
        if st.button("Iniciar"): 
            if len(cpf) > 5: st.session_state["cpf_atual"] = cpf; st.rerun()
    else:
        st.success(f"Cliente: **{st.session_state['cpf_atual']}**")
        if st.button("Trocar Cliente"): st.session_state["cpf_atual"] = ""; st.rerun()
        
        st.divider()
        st.info("💡 Dica: O sistema vai ler o texto das imagens em Português.")
        
        files = st.file_uploader("Documentos", accept_multiple_files=True)
        
        if files and st.button("Processar e Enviar"):
            service = get_drive_service()
            
            # Busca/Cria Pasta
            try:
                q = f"name = '{st.session_state['cpf_atual']}' and '{FOLDER_ID_RAIZ}' in parents and trashed=false"
                res = service.files().list(q=q).execute().get('files', [])
                if res: folder_id = res[0]['id']
                else: folder_id = service.files().create(body={'name': st.session_state['cpf_atual'], 'parents': [FOLDER_ID_RAIZ], 'mimeType': 'application/vnd.google-apps.folder'}).execute()['id']
                
                bar = st.progress(0)
                status = st.empty()
                
                for i, f in enumerate(files):
                    status.text(f"Lendo texto de: {f.name}...")
                    
                    # Envia para a API fazer o OCR em PT-BR
                    pdf_ocr = converter_para_pdf_pesquisavel(f)
                    
                    if pdf_ocr:
                        nome = f.name.rsplit('.', 1)[0] + ".pdf"
                        upload_drive(service, pdf_ocr, nome, folder_id, 'application/pdf')
                    else:
                        st.warning(f"Falha ao ler {f.name}. Enviando original.")
                        upload_drive(service, f, f.name, folder_id, f.type)
                    
                    bar.progress((i+1)/len(files))
                
                status.text("Pronto!")
                st.balloons()
                st.success("Arquivos salvos e pesquisáveis!")
                
            except Exception as e:
                st.error(f"Erro Geral: {e}")
