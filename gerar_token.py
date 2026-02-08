from google_auth_oauthlib.flow import InstalledAppFlow

# Escopos necessários
SCOPES = ['https://www.googleapis.com/auth/drive.file']

def gerar_novo_token():
    print("--- GERADOR DE TOKEN (MODO CODESPACES) ---")
    
    # 1. Pede os dados (Você pega lá no Google Cloud ou nos seus segredos antigos)
    client_id = input("Cole seu CLIENT ID aqui e dê Enter: ").strip()
    client_secret = input("Cole seu CLIENT SECRET aqui e dê Enter: ").strip()

    # 2. Configura o fluxo
    flow = InstalledAppFlow.from_client_config(
        {
            "installed": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["http://localhost:8080/"]
            }
        },
        SCOPES
    )

    # 3. Gera o Link
    print("\n👇 CLIQUE NO LINK ABAIXO PARA AUTORIZAR 👇")
    # O browser não abre sozinho no codespaces, então usamos open_browser=False
    creds = flow.run_local_server(port=8080, open_browser=False)

    print("\n" + "="*50)
    print("✅ SUCESSO! Copie o Refresh Token abaixo:")
    print("="*50)
    print(creds.refresh_token)
    print("="*50)

if __name__ == "__main__":
    gerar_novo_token()
