# CineBot — Versão simples

Bot do Telegram desenvolvido em Python para pesquisar e recomendar filmes com a API TMDB.

## Comandos
- `/start` ou `/ajuda`: mostra as opções
- `/buscar Interestelar`: pesquisa filme pelo nome
- `/acao`, `/terror` e `/comedia`: recomendam filmes por gênero

## Como executar
1. Crie seu bot com o @BotFather e obtenha o token de leitura da API em https://www.themoviedb.org/settings/api
2. Crie o ambiente virtual: `python -m venv .venv`
3. Instale as dependências: `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`
4. Copie `.env.example` para `.env`, preenchendo os tokens reais **somente no `.env`**.
5. Rode: `.\.venv\Scripts\python.exe bot.py`

## Como funciona
O bot recebe comandos por meio da biblioteca `python-telegram-bot`. A função `consultar_api()` utiliza `requests.get()` para consultar endpoints `/search/movie` e `/discover/movie` do TMDB, processa a resposta JSON e devolve título, nota e sinopse ao Telegram.

> Projeto didático: para manter o código curto, as requisições `requests.get()` são síncronas dentro dos comandos assíncronos. Isso atende à demonstração educacional, mas não é ideal para alto volume de usuários.

API: https://developer.themoviedb.org/
