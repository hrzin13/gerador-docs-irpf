import streamlit as st
import io
import unicodedata
from pypdf import PdfReader
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

st.set_page_config(page_title="Robô Arquivista (Raio-X)", layout="centered")

# --- 1. O CÉREBRO DO ROBÔ (PALAVRAS SEM ACENTO E MINÚSCULAS) ---
# Dica: Coloque as palavras aqui sempre minúsculas e sem acento!
CEREBRO_DO_ROBO = {
    "1. Despesas Médicas": ["unimed", "hospital", "clinica", "medico", "dentista", "odontologia", "exame", "laboratorio", "saude", "psicologo", "fonoaudiologo"],
    "2. Educação": ["escola", "faculdade", "universidade", "colegio", "ensino", "educacao", "mensalidade", "curso", "pos-graduacao"],
    "3. Rendimentos": ["extrato", "banco", "itau", "bradesco", "nubank", "inter", "caixa", "santander", "financiamento", "consorcio", "comprovante de pagamento", "informe de rendimentos", "comprovante de rendimentos", "holerite", "salario", "pro-labore", "dirf"],
    "5. Impostos Pagos": ["darf", "das", "simples nacional", "receita federal", "guia", "tributo"],
    "6. Veículos": ["ipva", "licenciamento", "detran", "veiculo", "carro", "moto"],
    "7. Imóveis": ["iptu", "aluguel", "condominio", "imovel", "escritura"]
}

# --- 2. FUNÇÃO EXTRA: REMOVER ACENTOS ---
def normalizar_texto(texto):
    # Transforma "Atenção" em "atencao"
    try:
        texto = texto.lower() # Tudo minúsculo
        # Remove acentos (Mágica do Unicode)
        nfkd_form = unicodedata.normalize('NFKD', texto)
        texto_sem_acento = "".join([c for c in nfkd_form if not unicodedata.combining(c)])
        return texto_sem_acento
    except:
        return ""

# --- 3. CONEXÃO GOOGLE ---
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
        st.error(f"Erro Conexão Google: {e}")
        return None

# --- 4. GOOGLE OCR ---
def ocr_pelo_google(service, arquivo_upload, folder_temp_id):
    try:
        meta = {'name': "temp_ocr", 'mimeType': 'application/vnd.google-apps.document', 'parents': [folder_temp_id]}
        media = MediaIoBaseUpload(arquivo_upload, mimetype=arquivo_upload.type, resumable=True)
        file_doc = service.files().create(body=meta, media_body=media, fields='id').execute()
        doc_id = file_doc.get('id')
        
        pdf_content = service.files().export(fileId=doc_id, mimeType='application/pdf').execute()
        service.files().delete(fileId=doc_id).execute()
        
        return io.BytesIO(pdf_content)
    except Exception as e:
        st.error(f"Erro no OCR: {e}")
        return None

# --- 5. A INTELIGÊNCIA (AGORA LÊ TUDO E NORMALIZA) ---
def decidir_pasta(pdf_bytes):
    try:
        reader = PdfReader(pdf_bytes)
        texto_completo = ""
        
        # Lê TODAS as páginas (Página 1, 2, 3...) e junta num textão só
        for page in reader.pages:
            texto_completo += (page.extract_text() or "") + " "
        
        # Limpa o texto (Tira acento e deixa minúsculo)
        texto_limpo = normalizar_texto(texto_completo)
        
        # Procura palavras-chave
        for pasta, palavras_chave in CEREBRO_DO_ROBO.items():
            for palavra in palavras_chave:
                # Normaliza a palavra chave também pra garantir
                palavra_limpa = normalizar_texto(palavra)
                
                if palavra_limpa in texto_limpo:
                    return pasta, palavra, texto_limpo # Retorna o texto limpo pra gente ver
        
        return "Geral (Não Identificado)", None, texto_limpo
    except Exception as e:
        return "Geral (Erro Leitura)", None, ""

# --- 6. O ARQUIVISTA ---
def salvar_na_pasta_certa(service, pdf_bytes, nome_arquivo, nome_pasta, id_cliente):
    try:
        q = f"name = '{nome_pasta}' and '{id_cliente}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed=false"
        results = service.files().list(q=q, fields="files(id)").execute()
        pastas = results.get('files', [])
        
        if not pastas:
            meta_pasta = {'name': nome_pasta, 'parents': [id_cliente], 'mimeType': 'application/vnd.google-apps.folder'}
            pasta_criada = service.files().create(body=meta_pasta, fields='id').execute()
            id_destino = pasta_criada.get('id')
        else:
            id_destino = pastas[0]['id']
            
        meta_arquivo = {'name': nome_arquivo, 'parents': [id_destino]}
        media = MediaIoBaseUpload(pdf_bytes, mimetype='application/pdf', resumable=True)
        service.files().create(body=meta_arquivo, media_body=media, fields='id').execute()
        return True
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")
        return False

# --- 7. TELA ---
st.title("🤖 Robô Arquivista (Raio-X)")

# ⚠️⚠️⚠️ SEU ID DA PASTA AQUI ⚠️⚠️⚠️
FOLDER_ID_RAIZ = "1hxtNpuLtMiwfahaBRQcKrH6w_2cN_YFQ" 

service = get_drive_service()

if service:
    if "cpf_atual" not in st.session_state: st.session_state["cpf_atual"] = ""

    if not st.session_state["cpf_atual"]:
        cpf = st.text_input("Nome/CPF do Cliente:")
        if st.button("Acessar"): 
            if len(cpf) > 3: st.session_state["cpf_atual"] = cpf; st.rerun()
    else:
        st.success(f"🗂️ Cliente: **{st.session_state['cpf_atual']}**")
        if st.button("Sair"): st.session_state["cpf_atual"] = ""; st.rerun()
        
        st.info("O Robô agora lê **todas as páginas** e ignora acentos/maiúsculas.")
        
        files = st.file_uploader("Arquivos", accept_multiple_files=True)
        
        if files and st.button("Processar"):
            
            if "COLOQUE" in FOLDER_ID_RAIZ:
                st.error("🛑 ID da pasta não configurado (Linha 138).")
                st.stop()

            # Pega pasta do cliente
            try:
                q = f"name = '{st.session_state['cpf_atual']}' and '{FOLDER_ID_RAIZ}' in parents and trashed=false"
                res = service.files().list(q=q).execute().get('files', [])
                if res: id_pasta_cliente = res[0]['id']
                else: id_pasta_cliente = service.files().create(body={'name': st.session_state['cpf_atual'], 'parents': [FOLDER_ID_RAIZ], 'mimeType': 'application/vnd.google-apps.folder'}).execute()['id']
                
                bar = st.progress(0)
                
                for i, f in enumerate(files):
                    st.write(f"--- Processando: **{f.name}** ---")
                    
                    # 1. OCR
                    pdf_pronto = ocr_pelo_google(service, f, id_pasta_cliente)
                    
                    if pdf_pronto:
                        # 2. Decide Pasta (Lê tudo)
                        nome_pasta, palavra, texto_lido = decidir_pasta(pdf_pronto)
                        
                        if palavra:
                            st.success(f"✅ Classificado como: **{nome_pasta}** (Palavra: '{palavra}')")
                        else:
                            st.warning(f"⚠️ Não identificado. Indo para: **{nome_pasta}**")
                            
                        # --- RAIO X (DEBUG) ---
                        # Aqui você vê o que o robô leu!
                        with st.expander("🔍 Ver o que o robô leu (Raio-X)"):
                            st.text(texto_lido[0:1000] + "...") # Mostra os primeiros 1000 caracteres
                        
                        # 3. Salva
                        nome_final = f.name.rsplit('.', 1)[0] + ".pdf"
                        pdf_pronto.seek(0)
                        salvar_na_pasta_certa(service, pdf_pronto, nome_final, nome_pasta, id_pasta_cliente)
                    
                    bar.progress((i+1)/len(files))
                
                st.balloons()
                st.success("Concluído!")
                
            except Exception as e:
                st.error(f"Erro Geral: {e}")
