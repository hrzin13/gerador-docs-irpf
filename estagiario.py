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

# --- ⚠️ CONFIGURAÇÃO: SEU ID DA PASTA AQUI ---
FOLDER_ID_RAIZ = "1hxtNpuLtMiwfahaBRQcKrH6w_2cN_YFQ" 

# --- CÉREBRO DO ROBÔ (Categorias) ---
CEREBRO_DO_ROBO = {
    "1. Despesas Médicas": ["unimed", "hospital", "clinica", "medico", "dentista", "odontologia", "exame", "laboratorio", "saude", "psicologo", "fonoaudiologo"],
    "2. Educação": ["escola", "faculdade", "universidade", "colegio", "ensino", "educacao", "mensalidade", "curso", "pos-graduacao"],
    "3. Rendimentos": ["informe de rendimentos", "comprovante de rendimentos", "holerite", "salario", "pro-labore", "dirf"],
    "4. Bancos e Finanças": ["extrato", "banco", "itau", "bradesco", "nubank", "inter", "caixa", "santander", "financiamento", "consorcio", "comprovante de pagamento"],
    "5. Impostos Pagos": ["darf", "das", "simples nacional", "receita federal", "guia", "tributo"],
    "6. Veículos": ["ipva", "licenciamento", "detran", "veiculo", "carro", "moto"],
    "7. Imóveis": ["iptu", "aluguel", "condominio", "imovel", "escritura"]
}

# --- FUNÇÕES ---

def get_drive_service():
    """Conecta no Google Drive usando a chave secreta do Render."""
    try:
        creds = service_account.Credentials.from_service_account_file(
            'service_account.json', 
            scopes=['https://www.googleapis.com/auth/drive']
        )
        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        return None
def get_drive_service():
    # ... (código que já existe) ...
    creds = service_account.Credentials.from_service_account_file(...)
    
    # ADICIONE ISSO AQUI:
    print(f"🕵️ E-MAIL DO ROBÔ: {creds.service_account_email}")
    
    return build(...)

def ocr_google_drive(service, arquivo_bytes, nome_arquivo):
    """
    MÁGICA: Converte Foto (PNG/JPG) em PDF Pesquisável.
    1. Sobe como Google Doc (OCR acontece aqui)
    2. Baixa como PDF
    """
    try:
        # 1. Sobe para o Drive convertendo para Documento Google (Faz o OCR)
        meta = {
            'name': nome_arquivo, 
            'mimeType': 'application/vnd.google-apps.document', # Força o OCR
            'parents': [FOLDER_ID_RAIZ]
        }
        media = MediaIoBaseUpload(arquivo_bytes, mimetype='image/jpeg', resumable=True)
        arquivo_criado = service.files().create(body=meta, media_body=media, fields='id').execute()
        file_id = arquivo_criado.get('id')

        # 2. Baixa de volta como PDF (agora com texto selecionável)
        pdf_content = service.files().export(fileId=file_id, mimeType='application/pdf').execute()
        
        # 3. Limpa o arquivo temporário (Google Doc) do Drive
        service.files().delete(fileId=file_id).execute()
        
        return io.BytesIO(pdf_content), None # Sucesso
    except Exception as e:
        return None, str(e) # Erro

def normalizar_texto(texto):
    """Remove acentos e deixa tudo minúsculo."""
    try:
        texto = texto.lower()
        return "".join([c for c in unicodedata.normalize('NFKD', texto) if not unicodedata.combining(c)])
    except: return ""

def decidir_pasta(pdf_bytes):
    """Lê o PDF e decide em qual pasta guardar."""
    try:
        reader = PdfReader(pdf_bytes)
        texto = ""
        for page in reader.pages: texto += (page.extract_text() or "") + " "
        texto_limpo = normalizar_texto(texto)
        
        # Procura palavras-chave
        for pasta, palavras in CEREBRO_DO_ROBO.items():
            for p in palavras:
                if normalizar_texto(p) in texto_limpo: return pasta
        return "Geral (Não Identificado)"
    except: return "Erro Leitura"

def salvar_drive(service, pdf_bytes, nome_arq, nome_pasta):
    """Salva o arquivo final na pasta correta."""
    try:
        # Acha ou cria a pasta de destino
        q = f"name = '{nome_pasta}' and '{FOLDER_ID_RAIZ}' in parents and trashed=false"
        res = service.files().list(q=q).execute().get('files', [])
        if not res:
            meta = {'name': nome_pasta, 'parents': [FOLDER_ID_RAIZ], 'mimeType': 'application/vnd.google-apps.folder'}
            id_destino = service.files().create(body=meta).execute()['id']
        else: id_destino = res[0]['id']
        
        # Salva o arquivo
        meta_arq = {'name': nome_arq, 'parents': [id_destino]}
        media = MediaIoBaseUpload(pdf_bytes, mimetype='application/pdf')
        service.files().create(body=meta_arq, media_body=media).execute()
        return True, None
    except Exception as e:
        return False, str(e)

# --- ROTA DO WHATSAPP ---
@app.route("/bot", methods=['POST'])
def bot():
    msg = request.values.get('Body', '')
    num_media = request.values.get('NumMedia', '0')
    tipo = request.values.get('MediaContentType0', '') 
    
    resp = MessagingResponse()
    
    # SE TIVER ARQUIVO (FOTO OU PDF)
    if int(num_media) > 0:
        url = request.values.get('MediaUrl0')
        
        # Tenta baixar o arquivo do WhatsApp
        r = requests.get(url)
        
        # Se o Twilio bloquear (Erro 401), avisa o usuário
        if r.status_code == 401:
            resp.message("🔒 ERRO 401: O Twilio bloqueou a foto. Vá em Settings > General e desative o 'HTTP Basic Auth'.")
            return str(resp)
            
        arquivo_original = io.BytesIO(r.content)
        
        service = get_drive_service()
        if service:
            pdf_para_ler = None
            erro_ocr = None
            
            # --- CONVERSÃO INTELIGENTE ---
            if "image" in tipo:
                # É FOTO? Converte pra PDF com OCR
                pdf_para_ler, erro_ocr = ocr_google_drive(service, arquivo_original, "temp_ocr")
            elif "pdf" in tipo:
                # É PDF? Usa direto
                pdf_para_ler = arquivo_original
            else:
                resp.message(f"⚠️ Formato {tipo} não suportado. Mande Foto ou PDF.")
                return str(resp)

            # --- CLASSIFICAÇÃO E SALVAMENTO ---
            if pdf_para_ler:
                pasta_destino = decidir_pasta(pdf_para_ler)
                
                pdf_para_ler.seek(0) # Rebovina o arquivo
                
                # Nome do arquivo bonitinho (ex: DOC_Medicos_Zap.pdf)
                nome_final = f"DOC_{pasta_destino.split('.')[0]}_Zap.pdf"
                
                sucesso, erro_salvar = salvar_drive(service, pdf_para_ler, nome_final, pasta_destino)
                
                if sucesso:
                    resp.message(f"✅ Recebido! Converti para PDF e salvei na pasta: *{pasta_destino}*")
                else:
                    resp.message(f"❌ Erro ao Salvar: {erro_salvar}")
            else:
                resp.message(f"❌ Erro no Google OCR: {erro_ocr}")
        else:
            resp.message("❌ Erro de Autenticação (Chave do Google perdida).")
            
    # SE FOR SÓ TEXTO
    else:
        resp.message(f"🤖 Olá! Estou pronto.\nMande uma foto do documento que eu converto em PDF e arquivo pra você.")

    return str(resp)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
