"""CineBot: pesquisa e recomenda filmes usando a API do TMDB."""


import truststore
truststore.inject_into_ssl()

import os
import random
import requests
from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder, CommandHandler

# tokens guardados no arquivo .env.
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TMDB_TOKEN = os.getenv("TMDB_TOKEN")

#gêneros usados pela API TMDB.
GENEROS = {"acao": 28, "terror": 27, "comedia": 35}


def consultar_api(endereco, parametros):
    """Faz uma requisição GET ao TMDB e devolve os dados em JSON."""
    resposta = requests.get(
        "https://api.themoviedb.org/3" + endereco,
        headers={"Authorization": f"Bearer {TMDB_TOKEN}"},
        params={"language": "pt-BR", **parametros},
        timeout=15,
    )
    resposta.raise_for_status()  # Verifica se houve erro HTTP.
    return resposta.json()       


async def mostrar_filme(update, filme):
    """Envia as informações de um filme para o Telegram."""
    if not filme:
        await update.message.reply_text("Nenhum filme encontrado.")
        return

    titulo = filme.get("title", "Sem título")
    nota = filme.get("vote_average") or 0
    sinopse = filme.get("overview") or "Sinopse indisponível."
    mensagem = f"🎬 {titulo}\n⭐ Nota: {nota:.1f}/10\n\n📝 {sinopse}"
    await update.message.reply_text(mensagem[:4000])


async def iniciar(update, context):
    """Mostra ao usuário como utilizar o bot."""
    await update.message.reply_text(
        "🎬 Bem-vindo ao CineBot!\n\n"
        "/buscar nome — pesquisar filme\n"
        "/acao — recomendar ação\n"
        "/terror — recomendar terror\n"
        "/comedia — recomendar comédia"
    )


async def buscar(update, context):
    """Pesquisa um filme pelo nome informado no Telegram."""
    if not context.args:
        await update.message.reply_text("Exemplo: /buscar Interestelar")
        return

    # Pega o nome do filme digitado pelo usuário
    try:
        nome = " ".join(context.args)
            # Chama a função que faz a requisição GET ao TMDB
        dados = consultar_api("/search/movie", {"query": nome})
            # Extrai a lista de filmes do JSON retornado
        filmes = dados.get("results", [])
            # Extrai a lista de filmes do JSON retornado
        await mostrar_filme(update, filmes[0] if filmes else None)
    except requests.RequestException:
        await update.message.reply_text("Erro ao consultar o TMDB. Tente novamente.")


async def recomendar(update, context):
    """Recomenda um filme de acordo com o comando enviado."""
    genero = update.message.text.split()[0].split("@")[0][1:]

    try:
        dados = consultar_api(
            "/discover/movie",
            {"with_genres": GENEROS[genero], "include_adult": "true"},
        )
        filmes = dados.get("results", [])
        filme = random.choice(filmes) if filmes else None
        await mostrar_filme(update, filme)
    except requests.RequestException:
        await update.message.reply_text("Erro ao consultar o TMDB. Tente novamente.")


# Inicia o bot e relaciona cada comando à sua função.
if __name__ == "__main__":
    if not TELEGRAM_TOKEN or not TMDB_TOKEN:
        raise SystemExit("Preencha TELEGRAM_TOKEN e TMDB_TOKEN no arquivo .env")

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", iniciar))
    app.add_handler(CommandHandler("ajuda", iniciar))
    app.add_handler(CommandHandler("buscar", buscar))
    app.add_handler(CommandHandler(["acao", "terror", "comedia"], recomendar))

    print("CineBot iniciado! Abra o Telegram e envie /start.")
    app.run_polling()
