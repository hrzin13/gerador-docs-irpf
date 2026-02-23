import streamlit as st
import streamlit.components.v1 as components

# Configuração básica da página no Streamlit
st.set_page_config(page_title="Surpresa", page_icon="❤️", layout="centered")

# Todo o código HTML/CSS guardado como um texto (string)
html_surpresa = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Para Minha Futura Namorada ❤️</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@700&display=swap');
        
        body {
            background-color: #ffe4e1;
            font-family: 'Nunito', sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
            overflow: hidden; /* Evita barras de rolagem duplas */
        }
        .cartao {
            background-color: white;
            padding: 40px;
            border-radius: 25px;
            box-shadow: 0 10px 25px rgba(255, 105, 180, 0.4);
            text-align: center;
            max-width: 90%;
            border: 4px dashed #ff69b4;
        }
        h1 {
            color: #ff1493;
            margin-bottom: 10px;
            font-size: 24px;
        }
        p {
            color: #ff69b4;
            font-size: 18px;
            line-height: 1.5;
        }
        .imagem-hello-kitty {
            width: 150px;
            margin-bottom: 15px;
            animation: float 3s ease-in-out infinite;
        }
        
        @keyframes float {
            0% { transform: translateY(0px); }
            50% { transform: translateY(-10px); }
            100% { transform: translateY(0px); }
        }
        
        .coracao {
            color: #ff1493;
            font-size: 24px;
        }
    </style>
</head>
<body>
    <div class="cartao">
        <img src="https://upload.wikimedia.org/wikipedia/en/0/05/Hello_kitty_character_portrait.png" alt="Hello Kitty" class="imagem-hello-kitty">
        <h1>Para a mulher mais linda!</h1>
        <p>Você é ainda mais perfeita e fofa que a Hello Kitty. Fiz essa página especialmente para te arrancar um sorriso hoje, minha futura namorada! <span class="coracao">❤️</span></p>
    </div>
</body>
</html>
"""

# Renderiza o HTML no Streamlit com uma altura fixa para caber na tela do celular
components.html(html_surpresa, height=700)
