import streamlit as st
import io
import time
from pypdf import PdfReader # Biblioteca para ler o texto do PDF
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

st.set_page_config(page_title="Robô Arquivista IRPF", layout="centered")

# --- 1. O CÉREBRO DO ROBÔ (VOCÊ TREINA AQUI) ---
# Formato: "Nome da Pasta": ["palavra1", "palavra2", "palavra3"]
CEREBRO_DO_ROBO = {
    "1. Despesas Médicas": ["unimed", "hospital", "clinica", "medico", "médico", "dentista", "odontologia", "exame", "laboratorio", "saude", "psicologo", "fonoaudiologo"],
    "2. Educação": ["escola", "faculdade", "universidade", "colegio", "colégio", "ensino", "educacao", "mensalidade", "curso", "pos-graduacao"],
    "3. Rendimentos": ["informe de rendimentos", "comprovante de rendimentos", "holerite", "salario", "salário", "pro-labore", "dirf"],
    "4. Bancos e Finanças": ["extrato", "banco", "itaú", "itau", "bradesco", "nubank", "inter", "caixa", "santander", "financiamento", "consorcio"],
    "5. Impostos Pagos": ["darf", "das", "simples nacional", "receita federal", "guia", "tributo"],
    "6. Veículos": ["ipva", "licenciamento", "detran", "veiculo", "carro", "moto"],
    "7. Imóveis": ["iptu", "aluguel", "condominio", "imovel", "escritura"]
}

# --- 2. CONEXÃO GOOGLE ---
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

# --- 3. GOOGLE OCR (Imagem -> PDF Pesquisável) ---
def ocr_pelo_google(service, arquivo_upload, folder_temp_id):
    try:
        # Sobe como DOC para forçar leitura
        meta = {'name': "temp_ocr", 'mimeType': 'application/vnd.google-apps.document', 'parents': [folder_temp_id]}
        media = MediaIoBaseUpload(arquivo_upload, mimetype=arquivo_upload.type, resumable=True)
        file_doc = service.files().create(body=meta, media_body=media, fields='id').execute()
        doc_id = file_doc.get('id')
        
        # Baixa como PDF
        pdf_content = service.files().export(fileId=doc_id, mimeType='application/pdf').execute()
        
        # Apaga o temporário
        service.files().delete(fileId=doc_id).execute()
        
        return io.BytesIO(pdf_content)
    except Exception as e:
        st.error(f"Erro no OCR: {e}")
        return None

# --- 4. A INTELIGÊNCIA (Lê Texto -> Decide Pasta) ---
def decidir_pasta(pdf_bytes):
    try:
        # Lê o texto do PDF
        reader = PdfReader(pdf_bytes)
        texto_completo = ""
        for page in reader.pages:
            texto_completo += page.extract_text() or ""
        
        texto_completo = texto_completo.lower() # Deixa tudo minúsculo pra facilitar
        
        # Procura palavras-chave
        for pasta, palavras_chave in CEREBRO_DO_ROBO.items():
            for palavra in palavras_chave:
                if palavra in texto_completo:
                    return pasta, palavra # Achou! Retorna o nome da pasta e a palavra que denunciou
        
        return "Geral (Não Identificado)", None # Não achou nada
    except Exception as e:
        return "Geral (Erro Leitura)", None

# --- 5. O ARQUIVISTA (Cria Pasta se precisar -> Salva) ---
def salvar_na_pasta_certa(service, pdf_bytes, nome_arquivo, nome_pasta, id_cliente):
    try:
        # 1. Procura se a pasta já existe dentro da pasta do cliente
        q = f"name = '{nome_pasta}' and '{id_cliente}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed=false"
        results = service.files().list(q=q, fields="files(id)").execute()
        pastas = results.get('files', [])
        
        if not pastas:
            # Se não existe, cria a pasta
            meta_pasta = {
                'name': nome_pasta,
                'parents': [id_cliente],
                'mimeType': 'application/vnd.google-apps.folder'
            }
            pasta_criada = service.files().create(body=meta_pasta, fields='id').execute()
            id_destino = pasta_criada.get('id')
            st.toast(f"📂 Pasta '{nome_pasta}' criada automaticamente!")
        else:
            id_destino = pastas[0]['id']
            
        # 2. Salva o arquivo lá dentro
        meta_arquivo = {'name': nome_arquivo, 'parents': [id_destino]}
        media = MediaIoBaseUpload(pdf_bytes, mimetype='application/pdf', resumable=True)
        service.files().create(body=meta_arquivo, media_body=media, fields='id').execute()
        return True
        
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")
        return False

# --- 6. TELA DO SISTEMA ---
st.title("🤖 Robô Arquivista (Automático)")

# ⚠️⚠️⚠️ SEU ID DA PASTA RAIZ AQUI ⚠️⚠️⚠️
FOLDER_ID_RAIZ = "1hxtNpuLtMiwfahaBRQcKrH6w_2cN_YFQ" 

service = get_drive_service()

if service:
    if "cpf_atual" not in st.session_state: st.session_state["cpf_atual"] = ""

    if not st.session_state["cpf_atual"]:
        cpf = st.text_input("CPF ou Nome do Cliente:")
        if st.button("Acessar Pasta do Cliente"): 
            if len(cpf) > 3: st.session_state["cpf_atual"] = cpf; st.rerun()
    else:
        st.success(f"🗂️ Trabalhando para: **{st.session_state['cpf_atual']}**")
        if st.button("Mudar de Cliente"): st.session_state["cpf_atual"] = ""; st.rerun()
        
        st.divider()
        st.info("Envie FOTOS ou PDFs. Eu vou ler, identificar o assunto e criar a pasta certa.")
        
        files = st.file_uploader("Solte os documentos aqui:", accept_multiple_files=True)
        
        if files and st.button("Processar e Arquivar"):
            
            if "COLOQUE" in FOLDER_ID_RAIZ:
                st.error("🛑 Configure o ID da Pasta Raiz no código!")
                st.stop()

            # 1. Pega/Cria a pasta do Cliente
            try:
                q = f"name = '{st.session_state['cpf_atual']}' and '{FOLDER_ID_RAIZ}' in parents and trashed=false"
                res = service.files().list(q=q).execute().get('files', [])
                if res: id_pasta_cliente = res[0]['id']
                else: id_pasta_cliente = service.files().create(body={'name': st.session_state['cpf_atual'], 'parents': [FOLDER_ID_RAIZ], 'mimeType': 'application/vnd.google-apps.folder'}).execute()['id']
                
                bar = st.progress(0)
                log = st.empty()
                
                for i, f in enumerate(files):
                    log.markdown(f"**Analisando:** `{f.name}`...")
                    
                    # A. OCR (Google lê)
                    pdf_pronto = ocr_pelo_google(service, f, id_pasta_cliente)
                    
                    if pdf_pronto:
                        # B. CÉREBRO (Identifica do que se trata)
                        nome_pasta_destino, palavra_encontrada = decidir_pasta(pdf_pronto)
                        
                        if palavra_encontrada:
                            log.markdown(f"✅ Identifiquei **'{palavra_encontrada}'**. Classificando em: **{nome_pasta_destino}**")
                        else:
                            log.warning(f"❓ Não identifiquei palavras-chave. Vai para: **{nome_pasta_destino}**")
                        
                        # C. ARQUIVISTA (Salva na pasta certa)
                        nome_final = f.name.rsplit('.', 1)[0] + ".pdf"
                        pdf_pronto.seek(0) # Reseta o ponteiro do arquivo
                        salvar_na_pasta_certa(service, pdf_pronto, nome_final, nome_pasta_destino, id_pasta_cliente)
                        
                    else:
                        st.error(f"Falha ao ler {f.name}")
                    
                    bar.progress((i+1)/len(files))
                
                log.success("✅ Todos os documentos foram lidos, classificados e arquivados!")
                st.balloons()
                
            except Exception as e:
                st.error(f"Erro Geral: {e}")
