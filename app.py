import streamlit as st
import convertapi
import os
import tempfile
import traceback
import io # Garanta que o io está importado
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

st.set_page_config(page_title="Scanner IRPF Pro", layout="centered")

# --- 1. CONFIGURAÇÃO BLINDADA ---
def configurar_apis():
    # Verifica se a seção existe
    if "convertapi" not in st.secrets:
        st.error("❌ ERRO NO SECRETS: Falta a seção [convertapi]")
        return False
        
    # Verifica se a chave 'secret' existe
    if "secret" not in st.secrets["convertapi"]:
        st.error("❌ ERRO NO SECRETS: Falta a chave 'secret' dentro de [convertapi]")
        return False

    # SEGREDO: Força a configuração nos dois lugares possíveis
    chave = st.secrets["convertapi"]["secret"]
    convertapi.api_secret = chave
    convertapi.api_credentials = chave # <--- ESSA LINHA CONSERTA O SEU ERRO
    
    return True

# O resto do código continua igual...
# (def converter_via_api...)
# (def get_drive_service...)

# --- 2. FUNÇÃO DE CONVERSÃO (Blindada) ---
def converter_via_api(arquivo_upload):
    if not convertapi.api_secret:
        st.error("Conversão cancelada: Falta a senha da API.")
        return None

    try:
        # Define a extensão (se não tiver, assume .jpg)
        ext = os.path.splitext(arquivo_upload.name)[1]
        if not ext: ext = ".jpg"

        # Salva o arquivo temporário
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as temp_input:
            temp_input.write(arquivo_upload.getvalue())
            input_path = temp_input.name

        # Manda para o ConvertAPI
        # Parâmetros ajustados para evitar erros de tipo
        result = convertapi.convert('pdf', {
            'File': input_path,
            'StoreFile': 'true',
            'Ocr': 'true',
            'ScaleProportional': 'true',
            'PageSize': 'a4'
        })
        
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
        # Mostra o erro real para a gente entender
        st.error(f"Erro detalhado na API: {e}")
        st.code(traceback.format_exc()) # Mostra o rastro do erro
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
        st.error(f"Erro ao conectar no Google: {e}")
        return None

def upload_drive(service, file_obj, name, folder_id, mime):
    try:
        meta = {'name': name, 'parents': [folder_id]}
        media = MediaIoBaseUpload(file_obj, mimetype=mime, resumable=True)
        service.files().create(body=meta, media_body=media, fields='id').execute()
        return True
    except Exception as e:
        st.error(f"Falha no upload pro Drive: {e}")
        return False

# --- 4. TELA PRINCIPAL ---
import io

st.title("🚀 Scanner Pro IRPF")

# Verifica se as chaves estão ok antes de começar
apis_ok = configurar_apis()

# SEU ID DA PASTA AQUI
FOLDER_ID_RAIZ = "1hxtNpuLtMiwfahaBRQcKrH6w_2cN_YFQ" 

if apis_ok:
    if "cpf_atual" not in st.session_state: st.session_state["cpf_atual"] = ""

    if not st.session_state["cpf_atual"]:
        st.info("👋 Bem-vindo! Identifique o cliente.")
        cpf = st.text_input("CPF do Cliente:", max_chars=14)
        if st.button("Iniciar Atendimento", use_container_width=True): 
            if len(cpf) > 5: st.session_state["cpf_atual"] = cpf; st.rerun()
    else:
        st.success(f"📂 Cliente Ativo: **{st.session_state['cpf_atual']}**")
        if st.button("Trocar Cliente", type="secondary"): st.session_state["cpf_atual"] = ""; st.rerun()
        
        st.divider()
        st.write("Selecione fotos da galeria ou documentos:")
        files = st.file_uploader("Arquivos", accept_multiple_files=True, label_visibility="collapsed")
        
        if files and st.button(f"Processar {len(files)} Arquivos 🚀", use_container_width=True):
            service = get_drive_service()
            
            if not service:
                st.error("Não consegui conectar no Google Drive.")
            else:
                # Busca pasta do CPF
                try:
                    q = f"name = '{st.session_state['cpf_atual']}' and '{FOLDER_ID_RAIZ}' in parents and trashed=false"
                    res = service.files().list(q=q).execute().get('files', [])
                    if res: folder_id = res[0]['id']
                    else: folder_id = service.files().create(body={'name': st.session_state['cpf_atual'], 'parents': [FOLDER_ID_RAIZ], 'mimeType': 'application/vnd.google-apps.folder'}).execute()['id']
                    
                    bar = st.progress(0)
                    status = st.empty()
                    
                    for i, f in enumerate(files):
                        status.text(f"Processando {i+1}/{len(files)}: {f.name}...")
                        
                        # Se for imagem -> API PRO
                        if f.type.startswith('image/'):
                            pdf_pro = converter_via_api(f)
                            if pdf_pro:
                                nome = f.name.rsplit('.', 1)[0] + ".pdf"
                                upload_drive(service, pdf_pro, nome, folder_id, 'application/pdf')
                            else:
                                st.warning(f"⚠️ {f.name} foi enviado sem conversão (falha na API).")
                                upload_drive(service, f, f.name, folder_id, f.type)
                        else:
                            # PDF ou outros -> Direto
                            upload_drive(service, f, f.name, folder_id, f.type)
                        
                        bar.progress((i+1)/len(files))
                    
                    status.text("Finalizado!")
                    st.balloons()
                    st.success("✅ Todos os arquivos foram salvos na pasta do cliente!")
                    
                except Exception as e:
                    st.error(f"Erro geral: {e}")
