#Bibliotecas
#certificados de segurança para conexão com as APIs
import truststore
truststore.inject_into_ssl()
#bibliotecas para acessar variáveis, gerar números aleatórios e consultar APIs
import os
import random
import requests
#carrega os tokens armazenados no arquivo .env
from dotenv import load_dotenv
#bibliotecas para criar o bot e configurar os comandos do Telegram
from telegram.ext import ApplicationBuilder, CommandHandler

#tokens guardados no arquivo .env.
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
    resposta.raise_for_status()  #verifica se houve erro HTTP.
    return resposta.json()       



async def mostrar_filme(update, filme):
    """Envia as informações completas de um filme para o Telegram."""
    if not filme:
        await update.message.reply_text("Nenhum filme encontrado.")
        return

    titulo = filme.get("title", "Sem título")
    nota = filme.get("vote_average") or 0
    sinopse = filme.get("overview") or "Sinopse indisponível."

    # Obtém o ano de lançamento
    lancamento = filme.get("release_date") or ""
    ano = lancamento[:4] if lancamento else "Não informado"

    # Monta a mensagem
    mensagem = (
        f"🎬 {titulo}\n"
        f"📅 Ano: {ano}\n"
        f"⭐ Nota: {nota:.1f}/10\n\n"
        f"📝 {sinopse}"
    )

    # Obtém o cartaz do TMDB
    poster = filme.get("poster_path")

    if poster:
        imagem = f"https://image.tmdb.org/t/p/w500{poster}"
        await update.message.reply_photo(
            photo=imagem,
            caption=mensagem[:1024]
        )
    else:
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

    #pega o nome do filme digitado pelo usuário
    try:
        nome = " ".join(context.args)
            #chama a função que faz a requisição GET ao TMDB
        dados = consultar_api("/search/movie", {"query": nome})
            #extrai a lista de filmes do JSON retornado
        filmes = dados.get("results", [])
            #extrai a lista de filmes do JSON retornado
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


#inicia o bot e relaciona cada comando à sua função.
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
