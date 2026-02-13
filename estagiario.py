from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import requests
import io
import unicodedata
from pypdf import PdfReader
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

app = Flask(__name__)

# --- CONFIGURAÇÃO ---
# ⚠️ GARANTA QUE O ID ESTÁ SEM ESPAÇOS EM BRANCO NO FINAL
FOLDER_ID_RAIZ = "1hxtNpuLtMiwfahaBRQcKrH6w_2cN_YFQ" 

CEREBRO_DO_ROBO = {
    "1. Despesas Médicas": ["unimed", "hospital", "clinica", "medico", "dentista", "saude"],
    "2. Educação": ["escola", "faculdade", "universidade", "ensino", "curso"],
    "3. Rendimentos": ["informe", "holerite", "salario", "pro-labore"],
    "4. Bancos": ["extrato", "banco", "nubank", "caixa", "santander", "comprovante"],
    "5. Impostos": ["darf", "das", "receita"],
    "6. Veículos": ["ipva", "licenciamento", "detran"],
    "7. Imóveis": ["iptu", "aluguel", "condominio"]
}

def get_drive_service():
    try:
        creds = service_account.Credentials.from_service_account_file(
            'service_account.json', 
            scopes=['https://www.googleapis.com/auth/drive']
        )
        # Imprime quem é o robô pra gente ter certeza
        print(f"🤖 LOGADO COMO: {creds.service_account_email}")
        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        print(f"❌ ERRO NA CHAVE: {str(e)}")
        return None

def ocr_google_drive(service, arquivo_bytes, nome_arquivo):
    try:
        meta = {
            'name': nome_arquivo, 
            'mimeType': 'application/vnd.google-apps.document',
            'parents': [FOLDER_ID_RAIZ]
        }
        media = MediaIoBaseUpload(arquivo_bytes, mimetype='image/jpeg', resumable=True)
        
        # O SEGREDO DO 403: supportsAllDrives=True
        arquivo_criado = service.files().create(
            body=meta, 
            media_body=media, 
            fields='id',
            supportsAllDrives=True
        ).execute()
        
        file_id = arquivo_criado.get('id')
        pdf_content = service.files().export(fileId=file_id, mimeType='application/pdf').execute()
        service.files().delete(fileId=file_id, supportsAllDrives=True).execute()
        
        return io.BytesIO(pdf_content), None
    except Exception as e:
        return None, str(e)

def normalizar_texto(texto):
    try:
        texto = texto.lower()
        return "".join([c for c in unicodedata.normalize('NFKD', texto) if not unicodedata.combining(c)])
    except: return ""

def decidir_pasta(pdf_bytes):
    try:
        reader = PdfReader(pdf_bytes)
        texto = ""
        for page in reader.pages: texto += (page.extract_text() or "") + " "
        texto_limpo = normalizar_texto(texto)
        for pasta, palavras in CEREBRO_DO_ROBO.items():
            for p in palavras:
                if normalizar_texto(p) in texto_limpo: return pasta
        return "Geral"
    except: return "Erro Leitura"

def salvar_drive(service, pdf_bytes, nome_arq, nome_pasta):
    try:
        # Busca pasta existente com suporte a drives compartilhados
        q = f"name = '{nome_pasta}' and '{FOLDER_ID_RAIZ}' in parents and trashed=false"
        res = service.files().list(
            q=q, 
            spaces='drive', 
            corpora='allDrives', 
            includeItemsFromAllDrives=True, 
            supportsAllDrives=True
        ).execute().get('files', [])
        
        if not res:
            meta = {'name': nome_pasta, 'parents': [FOLDER_ID_RAIZ], 'mimeType': 'application/vnd.google-apps.folder'}
            id_destino = service.files().create(body=meta, supportsAllDrives=True).execute()['id']
        else: 
            id_destino = res[0]['id']
        
        meta_arq = {'name': nome_arq, 'parents': [id_destino]}
        media = MediaIoBaseUpload(pdf_bytes, mimetype='application/pdf')
        service.files().create(body=meta_arq, media_body=media, supportsAllDrives=True).execute()
        return True, None
    except Exception as e:
        return False, str(e)

@app.route("/bot", methods=['POST'])
def bot():
    msg = request.values.get('Body', '')
    num_media = request.values.get('NumMedia', '0')
    tipo = request.values.get('MediaContentType0', '') 
    resp = MessagingResponse()
    
    if int(num_media) > 0:
        url = request.values.get('MediaUrl0')
        r = requests.get(url)
        
        if r.status_code == 401: # Erro do Twilio
            resp.message("🔒 Erro 401: Desative o 'HTTP Basic Auth' no Twilio.")
            return str(resp)

        service = get_drive_service()
        if not service:
            resp.message("❌ Erro grave: Não consegui ler a chave JSON no Render.")
            return str(resp)

        arquivo_original = io.BytesIO(r.content)
        pdf_para_ler = None
        erro_ocr = None

        if "image" in tipo:
            pdf_para_ler, erro_ocr = ocr_google_drive(service, arquivo_original, "temp_ocr")
        elif "pdf" in tipo:
            pdf_para_ler = arquivo_original

        if pdf_para_ler:
            pasta_destino = decidir_pasta(pdf_para_ler)
            pdf_para_ler.seek(0)
            sucesso, erro_salvar = salvar_drive(service, pdf_para_ler, f"DOC_Zap_{pasta_destino[:10]}.pdf", pasta_destino)
            
            if sucesso:
                resp.message(f"✅ Salvo na pasta: {pasta_destino}")
            else:
                resp.message(f"❌ Erro 403/Permissão ao salvar final: {erro_salvar}")
        else:
            resp.message(f"❌ Erro no OCR: {erro_ocr}")
    else:
        resp.message("🤖 Mande a foto.")

    return str(resp)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
