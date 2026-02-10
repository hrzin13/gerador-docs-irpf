import streamlit as st
import convertapi
import os
import tempfile
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

st.set_page_config(page_title="Upload IRPF Pro", layout="centered")

# --- 1. CONFIGURAÇÃO (API e Google) ---
if "convertapi" in st.secrets:
    convertapi.api_secret = st.secrets["convertapi"]["secret"]
else:
    st.error("Falta configurar o segredo do ConvertAPI nos Secrets!")

def get_drive_service():
    # (Sua autenticação do Google que já funciona continua igual)
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

# --- 2. FUNÇÃO MÁGICA (Via API Externa) ---
def converter_via_api(arquivo_upload):
    try:
        # Salva o arquivo temporariamente para enviar
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(arquivo_upload.name)[1]) as temp_input:
            temp_input.write(arquivo_upload.getvalue())
            input_path = temp_input.name

        # Manda para o ConvertAPI transformar em PDF com OCR
        # 'ocr=true' força a leitura do texto
        # 'scale=true' ajusta para caber na página
        result = convertapi.convert('pdf', {
            'File': input_path,
            'StoreFile': 'true',
            'Ocr': 'true', 
            'ScaleProportional': 'true',
            'PageSize': 'a4' # Força sair em A4
        })
        
        # Baixa o arquivo pronto
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_output:
            result.save_files(temp_output.name)
            temp_output_path = temp_output.name
            
        # Lê o PDF pronto para memória
        with open(temp_output_path, 'rb') as f:
            pdf_bytes = f.read()
            
        # Limpeza
        os.remove(input_path)
        os.remove(temp_output_path)
        
        return io.BytesIO(pdf_bytes)

    except Exception as e:
        st.error(f"Erro na conversão API: {e}")
        return None

# --- 3. UPLOAD PRO DRIVE ---
def upload_drive(service, file_obj, name, folder_id, mime):
    meta = {'name': name, 'parents': [folder_id]}
    media = MediaIoBaseUpload(file_obj, mimetype=mime, resumable=True)
    service.files().create(body=meta, media_body=media, fields='id').execute()

# --- 4. INTERFACE ---
import io # Precisa importar isso aqui ou lá em cima

st.title("🚀 Scanner IRPF Profissional")

FOLDER_ID_RAIZ = "1hxtNpuLtMiwfahaBRQcKrH6w_2cN_YFQ" 

if "cpf_atual" not in st.session_state: st.session_state["cpf_atual"] = ""

if not st.session_state["cpf_atual"]:
    cpf = st.text_input("CPF do Cliente:")
    if st.button("Iniciar"): 
        if len(cpf) > 5: st.session_state["cpf_atual"] = cpf; st.rerun()
else:
    st.markdown(f"Cliente: **{st.session_state['cpf_atual']}**")
    if st.button("Sair"): st.session_state["cpf_atual"] = ""; st.rerun()
    
    files = st.file_uploader("Documentos", accept_multiple_files=True)
    
    if files and st.button("Processar"):
        service = get_drive_service()
        
        # Busca pasta do CPF
        q = f"name = '{st.session_state['cpf_atual']}' and '{FOLDER_ID_RAIZ}' in parents and trashed=false"
        res = service.files().list(q=q).execute().get('files', [])
        if res: folder_id = res[0]['id']
        else: folder_id = service.files().create(body={'name': st.session_state['cpf_atual'], 'parents': [FOLDER_ID_RAIZ], 'mimeType': 'application/vnd.google-apps.folder'}).execute()['id']
        
        bar = st.progress(0)
        for i, f in enumerate(files):
            # Se for imagem, usa a API PRO
            if f.type.startswith('image/'):
                st.toast(f"Digitalizando {f.name} via API...")
                pdf_pro = converter_via_api(f)
                if pdf_pro:
                    nome = f.name.rsplit('.', 1)[0] + ".pdf"
                    upload_drive(service, pdf_pro, nome, folder_id, 'application/pdf')
                else:
                    upload_drive(service, f, f.name, folder_id, f.type)
            else:
                upload_drive(service, f, f.name, folder_id, f.type)
            bar.progress((i+1)/len(files))
        st.success("Tudo enviado com qualidade máxima!")
