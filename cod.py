import requests
import speech_recognition as sr
from gtts import gTTS
import os
import re  # Para usar expressões regulares
from datetime import datetime
import urllib.parse  # Para codificar a URL corretamente
from pydub import AudioSegment  # Para ajustar a velocidade do áudio
from pydub.playback import play  # Para tocar o áudio
import time  # Para cache
# Chaves de API
API_KEY_CLIMA = '3c132e364beed135b3586dbdda65caab'  # OpenWeather
API_KEY_NEWS = '2e11e6caef1443bc9b56ce0d32ad23ef'  # NewsAPI
API_KEY_GOOGLE = 'AIzaSyAgjbiAxACG62hFl-eJIIxpWFtqQZPRXYQ'  # Google Custom Search
SEARCH_ENGINE_ID = 'b6ff778fe09c34a17'  # ID do Google Custom Search

# Cache para clima (evita consultas repetidas)
clima_cache = {}
clima_cache_ttl = 600  # Tempo de validade do cache em segundos (10 minutos)

# Função para falar o texto usando gTTS e ajustar a velocidade
def falar(texto):
    tts = gTTS(texto, lang='pt-br')
    tts.save("fala.mp3")
    
    # Carrega o áudio e ajusta a velocidade
    audio = AudioSegment.from_mp3("fala.mp3")
    audio = audio.speedup(playback_speed=1.1)  # Ajuste de velocidade
    play(audio)

# Função para confirmar a resposta reconhecida
def confirmar_fala(fala):
    falar(f"Você quis dizer {fala}? Responda sim ou não.")
    
    # Captura a confirmação apenas uma vez
    confirmacao = capturar_resposta()

    # Se a confirmação for sim, retorna True
    if "sim" in confirmacao.lower():
        return True
    # Se a confirmação for não, retorna False
    elif "não" in confirmacao.lower():
        return False
    # Se a resposta não for clara, assume que é "sim"
    else:
        falar("Não entendi, mas vou considerar que sim.")
        return True

# Função para capturar resposta de voz com ajustes de silêncio e timeout
def capturar_resposta():
    reconhecedor = sr.Recognizer()

    with sr.Microphone() as source:
        reconhecedor.adjust_for_ambient_noise(source)
        print("Estou ouvindo...")

        try:
            audio = reconhecedor.listen(source, timeout=5, phrase_time_limit=5)
            texto = reconhecedor.recognize_google(audio, language='pt-BR')
            print(f"Você disse: {texto}")
            return texto
        except sr.WaitTimeoutError:
            falar("Tempo esgotado. Tente novamente.")
            return ""
        except sr.UnknownValueError:
            falar("Desculpe, não entendi o que você disse.")
            return ""
        except sr.RequestError as e:
            falar(f"Houve um erro ao tentar reconhecer sua fala: {e}")
            return ""

# Função para escutar continuamente até detectar a palavra-chave
def escutar_palavra_chave(palavra_chave="assistente"):
    reconhecedor = sr.Recognizer()
    falar("Estou ouvindo...")

    with sr.Microphone() as source:
        reconhecedor.adjust_for_ambient_noise(source)
        while True:
            print("Aguardando a palavra-chave...")
            audio = reconhecedor.listen(source)
            try:
                # Tenta reconhecer a palavra falada
                texto = reconhecedor.recognize_google(audio, language='pt-BR').lower()
                print(f"Você disse: {texto}")
                if palavra_chave in texto:
                    falar("Como posso ajudar você?")
                    return  # Sai do loop e passa para a captura da pergunta
            except sr.UnknownValueError:
                # Se não entender a palavra, continua ouvindo
                print("Não entendi, continue falando.")
            except sr.RequestError as e:
                falar(f"Houve um erro: {e}")
                break

# Função para extrair a cidade da pergunta usando regex
def extrair_cidade(pergunta):
    # Regex para detectar uma cidade após "clima em"
    match = re.search(r'clima em ([\w\s]+)', pergunta.lower())
    if match:
        cidade = match.group(1).strip()
        print(f"Identifiquei a cidade: {cidade}")
        return cidade.capitalize()  # Retorna a cidade com a primeira letra maiúscula
    return None

# Função para extrair o tema da notícia da pergunta
def extrair_tema_noticias(pergunta):
    # Regex para detectar o tema da notícia na pergunta
    match = re.search(r'notícias sobre ([\w\s]+)', pergunta.lower())
    if match:
        tema = match.group(1).strip()
        print(f"Identifiquei o tema da notícia: {tema}")
        return tema.capitalize()
    return None

# Função para buscar clima, com cache
def obter_clima(cidade):
    # Verificar se o clima da cidade está no cache
    if cidade in clima_cache and time.time() - clima_cache[cidade]['timestamp'] < clima_cache_ttl:
        return clima_cache[cidade]['dados']
    
    url = f"http://api.openweathermap.org/data/2.5/weather?q={cidade}&appid={API_KEY_CLIMA}&units=metric&lang=pt_br"
    response = requests.get(url)

    if response.status_code == 200:
        dados = response.json()

        descricao = dados['weather'][0]['description']
        temperatura = dados['main']['temp']
        umidade = dados['main']['humidity']
        vento = dados['wind']['speed']

        if 'rain' in dados:
            chuva = dados['rain'].get('1h', 0)
            chance_chuva = f"Há previsão de {chuva} mm de chuva."
        else:
            chance_chuva = "Não há previsão de chuva nas próximas horas."

        resposta = (f"Clima em {cidade}: {descricao}, temperatura de {temperatura}°C, umidade de {umidade}%, "
                    f"velocidade do vento {vento} m/s. {chance_chuva}")
        
        # Armazenar no cache
        clima_cache[cidade] = {'dados': resposta, 'timestamp': time.time()}
        
        return resposta
    else:
        return "Desculpe, não consegui obter as informações do clima no momento."

# Função para buscar notícias com temas específicos
def buscar_noticias(tema=""):
    if not tema:
        url = f"https://newsapi.org/v2/top-headlines?country=br&apiKey={API_KEY_NEWS}"
    else:
        url = f"https://newsapi.org/v2/everything?q={tema}&language=pt&apiKey={API_KEY_NEWS}"
    
    response = requests.get(url)
    
    if response.status_code == 200:
        dados = response.json()

        noticias = []
        for item in dados.get('articles', []):
            titulo = item['title']
            descricao = item.get('description', 'Descrição não disponível')
            noticias.append(f"Título: {titulo}\nDescrição: {descricao}\n")

        if noticias:
            return "\n".join(noticias[:3])  # Retorna até 3 notícias
        else:
            return f"Não encontrei notícias específicas sobre {tema}."
    else:
        return f"Erro ao consultar a NewsAPI: {response.status_code}"

# Função para ajustar a saudação personalizada com base no horário
def saudacao_personalizada():
    hora_atual = datetime.now().hour
    if hora_atual < 12:
        return "Bom dia!"
    elif 12 <= hora_atual < 18:
        return "Boa tarde!"
    else:
        return "Boa noite!"

# Função para responder perguntas por voz
def responder_pergunta(pergunta, contexto={}):
    saudacao = saudacao_personalizada()

    if "clima" in pergunta.lower():
        # Extrair a cidade diretamente da pergunta
        cidade = extrair_cidade(pergunta)
        if not cidade:
            falar("De qual cidade você deseja saber o clima?")
            cidade = capturar_resposta()
            contexto['cidade'] = cidade
        return f"{saudacao} Aqui está a previsão do tempo para {cidade}. " + obter_clima(cidade)

    elif "notícia" in pergunta.lower() or "notícias" in pergunta.lower():
        # Extrair o tema da notícia diretamente da pergunta
        tema = extrair_tema_noticias(pergunta)
        if not tema:
            falar("Sobre qual tema você gostaria de saber notícias?")
            tema = capturar_resposta()
            contexto['tema'] = tema
        return f"Aqui estão as últimas notícias sobre {tema}: \n" + buscar_noticias(tema)

    elif "pesquise" in pergunta.lower() or "busque" in pergunta.lower():
        falar("O que você gostaria de pesquisar no Google?")
        consulta = capturar_resposta()
        return pesquisar_google(consulta)

    else:
        return pesquisar_google(pergunta)

# Função principal para capturar a pergunta por voz e responder
def capturar_audio():
    reconhecedor = sr.Recognizer()

    with sr.Microphone() as source:
        escutar_palavra_chave()  # Espera até a palavra-chave ser dita

        reconhecedor.adjust_for_ambient_noise(source)
        try:
            audio = reconhecedor.listen(source, timeout=5, phrase_time_limit=5)
            pergunta = reconhecedor.recognize_google(audio, language='pt-BR')
            print(f"Você disse: {pergunta}")

            contexto = {}  # Para armazenar dados de contexto (ex.: cidade, tema)
            # Confirmar uma única vez se o reconhecimento foi correto
            if confirmar_fala(pergunta):
                resposta = responder_pergunta(pergunta, contexto)
                print(f"Resposta: {resposta}")
                falar(resposta)
            else:
                # Se a confirmação for não, pede novamente a pergunta
                falar("Por favor, repita sua pergunta.")
                capturar_audio()

        except sr.WaitTimeoutError:
            falar("Desculpe, você demorou muito para responder.")
        except sr.UnknownValueError:
            falar("Desculpe, não entendi o que você disse.")
        except sr.RequestError as e:
            falar(f"Houve um erro ao tentar reconhecer sua fala: {e}")

# Chama a função para capturar a voz e responder
capturar_audio()
