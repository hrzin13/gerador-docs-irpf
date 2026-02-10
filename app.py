import streamlit as st
import io
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

st.set_page_config(page_title="Scanner Google Nativo", layout="centered")

# --- 1. CONFIGURAÇÃO (GOOGLE) ---
def get_drive_service():
    try:
        # Tenta pegar dos secrets
        if "gcp_service_account" in st.secrets:
            creds = service_account.Credentials.from_service_account_info(
                st.secrets["gcp_service_account"], scopes=['https://www.googleapis.com/auth/drive'])
        elif "google_auth" in st.secrets:
            info = st.secrets["google_auth"]
            creds = Credentials(None, refresh_token=info["refresh_token"], 
                              token_uri="https://oauth2.googleapis.com/token",
                              client_id=info["client_id"], client_secret=info["client_secret"])
        else:
            st.error("❌ Erro: Faltam as credenciais do Google nos Secrets.")
            return None
        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        st.error(f"Erro ao conectar no Google: {e}")
        return None

# --- 2. A MÁGICA: USA O GOOGLE PRA LER O TEXTO ---
def ocr_pelo_google(service, arquivo_upload, folder_id):
    try:
        nome_original = arquivo_upload.name
        mime_type = arquivo_upload.type
        
        # 1. SOBE COMO "GOOGLE DOC" (Isso força o OCR)
        # O segredo é o mimeType 'application/vnd.google-apps.document'
        meta_temp = {
            'name': f"[TEMP] {nome_original}",
            'mimeType': 'application/vnd.google-apps.document', # <--- O PULO DO GATO
            'parents': [folder_id]
        }
        
        media_temp = MediaIoBaseUpload(arquivo_upload, mimetype=mime_type, resumable=True)
        
        arquivo_temp = service.files().create(
            body=meta_temp, 
            media_body=media_temp, 
            fields='id'
        ).execute()
        
        temp_id = arquivo_temp.get('id')
        
        # 2. CONVERTE ESSE DOC (QUE JÁ TEM TEXTO) PARA PDF
        # Agora baixamos o arquivo que o Google criou, mas pedindo em PDF
        pdf_content = service.files().export(
            fileId=temp_id,
            mimeType='application/pdf'
        ).execute()
        
        # 3. APAGA O ARQUIVO TEMPORÁRIO (O RASCUNHO)
        service.files().delete(fileId=temp_id).execute()
        
        return pdf_content # Retorna os bytes do PDF pronto

    except Exception as e:
        st.error(f"Erro no OCR Google: {e}")
        return None

# --- 3. UPLOAD FINAL ---
def upload_final(service, pdf_bytes, nome, folder_id):
    try:
        meta = {'name': nome, 'parents': [folder_id]}
        media = MediaIoBaseUpload(io.BytesIO(pdf_bytes), mimetype='application/pdf', resumable=True)
        service.files().create(body=meta, media_body=media, fields='id').execute()
        return True
    except Exception as e:
        st.error(f"Erro ao Salvar Final: {e}")
        return False

# --- 4. TELA ---
st.title("G-Scanner (OCR Nativo)")

# ⚠️⚠️⚠️ SEU ID DA PASTA AQUI ⚠️⚠️⚠️
FOLDER_ID_RAIZ = "1hxtNpuLtMiwfahaBRQcKrH6w_2cN_YFQ" 

if "cpf_atual" not in st.session_state: st.session_state["cpf_atual"] = ""

# Verifica se logou no Google
service = get_drive_service()

if service:
    if not st.session_state["cpf_atual"]:
        cpf = st.text_input("CPF do Cliente:", max_chars=14)
        if st.button("Iniciar"): 
            if len(cpf) > 5: st.session_state["cpf_atual"] = cpf; st.rerun()
    else:
        st.success(f"Cliente: **{st.session_state['cpf_atual']}**")
        if st.button("Trocar Cliente"): st.session_state["cpf_atual"] = ""; st.rerun()
        
        st.info("ℹ️ Usando a inteligência do Google Drive para ler o texto.")
        
        files = st.file_uploader("Mande Prints, Fotos ou Imagens", accept_multiple_files=True)
        
        if files and st.button("Processar pelo Google"):
            
            if "COLOQUE" in FOLDER_ID_RAIZ:
                st.error("🛑 Faltou o ID da pasta na linha 83!")
                st.stop()

            # Busca/Cria Pasta do Cliente
            try:
                q = f"name = '{st.session_state['cpf_atual']}' and '{FOLDER_ID_RAIZ}' in parents and trashed=false"
                res = service.files().list(q=q).execute().get('files', [])
                if res: folder_id = res[0]['id']
                else: folder_id = service.files().create(body={'name': st.session_state['cpf_atual'], 'parents': [FOLDER_ID_RAIZ], 'mimeType': 'application/vnd.google-apps.folder'}).execute()['id']
                
                bar = st.progress(0)
                status = st.empty()
                
                for i, f in enumerate(files):
                    status.text(f"Google está lendo: {f.name}...")
                    
                    # Roda o processo
                    pdf_bytes = ocr_pelo_google(service, f, folder_id)
                    
                    if pdf_bytes:
                        nome_pdf = f.name.rsplit('.', 1)[0] + ".pdf"
                        upload_final(service, pdf_bytes, nome_pdf, folder_id)
                    else:
                        st.warning(f"Falha em {f.name}.")
                    
                    bar.progress((i+1)/len(files))
                
                status.text("Pronto!")
                st.balloons()
                st.success("✅ PDFs gerados pelo Google!")
                
            except Exception as e:
                st.error(f"Erro Geral: {e}")
