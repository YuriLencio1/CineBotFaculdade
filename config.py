"""Etapa 1: configurações e tokens do CineBot."""

import os
from pathlib import Path

from dotenv import load_dotenv

try:
    import truststore  # Opcional: certificados do Windows/sistema.
except ImportError:
    truststore = None

# Usa os certificados do Windows/sistema operacional nas conexões HTTPS.
if truststore is not None:
    truststore.inject_into_ssl()

# Carrega o .env da pasta do projeto, mesmo que o terminal esteja em outra pasta.
load_dotenv(Path(__file__).with_name('.env'))

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TMDB_TOKEN = os.getenv('TMDB_TOKEN')

# Cada gênero possui um ID definido pela API TMDB.
GENEROS = {
    'acao': 28, 'aventura': 12, 'animacao': 16, 'comedia': 35,
    'crime': 80, 'documentario': 99, 'drama': 18, 'familia': 10751,
    'fantasia': 14, 'historia': 36, 'terror': 27, 'musica': 10402,
    'misterio': 9648, 'romance': 10749, 'ficcao cientifica': 878,
    'suspense': 53, 'guerra': 10752, 'faroeste': 37,
}

# Nota na TMDB vai de 0 a 10; estes limites selecionam filmes bem avaliados.
NOTA_MINIMA = 8.0
VOTOS_MINIMOS = 1000
MAX_FILMES = 8
