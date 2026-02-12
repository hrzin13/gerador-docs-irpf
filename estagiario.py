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

# --- CONFIGURAÇÕES ---
# ⚠️ CONFIRA SEU ID AQUI PELA ÚLTIMA VEZ
FOLDER_ID_RAIZ = "1hxtNpuLtMiwfahaBRQcKrH6w_2cN_YFQ" 

CEREBRO_DO_ROBO = {
    "1. Despesas Médicas": ["unimed", "hospital", "clinica", "medico", "dentista"],
    "2. Educação": ["escola", "faculdade", "universidade", "colegio", "ensino"],
    "3. Rendimentos": ["informe de rendimentos", "holerite", "salario"],
    "4. Bancos e Finanças": ["extrato", "banco", "itau", "nubank", "caixa"],
    "5. Impostos Pagos": ["darf", "das", "receita federal"],
    "6. Veículos": ["ipva", "licenciamento", "detran"],
    "7. Imóveis": ["iptu", "aluguel", "condominio"]
}

# --- FUNÇÕES ---

def get_drive_service():
    try:
        creds = service_account.Credentials.from_service_account_file(
            'service_account.json', 
            scopes=['https://www.googleapis.com/auth/drive']
        )
        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        return None, str(e) # Retorna o erro pra gente ver

def ocr_google_drive(service, arquivo_bytes, nome_arquivo):
    try:
        meta = {
            'name': nome_arquivo, 
            'mimeType': 'application/vnd.google-apps.document',
            'parents': [FOLDER_ID_RAIZ]
        }
        media = MediaIoBaseUpload(arquivo_bytes, mimetype='image/jpeg', resumable=True)
        arquivo_criado = service.files().create(body=meta, media_body=media, fields='id').execute()
        file_id = arquivo_criado.get('id')

        pdf_content = service.files().export(fileId=file_id, mimeType='application/pdf').execute()
        service.files().delete(fileId=file_id).execute()
        
        return io.BytesIO(pdf_content), None # Sucesso (PDF, Sem Erro)
    except Exception as e:
        return None, str(e) # Falha (Nada, Texto do Erro)

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
        return "Geral (Não Identificado)"
    except: return "Erro Leitura"

def salvar_drive(service, pdf_bytes, nome_arq, nome_pasta):
    try:
        q = f"name = '{nome_pasta}' and '{FOLDER_ID_RAIZ}' in parents and trashed=false"
        res = service.files().list(q=q).execute().get('files', [])
        if not res:
            meta = {'name': nome_pasta, 'parents': [FOLDER_ID_RAIZ], 'mimeType': 'application/vnd.google-apps.folder'}
            id_destino = service.files().create(body=meta).execute()['id']
        else: id_destino = res[0]['id']
        
        meta_arq = {'name': nome_arq, 'parents': [id_destino]}
        media = MediaIoBaseUpload(pdf_bytes, mimetype='application/pdf')
        service.files().create(body=meta_arq, media_body=media).execute()
        return True, None
    except Exception as e:
        return False, str(e)

# --- ROTAS ---
@app.route("/bot", methods=['POST'])
def bot():
    msg = request.values.get('Body', '')
    num_media = request.values.get('NumMedia', '0')
    tipo = request.values.get('MediaContentType0', '') 
    
    resp = MessagingResponse()
    
    if int(num_media) > 0:
        url = request.values.get('MediaUrl0')
        
        # DEBUG: Verifica se baixou a imagem mesmo
        r = requests.get(url)
        if r.status_code != 200:
            resp.message(f"❌ Erro ao baixar imagem do WhatsApp. Código: {r.status_code}")
            return str(resp)
            
        arquivo_original = io.BytesIO(r.content)
        
        service, erro_auth = get_drive_service() # Pega serviço E erro se houver
        
        if service:
            pdf_para_ler = None
            erro_ocr = None
            
            if "image" in tipo:
                # Tenta OCR e captura o erro exato
                pdf_para_ler, erro_ocr = ocr_google_drive(service, arquivo_original, "temp_zap_ocr")
            elif "pdf" in tipo:
                pdf_para_ler = arquivo_original
            else:
                resp.message(f"⚠️ Tipo não suportado: {tipo}")
                return str(resp)

            if pdf_para_ler:
                pasta_destino = decidir_pasta(pdf_para_ler)
                pdf_para_ler.seek(0)
                sucesso, erro_salvar = salvar_drive(service, pdf_para_ler, f"ZAP_DOC.pdf", pasta_destino)
                
                if sucesso:
                    resp.message(f"✅ Sucesso! Salvo em: *{pasta_destino}*")
                else:
                    resp.message(f"❌ Erro ao Salvar no Final: {erro_salvar}")
            else:
                # AQUI ESTÁ O SEGREDINHO: O robô vai te contar o erro
                resp.message(f"❌ Erro DETALHADO do Google: {erro_ocr}")
        else:
            resp.message(f"❌ Erro de Autenticação (Chave): {erro_auth}")
            
    else:
        resp.message(f"🤖 Oi! Mande a foto pra eu testar.")

    return str(resp)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
