"""Etapa 3: comunicação com a API TMDB usando requests (GET)."""

import asyncio
import random

import requests

from config import TMDB_TOKEN

URL_BASE = 'https://api.themoviedb.org/3'


def _consultar_api_sincrona(endereco, parametros):
    """Faz a requisição GET e transforma a resposta JSON em dicionário Python."""
    if not TMDB_TOKEN:
        raise ValueError('TMDB_TOKEN não configurado no .env')

    resposta = requests.get(
        URL_BASE + endereco,
        headers={'Authorization': f'Bearer {TMDB_TOKEN}'},
        params={'language': 'pt-BR', **parametros},
        timeout=15,
    )
    resposta.raise_for_status()  # Gera erro se a API devolver 4xx ou 5xx.
    dados = resposta.json()
    if not isinstance(dados, dict):
        raise ValueError('A TMDB devolveu uma resposta inesperada.')
    return dados


async def consultar_api(endereco, parametros):
    """Executa o requests.get em outra thread para não bloquear o Telegram."""
    return await asyncio.to_thread(_consultar_api_sincrona, endereco, parametros)


async def sortear_filme(endereco, parametros, pagina_max=1):
    """Consulta uma página existente e devolve um filme aleatório ou None.

    Correção: antes o código sorteava páginas inexistentes e retornava lista vazia.
    A TMDB limita a paginação a, no máximo, 500 páginas.
    """
    parametros = {**parametros, 'page': 1}
    dados = await consultar_api(endereco, parametros)
    filmes = dados.get('results') or []

    total_paginas = max(1, int(dados.get('total_pages') or 1))
    limite = min(total_paginas, max(1, pagina_max), 500)
    pagina = random.randint(1, limite)

    if pagina != 1:
        outros_dados = await consultar_api(endereco, {**parametros, 'page': pagina})
        outros_filmes = outros_dados.get('results') or []
        if outros_filmes:
            filmes = outros_filmes

    return random.choice(filmes) if filmes else None
