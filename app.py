import streamlit as st
import io
import time
from pypdf import PdfReader
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

st.set_page_config(page_title="Robô Arquivista (Lê Pag 2)", layout="centered")

# --- 1. O CÉREBRO DO ROBÔ ---
CEREBRO_DO_ROBO = {
    "1. Despesas Médicas": ["unimed", "hospital", "clinica", "medico", "médico", "dentista", "odontologia", "exame", "laboratorio", "saude", "psicologo", "fonoaudiologo"],
    "2. Educação": ["escola", "faculdade", "universidade", "colegio", "colégio", "ensino", "educacao", "mensalidade", "curso", "pos-graduacao"],
    "3. Rendimentos": ["informe de rendimentos", "comprovante de rendimentos", "holerite", "salario", "salário", "pro-labore", "dirf"],
    "4. Bancos e Finanças": ["extrato", "banco", "itaú", "itau", "bradesco", "nubank", "inter", "caixa", "santander", "financiamento", "consorcio", "comprovante de pagamento"],
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

# --- 3. GOOGLE OCR (Imagem -> PDF) ---
def ocr_pelo_google(service, arquivo_upload, folder_temp_id):
    try:
        # Sobe como Google DOC
        meta = {'name': "temp_ocr", 'mimeType': 'application/vnd.google-apps.document', 'parents': [folder_temp_id]}
        media = MediaIoBaseUpload(arquivo_upload, mimetype=arquivo_upload.type, resumable=True)
        file_doc = service.files().create(body=meta, media_body=media, fields='id').execute()
        doc_id = file_doc.get('id')
        
        # Baixa como PDF
        pdf_content = service.files().export(fileId=doc_id, mimeType='application/pdf').execute()
        
        # Apaga o DOC temporário
        service.files().delete(fileId=doc_id).execute()
        
        return io.BytesIO(pdf_content)
    except Exception as e:
        st.error(f"Erro no OCR: {e}")
        return None

# --- 4. A INTELIGÊNCIA (AGORA OLHANDO A PÁGINA 2) ---
def decidir_pasta(pdf_bytes):
    try:
        reader = PdfReader(pdf_bytes)
        texto_analisado = ""
        
        # --- AQUI ESTÁ A MUDANÇA ---
        qtd_paginas = len(reader.pages)
        
        if qtd_paginas >= 2:
            # Se tiver 2 ou mais páginas, PEGA A SEGUNDA (índice 1)
            # É aqui que o Google esconde o texto do OCR
            texto_analisado = reader.pages[1].extract_text() or ""
            st.toast("📖 Lendo a Página 2 (OCR)...")
        else:
            # Se só tiver 1 página, lê a primeira mesmo (melhor que nada)
            texto_analisado = reader.pages[0].extract_text() or ""
            st.toast("⚠️ Arquivo curto: Lendo Página 1...")
            
        texto_analisado = texto_analisado.lower()
        
        # Procura palavras-chave
        for pasta, palavras_chave in CEREBRO_DO_ROBO.items():
            for palavra in palavras_chave:
                if palavra in texto_analisado:
                    return pasta, palavra 
        
        return "Geral (Não Identificado)", None
    except Exception as e:
        return "Geral (Erro Leitura)", None

# --- 5. O ARQUIVISTA ---
def salvar_na_pasta_certa(service, pdf_bytes, nome_arquivo, nome_pasta, id_cliente):
    try:
        # Verifica se pasta existe
        q = f"name = '{nome_pasta}' and '{id_cliente}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed=false"
        results = service.files().list(q=q, fields="files(id)").execute()
        pastas = results.get('files', [])
        
        if not pastas:
            # Cria pasta se não existir
            meta_pasta = {'name': nome_pasta, 'parents': [id_cliente], 'mimeType': 'application/vnd.google-apps.folder'}
            pasta_criada = service.files().create(body=meta_pasta, fields='id').execute()
            id_destino = pasta_criada.get('id')
        else:
            id_destino = pastas[0]['id']
            
        # Salva arquivo
        meta_arquivo = {'name': nome_arquivo, 'parents': [id_destino]}
        media = MediaIoBaseUpload(pdf_bytes, mimetype='application/pdf', resumable=True)
        service.files().create(body=meta_arquivo, media_body=media, fields='id').execute()
        return True
        
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")
        return False

# --- 6. TELA ---
st.title("🤖 Robô Arquivista (OCR Google)")

# ⚠️⚠️⚠️ COLOQUE SEU ID AQUI EMBAIXO ⚠️⚠️⚠️
FOLDER_ID_RAIZ = "1hxtNpuLtMiwfahaBRQcKrH6w_2cN_YFQ" 

service = get_drive_service()

if service:
    if "cpf_atual" not in st.session_state: st.session_state["cpf_atual"] = ""

    if not st.session_state["cpf_atual"]:
        cpf = st.text_input("CPF ou Nome do Cliente:")
        if st.button("Acessar Pasta"): 
            if len(cpf) > 3: st.session_state["cpf_atual"] = cpf; st.rerun()
    else:
        st.success(f"🗂️ Cliente: **{st.session_state['cpf_atual']}**")
        if st.button("Trocar"): st.session_state["cpf_atual"] = ""; st.rerun()
        
        st.info("O Robô vai ler a **Página 2** (onde fica o texto do Google) para classificar.")
        
        files = st.file_uploader("Solte os arquivos:", accept_multiple_files=True)
        
        if files and st.button("Processar"):
            
            if "COLOQUE" in FOLDER_ID_RAIZ:
                st.error("🛑 Erro: ID da Pasta Raiz não configurado.")
                st.stop()

            # Pega pasta do cliente
            try:
                q = f"name = '{st.session_state['cpf_atual']}' and '{FOLDER_ID_RAIZ}' in parents and trashed=false"
                res = service.files().list(q=q).execute().get('files', [])
                if res: id_pasta_cliente = res[0]['id']
                else: id_pasta_cliente = service.files().create(body={'name': st.session_state['cpf_atual'], 'parents': [FOLDER_ID_RAIZ], 'mimeType': 'application/vnd.google-apps.folder'}).execute()['id']
                
                bar = st.progress(0)
                log = st.empty()
                
                for i, f in enumerate(files):
                    log.markdown(f"**Lendo:** `{f.name}`...")
                    
                    # 1. Google OCR
                    pdf_pronto = ocr_pelo_google(service, f, id_pasta_cliente)
                    
                    if pdf_pronto:
                        # 2. Decide Pasta (Lendo Pág 2)
                        nome_pasta_destino, palavra = decidir_pasta(pdf_pronto)
                        
                        if palavra:
                            log.success(f"✅ Achei **'{palavra}'** em `{f.name}` -> Pasta: **{nome_pasta_destino}**")
                        else:
                            log.warning(f"⚠️ `{f.name}`: Sem palavra-chave na Pág 2 -> Pasta: **{nome_pasta_destino}**")
                        
                        # 3. Salva
                        nome_final = f.name.rsplit('.', 1)[0] + ".pdf"
                        pdf_pronto.seek(0)
                        salvar_na_pasta_certa(service, pdf_pronto, nome_final, nome_pasta_destino, id_pasta_cliente)
                    
                    bar.progress((i+1)/len(files))
                
                st.balloons()
                st.success("Processo Finalizado!")
                
            except Exception as e:
                st.error(f"Erro Geral: {e}")
