import streamlit as st
import convertapi
import os
import tempfile
import io
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

st.set_page_config(page_title="Scanner Direto (Raw)", layout="centered")

# --- 1. CONFIGURAÇÃO ---
def configurar_apis():
    if "convertapi" not in st.secrets or "secret" not in st.secrets["convertapi"]:
        st.error("❌ ERRO: Falta [convertapi] nos Secrets.")
        return False
    chave = st.secrets["convertapi"]["secret"]
    convertapi.api_secret = chave
    convertapi.api_credentials = chave 
    return True

# --- 2. CONVERSÃO PURA (SEM MEXER NO ARQUIVO) ---
def converter_sem_filtro(arquivo_upload):
    try:
        nome = arquivo_upload.name
        ext = os.path.splitext(nome)[1].lower()
        if not ext: ext = ".jpg"

        # Salva o arquivo EXATAMENTE como veio
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as t_in:
            t_in.write(arquivo_upload.getvalue())
            input_path = t_in.name

        # Manda pra API sem filtros, apenas pedindo OCR
        parametros = {
            'File': input_path,
            'Ocr': 'true',         # LER TEXTO
            'OcrLanguage': 'pt',   # PORTUGUÊS
            'StoreFile': 'true'    # Devolve o arquivo
        }

        # Se for imagem ou PDF, a saída é sempre PDF
        result = convertapi.convert('pdf', parametros)
        
        # Baixa o resultado
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as t_out:
            result.save_files(t_out.name)
            output_path = t_out.name
            
        with open(output_path, 'rb') as f:
            pdf_bytes = f.read()
            
        # Limpa
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
st.title("⚡ Scanner IRPF (Modo Direto)")

# ⚠️⚠️⚠️ SEU ID DA PASTA AQUI ⚠️⚠️⚠️
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
        
        st.info("ℹ️ Enviando arquivo puro para o motor de OCR.")
        
        files = st.file_uploader("Documentos (Print/Foto/PDF)", accept_multiple_files=True)
        
        if files and st.button("Processar"):
            service = get_drive_service()
            
            if "COLOQUE" in FOLDER_ID_RAIZ:
                st.error("🛑 Faltou o ID da pasta na linha 95!")
                st.stop()

            # Pega pasta
            try:
                q = f"name = '{st.session_state['cpf_atual']}' and '{FOLDER_ID_RAIZ}' in parents and trashed=false"
                res = service.files().list(q=q).execute().get('files', [])
                if res: folder_id = res[0]['id']
                else: folder_id = service.files().create(body={'name': st.session_state['cpf_atual'], 'parents': [FOLDER_ID_RAIZ], 'mimeType': 'application/vnd.google-apps.folder'}).execute()['id']
                
                bar = st.progress(0)
                status = st.empty()
                
                for i, f in enumerate(files):
                    status.text(f"Enviando {f.name}...")
                    
                    pdf_pronto = converter_sem_filtro(f)
                    
                    if pdf_pronto:
                        nome = f.name.rsplit('.', 1)[0] + ".pdf"
                        upload_drive(service, pdf_pronto, nome, folder_id, 'application/pdf')
                    else:
                        st.warning(f"Falha em {f.name}. Enviando original.")
                        f.seek(0)
                        upload_drive(service, f, f.name, folder_id, f.type)
                    
                    bar.progress((i+1)/len(files))
                
                status.text("Pronto!")
                st.balloons()
                st.success("✅ Arquivos enviados!")
                
            except Exception as e:
                st.error(f"Erro Geral: {e}")
