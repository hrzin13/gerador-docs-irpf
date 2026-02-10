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

st.set_page_config(page_title="Scanner IRPF Pro", layout="centered")

# --- 1. CONFIGURAÇÃO (Blindada) ---
def configurar_apis():
    # Verifica Secrets
    if "convertapi" not in st.secrets or "secret" not in st.secrets["convertapi"]:
        st.error("❌ Falta o segredo do ConvertAPI.")
        return False
    
    # Configura Senha
    chave = st.secrets["convertapi"]["secret"]
    convertapi.api_secret = chave
    convertapi.api_credentials = chave 
    return True

# --- 2. FUNÇÃO MÁGICA: MANDA DIRETO PRA NUVEM ---
def converter_na_nuvem(arquivo_upload):
    try:
        # Define a extensão do arquivo (jpg, png, pdf)
        nome_arquivo = arquivo_upload.name
        extensao = os.path.splitext(nome_arquivo)[1].lower()
        if not extensao: extensao = ".jpg"

        # Salva o arquivo original temporariamente
        with tempfile.NamedTemporaryFile(delete=False, suffix=extensao) as temp_input:
            temp_input.write(arquivo_upload.getvalue())
            input_path = temp_input.name

        # --- AQUI É O PULO DO GATO ---
        # Mandamos direto pro ConvertAPI com os parâmetros de OCR ligados
        # Eles se viram pra deixar A4 e Ler o texto
        
        parametros = {
            'File': input_path,
            'Ocr': 'true',            # Liga o leitor de texto
            'OcrLanguage': 'pt',      # Força Português (BR)
            'PageSize': 'a4',         # Força sair em tamanho A4
            'ScaleProportional': 'true', # Ajusta a imagem pra caber na folha
            'StoreFile': 'true'
        }

        # Faz a conversão (Seja imagem ou PDF, a saída é sempre PDF OCR)
        result = convertapi.convert('pdf', parametros)
        
        # Baixa o resultado
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_output:
            result.save_files(temp_output.name)
            output_path = temp_output.name
            
        with open(output_path, 'rb') as f:
            pdf_bytes = f.read()
            
        # Limpeza
        if os.path.exists(input_path): os.remove(input_path)
        if os.path.exists(output_path): os.remove(output_path)
        
        return io.BytesIO(pdf_bytes)

    except Exception as e:
        st.error(f"Erro na API: {e}")
        return None

# --- 3. GOOGLE DRIVE ---
def get_drive_service():
    try:
        if "gcp_service_account" in st.secrets:
            creds = service_account.Credentials.from_service_account_info(
                st.secrets["gcp_service_account"], scopes=['https://www.googleapis.com/auth/drive'])
        elif "google_auth" in st.secrets:
            info = st.secrets["google_auth"]
            creds = Credentials(None, refresh_token=info["refresh_token"], 
                              token_uri="https://oauth2.googleapis.com/token",
                              client_id=info["client_id"], client_secret=info["client_secret"])
        else:
            return None
        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        st.error(f"Erro Google: {e}")
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
st.title("📄 Scanner IRPF (Direto na Nuvem)")
apis_ok = configurar_apis()

# SEU ID DA PASTA AQUI
FOLDER_ID_RAIZ = "1hxtNpuLtMiwfahaBRQcKrH6w_2cN_YFQ" 

if apis_ok:
    if "cpf_atual" not in st.session_state: st.session_state["cpf_atual"] = ""

    if not st.session_state["cpf_atual"]:
        cpf = st.text_input("CPF do Cliente:", max_chars=14)
        if st.button("Iniciar"): 
            if len(cpf) > 5: st.session_state["cpf_atual"] = cpf; st.rerun()
    else:
        st.info(f"Cliente: **{st.session_state['cpf_atual']}**")
        if st.button("Trocar"): st.session_state["cpf_atual"] = ""; st.rerun()
        
        files = st.file_uploader("Documentos", accept_multiple_files=True)
        
        if files and st.button("Digitalizar e Enviar"):
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
                    status.text(f"Enviando pra API: {f.name}...")
                    
                    # Manda TUDO pra API (Imagem ou PDF)
                    pdf_ocr = converter_na_nuvem(f)
                    
                    if pdf_ocr:
                        nome = f.name.rsplit('.', 1)[0] + ".pdf"
                        upload_drive(service, pdf_ocr, nome, folder_id, 'application/pdf')
                    else:
                        st.warning(f"Falha na API com {f.name}. Enviando original.")
                        upload_drive(service, f, f.name, folder_id, f.type)
                    
                    bar.progress((i+1)/len(files))
                
                status.text("Sucesso!")
                st.balloons()
                st.success("Arquivos processados e salvos!")
                
            except Exception as e:
                st.error(f"Erro Geral: {e}")
