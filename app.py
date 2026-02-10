import streamlit as st
import convertapi
import os
import tempfile
import traceback
import io
import time
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

st.set_page_config(page_title="Scanner Sequencial (Word -> PDF)", layout="centered")

# --- 1. CONFIGURAÇÃO ---
def configurar_apis():
    if "convertapi" not in st.secrets or "secret" not in st.secrets["convertapi"]:
        st.error("❌ ERRO: Falta [convertapi] nos Secrets.")
        return False
    chave = st.secrets["convertapi"]["secret"]
    convertapi.api_secret = chave
    convertapi.api_credentials = chave 
    return True

# --- 2. PASSO 1: CONVERTER IMAGEM PARA WORD ---
def passo_1_criar_word(arquivo_upload):
    try:
        nome = arquivo_upload.name
        ext = os.path.splitext(nome)[1].lower() or ".jpg"

        # Salva temporário
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as t_in:
            t_in.write(arquivo_upload.getvalue())
            input_path = t_in.name

        # Parâmetros de Limpeza e Leitura
        parametros = {
            'File': input_path,
            'Ocr': 'true',
            'OcrLanguage': 'pt',
            'ImagePreprocessing': 'true',
            'RemoveNoise': 'true',
            'StoreFile': 'true'
        }

        # Chama a API para criar DOCX
        result = convertapi.convert('docx', parametros)
        
        # Baixa o Word
        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as t_out:
            result.save_files(t_out.name)
            output_word_path = t_out.name
            
        # Lê para a memória
        with open(output_word_path, 'rb') as f:
            word_bytes = f.read()

        # Limpa o arquivo de entrada
        if os.path.exists(input_path): os.remove(input_path)
        if os.path.exists(output_word_path): os.remove(output_word_path)

        return io.BytesIO(word_bytes)

    except Exception as e:
        st.error(f"Erro no Passo 1 (Word): {e}")
        return None

# --- 3. PASSO 2: CONVERTER WORD PARA PDF ---
def passo_2_criar_pdf(word_bytesio, nome_original):
    try:
        # Salva o Word que veio do Passo 1 num arquivo temporário
        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as t_word:
            t_word.write(word_bytesio.getvalue())
            word_path = t_word.name

        # Converte Word -> PDF (Rápido e Seguro)
        result = convertapi.convert('pdf', {
            'File': word_path,
            'PdfA': 'true',  # PDF/A (Arquivo Seguro)
            'PdfVersion': '1.7',
            'StoreFile': 'true'
        })

        # Baixa o PDF
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as t_pdf:
            result.save_files(t_pdf.name)
            output_pdf_path = t_pdf.name

        with open(output_pdf_path, 'rb') as f:
            pdf_bytes = f.read()

        # Limpa
        if os.path.exists(word_path): os.remove(word_path)
        if os.path.exists(output_pdf_path): os.remove(output_pdf_path)

        return io.BytesIO(pdf_bytes)

    except Exception as e:
        st.error(f"Erro no Passo 2 (PDF): {e}")
        return None

# --- 4. GOOGLE DRIVE ---
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

# --- 5. TELA PRINCIPAL ---
st.title("🔄 Scanner Sequencial (Word -> PDF)")

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
        
        st.info("Fluxo: Imagem -> Word (OCR) -> PDF Final.")
        
        files = st.file_uploader("Documentos", accept_multiple_files=True)
        
        if files and st.button("Executar Conversão"):
            service = get_drive_service()
            
            # Trava de Segurança
            if "COLOQUE" in FOLDER_ID_RAIZ:
                st.error("🛑 Erro: ID da pasta não configurado na linha 134.")
                st.stop()

            # Busca Pasta
            try:
                q = f"name = '{st.session_state['cpf_atual']}' and '{FOLDER_ID_RAIZ}' in parents and trashed=false"
                res = service.files().list(q=q).execute().get('files', [])
                if res: folder_id = res[0]['id']
                else: folder_id = service.files().create(body={'name': st.session_state['cpf_atual'], 'parents': [FOLDER_ID_RAIZ], 'mimeType': 'application/vnd.google-apps.folder'}).execute()['id']
                
                bar = st.progress(0)
                status_box = st.empty()
                
                for i, f in enumerate(files):
                    # --- FASE 1: CRIA O WORD ---
                    status_box.markdown(f"**Fase 1/2:** Criando texto editável (Word) para `{f.name}`...")
                    word_temp = passo_1_criar_word(f)
                    
                    if word_temp:
                        # --- FASE 2: CRIA O PDF ---
                        status_box.markdown(f"**Fase 2/2:** Gerando PDF final para `{f.name}`...")
                        time.sleep(1) # Pausa dramática para não travar API
                        
                        pdf_final = passo_2_criar_pdf(word_temp, f.name)
                        
                        if pdf_final:
                            nome_final = f.name.rsplit('.', 1)[0] + ".pdf"
                            status_box.markdown(f"Enviando `{nome_final}` para o Drive...")
                            upload_drive(service, pdf_final, nome_final, folder_id, 'application/pdf')
                        else:
                            st.warning(f"Falha na Fase 2 (PDF).")
                    else:
                        st.warning(f"Falha na Fase 1 (Word) para {f.name}.")
                        upload_drive(service, f, f.name, folder_id, f.type)
                    
                    bar.progress((i+1)/len(files))
                
                status_box.text("Processo Finalizado!")
                st.balloons()
                st.success("✅ Todos os arquivos foram processados e salvos como PDF!")
                
            except Exception as e:
                st.error(f"Erro Geral: {e}")
