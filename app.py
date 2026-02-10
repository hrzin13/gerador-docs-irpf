import streamlit as st
import convertapi
import os
import tempfile
import traceback
import io
from PIL import Image
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

st.set_page_config(page_title="Scanner IRPF Ultimate", layout="centered")

# --- 1. CONFIGURAÇÃO (Blindada) ---
def configurar_apis():
    # 1. Checa ConvertAPI
    if "convertapi" not in st.secrets or "secret" not in st.secrets["convertapi"]:
        st.error("❌ Erro nos Secrets: Falta [convertapi] ou a chave 'secret'.")
        return False
    
    # Configura a senha (Força bruta para garantir)
    chave = st.secrets["convertapi"]["secret"]
    convertapi.api_secret = chave
    convertapi.api_credentials = chave 
    return True

# --- 2. PASSO A PASSO: FOTO -> PDF A4 -> PDF OCR ---
def processar_documento_completo(arquivo_upload):
    if not convertapi.api_secret:
        st.error("Sem senha da API.")
        return None

    temp_filenames = [] # Lista para apagar arquivos depois
    try:
        # --- ETAPA 1: CONVERSÃO LOCAL (FOTO -> PDF A4) ---
        # Isso garante que a dimensão fique perfeita (A4) sem gastar crédito
        img = Image.open(arquivo_upload)
        if img.mode != 'RGB': img = img.convert('RGB')
        
        # Cria folha A4 Branca (300 DPI)
        a4_w, a4_h = 2480, 3508
        canvas = Image.new('RGB', (a4_w, a4_h), (255, 255, 255))
        
        # Redimensiona imagem para caber na folha
        img.thumbnail((a4_w - 200, a4_h - 200), Image.Resampling.LANCZOS)
        
        # Centraliza
        x = (a4_w - img.width) // 2
        y = (a4_h - img.height) // 2
        canvas.paste(img, (x, y))
        
        # Salva esse PDF "mudo" (sem texto) temporariamente
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_local:
            canvas.save(tmp_local.name, "PDF", resolution=300)
            pdf_local_path = tmp_local.name
            temp_filenames.append(pdf_local_path)

        # --- ETAPA 2: NUVEM (PDF MUDO -> PDF FALANTE/OCR) ---
        # Agora mandamos o PDF pronto pro ConvertAPI só colocar o texto
        
        result = convertapi.convert('pdf', {
            'File': pdf_local_path,
            'Ocr': 'true',            # Liga o leitor
            'OcrLanguage': 'pt',      # <--- O SEGREDO! (Português)
            'OcrMode': 'always',      # Obriga a ler tudo
            'StoreFile': 'true'
        })
        
        # Baixa o PDF final
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_final:
            result.save_files(tmp_final.name)
            pdf_final_path = tmp_final.name
            temp_filenames.append(pdf_final_path)
            
        with open(pdf_final_path, 'rb') as f:
            pdf_bytes = f.read()
            
        return io.BytesIO(pdf_bytes)

    except Exception as e:
        st.error(f"Erro no processamento: {e}")
        st.write(traceback.format_exc())
        return None
    finally:
        # Limpa a sujeira do disco
        for f in temp_filenames:
            if os.path.exists(f): os.remove(f)

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
st.title("📄 Scanner IRPF (OCR PT-BR)")
apis_ok = configurar_apis()

# SEU ID DA PASTA AQUI
FOLDER_ID_RAIZ = "COLOQUE_SEU_ID_AQUI" 

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
        
        if files and st.button("Processar"):
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
                    status.text(f"Convertendo {f.name}...")
                    
                    # Se for imagem -> Faz o Processo Completo (Local + Nuvem)
                    if f.type.startswith('image/'):
                        pdf_ocr = processar_documento_completo(f)
                        if pdf_ocr:
                            nome = f.name.rsplit('.', 1)[0] + ".pdf"
                            upload_drive(service, pdf_ocr, nome, folder_id, 'application/pdf')
                        else:
                            st.warning(f"Falha na conversão de {f.name}. Enviando original.")
                            upload_drive(service, f, f.name, folder_id, f.type)
                    
                    # Se já for PDF -> Manda direto (ou poderia mandar pro OCR também se quisesse)
                    else:
                        upload_drive(service, f, f.name, folder_id, f.type)
                    
                    bar.progress((i+1)/len(files))
                
                status.text("Sucesso!")
                st.balloons()
                st.success("Arquivos processados e salvos!")
                
            except Exception as e:
                st.error(f"Erro Geral: {e}")
