import streamlit as st
import convertapi
import os
import tempfile
import io
from PIL import Image # Biblioteca de imagem do Python
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

st.set_page_config(page_title="Scanner Universal (Tudo vira PDF)", layout="centered")

# --- 1. CONFIGURAÇÃO ---
def configurar_apis():
    if "convertapi" not in st.secrets or "secret" not in st.secrets["convertapi"]:
        st.error("❌ ERRO: Falta [convertapi] nos Secrets.")
        return False
    chave = st.secrets["convertapi"]["secret"]
    convertapi.api_secret = chave
    convertapi.api_credentials = chave 
    return True

# --- 2. PASSO 1: PADRONIZAR (FOTO -> PDF MUDO) ---
# Essa função roda NO SEU SERVIDOR (Não gasta crédito, não falha)
def transformar_foto_em_pdf_local(arquivo_upload):
    try:
        image = Image.open(arquivo_upload)
        
        # Converte para RGB (Evita erro com PNG transparente)
        if image.mode != 'RGB':
            image = image.convert('RGB')

        # Cria uma folha A4 Branca em memória
        # A4 em 72 DPI = 595 x 842 pixels (Padrão PDF)
        # Vamos fazer um pouco maior para garantir qualidade
        a4_width, a4_height = 1240, 1754 
        canvas = Image.new('RGB', (a4_width, a4_height), (255, 255, 255))
        
        # Redimensiona a imagem para caber na folha (mantendo proporção)
        image.thumbnail((a4_width - 100, a4_height - 100), Image.Resampling.LANCZOS)
        
        # Centraliza
        x = (a4_width - image.width) // 2
        y = (a4_height - image.height) // 2
        canvas.paste(image, (x, y))
        
        # Salva como PDF em memória
        pdf_bytes = io.BytesIO()
        canvas.save(pdf_bytes, format='PDF', resolution=150)
        pdf_bytes.seek(0)
        
        return pdf_bytes

    except Exception as e:
        st.error(f"Erro ao criar PDF local: {e}")
        return None

# --- 3. PASSO 2: A MÁGICA (PDF MUDO -> PDF PESQUISÁVEL) ---
# Agora mandamos pro site o arquivo que JÁ É PDF. Ele só faz o OCR.
def aplicar_ocr_na_nuvem(arquivo_pdf_bytes, nome_original):
    try:
        # Salva o PDF mudo temporariamente
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as t_in:
            t_in.write(arquivo_pdf_bytes.getvalue())
            input_path = t_in.name

        # Manda para a API
        # Como já é PDF, o site usa o motor de OCR de PDF (que você disse que funciona!)
        parametros = {
            'File': input_path,
            'Ocr': 'true',
            'OcrLanguage': 'pt',     # Português
            'PdfVersion': '1.7',
            'StoreFile': 'true'      # Devolve o arquivo
        }

        result = convertapi.convert('pdf', parametros)
        
        # Baixa o PDF pronto
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as t_out:
            result.save_files(t_out.name)
            output_path = t_out.name
            
        with open(output_path, 'rb') as f:
            final_bytes = f.read()

        # Limpa
        if os.path.exists(input_path): os.remove(input_path)
        if os.path.exists(output_path): os.remove(output_path)

        return io.BytesIO(final_bytes)

    except Exception as e:
        st.error(f"Erro na API: {e}")
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

# --- 5. TELA ---
st.title("📲 Scanner Universal (JPG vira PDF)")

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
        
        st.info("ℹ️ Estratégia: O sistema converte FOTO em PDF internamente, e depois manda para o OCR.")
        
        files = st.file_uploader("Documentos (Fotos ou PDF)", accept_multiple_files=True)
        
        if files and st.button("Processar Documentos"):
            service = get_drive_service()
            
            # Trava de segurança
            if "COLOQUE" in FOLDER_ID_RAIZ:
                st.error("🛑 ID da pasta não configurado na linha 140.")
                st.stop()

            # Busca Pasta
            try:
                q = f"name = '{st.session_state['cpf_atual']}' and '{FOLDER_ID_RAIZ}' in parents and trashed=false"
                res = service.files().list(q=q).execute().get('files', [])
                if res: folder_id = res[0]['id']
                else: folder_id = service.files().create(body={'name': st.session_state['cpf_atual'], 'parents': [FOLDER_ID_RAIZ], 'mimeType': 'application/vnd.google-apps.folder'}).execute()['id']
                
                bar = st.progress(0)
                status = st.empty()
                
                for i, f in enumerate(files):
                    status.text(f"Analisando: {f.name}...")
                    
                    arquivo_para_enviar = None
                    
                    # CASO 1: É UMA FOTO (JPG/PNG)?
                    if f.type.startswith('image/'):
                        status.text(f"Passo 1: Transformando foto {f.name} em PDF (Local)...")
                        # Transforma em PDF aqui mesmo no Python
                        arquivo_para_enviar = transformar_foto_em_pdf_local(f)
                    
                    # CASO 2: JÁ É PDF?
                    else:
                        status.text(f"Passo 1: {f.name} já é PDF. Preparando...")
                        arquivo_para_enviar = f
                    
                    # ENVIAR PARA API (OCR)
                    if arquivo_para_enviar:
                        status.text(f"Passo 2: Aplicando OCR na nuvem em {f.name}...")
                        pdf_final = aplicar_ocr_na_nuvem(arquivo_para_enviar, f.name)
                        
                        if pdf_final:
                            nome_final = f.name.rsplit('.', 1)[0] + ".pdf"
                            upload_drive(service, pdf_final, nome_final, folder_id, 'application/pdf')
                        else:
                            st.warning(f"Falha no OCR de {f.name}. Salvando original.")
                            upload_drive(service, f, f.name, folder_id, f.type)
                    
                    bar.progress((i+1)/len(files))
                
                status.text("Concluído!")
                st.balloons()
                st.success("✅ Todos os arquivos agora são PDFs Pesquisáveis!")
                
            except Exception as e:
                st.error(f"Erro Geral: {e}")
