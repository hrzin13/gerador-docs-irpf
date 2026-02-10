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

st.set_page_config(page_title="Scanner Blindado (Img->Word->PDF)", layout="centered")

# --- 1. CONFIGURAÇÃO ---
def configurar_apis():
    if "convertapi" not in st.secrets or "secret" not in st.secrets["convertapi"]:
        st.error("❌ ERRO: Falta o segredo do ConvertAPI.")
        return False
    
    chave = st.secrets["convertapi"]["secret"]
    convertapi.api_secret = chave
    convertapi.api_credentials = chave 
    return True

# --- 2. O PULO DO GATO: IMAGEM -> WORD -> PDF ---
def converter_salto_duplo(arquivo_upload):
    try:
        nome_arquivo = arquivo_upload.name
        extensao = os.path.splitext(nome_arquivo)[1].lower() or ".jpg"

        # Salva o arquivo original temporariamente
        with tempfile.NamedTemporaryFile(delete=False, suffix=extensao) as temp_input:
            temp_input.write(arquivo_upload.getvalue())
            input_path = temp_input.name
            
        temp_word_path = None
        output_pdf_path = None

        # --- PASSO 1: FOTO -> WORD (Gasta 1 crédito) ---
        # Aqui a gente força a criação do texto editável
        st.toast(f"Passo 1/2: Criando texto Word para {nome_arquivo}...")
        
        result_word = convertapi.convert('docx', {
            'File': input_path,
            'Ocr': 'true',
            'OcrLanguage': 'pt',
            'ImagePreprocessing': 'true', # Limpeza pesada
            'RemoveNoise': 'true',
            'ScaleImage': 'true'
        })
        
        # Salva o Word temporário
        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as temp_word:
            result_word.save_files(temp_word.name)
            temp_word_path = temp_word.name

        # --- PASSO 2: WORD -> PDF (Gasta +1 crédito) ---
        # Agora pegamos o texto garantido do Word e selamos num PDF
        st.toast(f"Passo 2/2: Gerando PDF final para {nome_arquivo}...")
        
        result_pdf = convertapi.convert('pdf', {
            'File': temp_word_path,
            'PdfVersion': '1.7', # Versão moderna
            'PdfA': 'true'       # PDF/A (Padrão de arquivo eterno)
        })

        # Baixa o PDF final
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
            result_pdf.save_files(temp_pdf.name)
            output_pdf_path = temp_pdf.name
            
        with open(output_pdf_path, 'rb') as f:
            pdf_bytes = f.read()
            
        # Limpa toda a sujeira (Original, Word temp e PDF temp)
        if os.path.exists(input_path): os.remove(input_path)
        if temp_word_path and os.path.exists(temp_word_path): os.remove(temp_word_path)
        if output_pdf_path and os.path.exists(output_pdf_path): os.remove(output_pdf_path)
        
        return io.BytesIO(pdf_bytes)

    except Exception as e:
        st.error(f"Erro no Salto Duplo: {e}")
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
st.title("🛡️ Scanner IRPF (Método Garantido)")

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
        
        st.info("ℹ️ Método Ativado: Foto -> Word -> PDF (Garante texto pesquisável).")
        
        files = st.file_uploader("Documentos", accept_multiple_files=True)
        
        if files and st.button("Converter com Segurança Máxima"):
            service = get_drive_service()
            
            # Trava de ID
            if "COLOQUE" in FOLDER_ID_RAIZ:
                st.error("🛑 Você esqueceu o ID da pasta na linha 118!")
                st.stop()

            # Pasta
            try:
                q = f"name = '{st.session_state['cpf_atual']}' and '{FOLDER_ID_RAIZ}' in parents and trashed=false"
                res = service.files().list(q=q).execute().get('files', [])
                if res: folder_id = res[0]['id']
                else: folder_id = service.files().create(body={'name': st.session_state['cpf_atual'], 'parents': [FOLDER_ID_RAIZ], 'mimeType': 'application/vnd.google-apps.folder'}).execute()['id']
                
                bar = st.progress(0)
                status = st.empty()
                
                for i, f in enumerate(files):
                    status.text(f"Processando {f.name} (Pode demorar um pouco mais)...")
                    
                    # Chama a função DUPLA
                    pdf_final = converter_salto_duplo(f)
                    
                    if pdf_final:
                        nome = f.name.rsplit('.', 1)[0] + ".pdf"
                        upload_drive(service, pdf_final, nome, folder_id, 'application/pdf')
                    else:
                        st.warning(f"Falha em {f.name}. Enviando original.")
                        upload_drive(service, f, f.name, folder_id, f.type)
                    
                    bar.progress((i+1)/len(files))
                
                status.text("Pronto!")
                st.balloons()
                st.success("✅ Documentos blindados salvos no Drive!")
                
            except Exception as e:
                st.error(f"Erro Geral: {e}")
