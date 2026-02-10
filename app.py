import streamlit as st
import convertapi
import os
import tempfile
import io
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

st.set_page_config(page_title="Prova Real (Word)", layout="centered")

# --- 1. CONFIGURAÇÃO ---
def configurar_apis():
    if "convertapi" not in st.secrets:
        st.error("❌ Falta [convertapi] nos Secrets.")
        return False
    
    chave = st.secrets["convertapi"]["secret"]
    convertapi.api_secret = chave
    convertapi.api_credentials = chave 
    return True

# --- 2. CONVERSÃO PARA WORD (DOCX) ---
def converter_para_word(arquivo_upload):
    try:
        nome = arquivo_upload.name
        ext = os.path.splitext(nome)[1].lower() or ".jpg"

        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as t_in:
            t_in.write(arquivo_upload.getvalue())
            input_path = t_in.name

        # MANDA CONVERTER PRA WORD (DOCX)
        # Assim a gente VÊ se o texto foi lido mesmo
        parametros = {
            'File': input_path,
            'Ocr': 'true',
            'OcrLanguage': 'pt',     # Português
            'ImagePreprocessing': 'true', # Limpeza
            'StoreFile': 'true'
        }

        # Pede 'docx' em vez de 'pdf'
        result = convertapi.convert('docx', parametros)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as t_out:
            result.save_files(t_out.name)
            output_path = t_out.name
            
        with open(output_path, 'rb') as f:
            arquivo_bytes = f.read()
            
        if os.path.exists(input_path): os.remove(input_path)
        if os.path.exists(output_path): os.remove(output_path)
        
        return io.BytesIO(arquivo_bytes)

    except Exception as e:
        st.error(f"Erro na API: {e}")
        return None

# --- 3. GOOGLE DRIVE ---
def get_drive_service():
    try:
        if "gcp_service_account" in st.secrets:
            creds = service_account.Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=['https://www.googleapis.com/auth/drive'])
        elif "google_auth" in st.secrets:
            info = st.secrets["google_auth"]
            creds = Credentials(None, refresh_token=info["refresh_token"], token_uri="https://oauth2.googleapis.com/token", client_id=info["client_id"], client_secret=info["client_secret"])
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
st.title("📝 Teste Word (Editável)")

# ⚠️⚠️⚠️ NÃO ESQUEÇA O ID DA PASTA AQUI EMBAIXO ⚠️⚠️⚠️
FOLDER_ID_RAIZ = "COLOQUE_SEU_ID_AQUI" 

if configurar_apis():
    if "cpf_atual" not in st.session_state: st.session_state["cpf_atual"] = ""

    if not st.session_state["cpf_atual"]:
        cpf = st.text_input("CPF do Cliente:")
        if st.button("Entrar"): st.session_state["cpf_atual"] = cpf; st.rerun()
    else:
        st.info(f"Cliente: {st.session_state['cpf_atual']}")
        
        files = st.file_uploader("Mande a foto pra testar:", accept_multiple_files=True)
        
        if files and st.button("Converter para Word"):
            service = get_drive_service()
            
            # Verificação do ID
            if "COLOQUE" in FOLDER_ID_RAIZ:
                st.error("⚠️ Você esqueceu de colocar o ID DA PASTA no código!")
                st.stop()

            # Pega pasta
            try:
                q = f"name = '{st.session_state['cpf_atual']}' and '{FOLDER_ID_RAIZ}' in parents and trashed=false"
                res = service.files().list(q=q).execute().get('files', [])
                if res: folder_id = res[0]['id']
                else: folder_id = service.files().create(body={'name': st.session_state['cpf_atual'], 'parents': [FOLDER_ID_RAIZ], 'mimeType': 'application/vnd.google-apps.folder'}).execute()['id']
                
                bar = st.progress(0)
                
                for i, f in enumerate(files):
                    st.write(f"Transformando {f.name} em Word...")
                    
                    word_doc = converter_para_word(f)
                    
                    if word_doc:
                        nome = f.name.rsplit('.', 1)[0] + ".docx"
                        # Salva como Word
                        upload_drive(service, word_doc, nome, folder_id, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')
                    else:
                        st.warning("Falha na conversão.")
                    
                    bar.progress((i+1)/len(files))
                
                st.success("✅ Verifique no Drive! Se abrir o Word e tiver texto, funcionou.")
                
            except Exception as e:
                st.error(f"Erro Geral: {e}")
