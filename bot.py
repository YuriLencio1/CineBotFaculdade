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
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
import unicodedata

#tokens guardados no arquivo .env.
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TMDB_TOKEN = os.getenv("TMDB_TOKEN")

#gêneros usados pela API TMDB.
GENEROS = {
    "acao": 28, "aventura": 12, "animacao": 16, "comedia": 35,
    "crime": 80, "documentario": 99, "drama": 18, "familia": 10751,
    "fantasia": 14, "historia": 36, "terror": 27, "musica": 10402,
    "misterio": 9648, "romance": 10749, "ficcao cientifica": 878,
    "suspense": 53, "guerra": 10752, "faroeste": 37,
}

#chats que estão esperando o usuário digitar o gênero
aguardando_genero = set()

#o TMDB usa nota de 0 a 10; 5 estrelas = nota a partir de 8 (ajuste se quiser)
NOTA_MINIMA = 8.0
VOTOS_MINIMOS = 1000   #evita filmes com poucas avaliações
MAX_FILMES = 8


def normalizar(texto):
    """Remove acentos e deixa em minúsculo: 'Comédia' -> 'comedia'."""
    texto = unicodedata.normalize("NFD", texto.strip().lower())
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")


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

async def recomendacao(update, context):
    """Pergunta o gênero e marca o chat como 'aguardando'."""
    aguardando_genero.add(update.effective_chat.id)
    await update.message.reply_text(
        "Qual gênero você deseja?\n\n"
        "Opções: " + ", ".join(g.title() for g in GENEROS) +
        "\n\n(/cancelar para sair)"
    )


async def receber_genero(update, context):
    """Recebe o gênero digitado e lista os filmes 5 estrelas."""
    chat_id = update.effective_chat.id

    #ignora mensagens de quem não está no meio de um /recomendacao
    if chat_id not in aguardando_genero:
        return

    genero = normalizar(update.message.text)

    if genero not in GENEROS:
        await update.message.reply_text(
            "Não reconheci esse gênero 😕 Tente outro (ou /cancelar)."
        )
        return  #continua aguardando um gênero válido

    aguardando_genero.discard(chat_id)  #já recebeu o gênero

    try:
        dados = consultar_api(
            "/discover/movie",
            {
                "with_genres": GENEROS[genero],
                "sort_by": "vote_average.desc",
                "vote_average.gte": NOTA_MINIMA,
                "vote_count.gte": VOTOS_MINIMOS,
            },
        )
    except requests.RequestException:
        await update.message.reply_text("Erro ao consultar o TMDB. Tente novamente.")
        return

    filmes = dados.get("results", [])[:MAX_FILMES]
    if not filmes:
        await update.message.reply_text("Não encontrei filmes 5 estrelas desse gênero.")
        return

    await update.message.reply_text(f"⭐⭐⭐⭐⭐ Filmes de {genero.title()} mais bem avaliados:")

    #uma mensagem por filme, para não passar do limite de 4096 caracteres do Telegram
    for filme in filmes:
        titulo = filme.get("title", "Sem título")
        ano = (filme.get("release_date") or "")[:4] or "s/ data"
        nota = filme.get("vote_average") or 0
        sinopse = filme.get("overview") or "Sinopse indisponível."
        await update.message.reply_text(
            f"🎬 {titulo} ({ano})\n"
            f"⭐ {nota:.1f}/10\n\n"
            f"📝 {sinopse}"[:4000]
        )


async def cancelar(update, context):
    """Cancela o /recomendacao em andamento."""
    aguardando_genero.discard(update.effective_chat.id)
    await update.message.reply_text("Recomendação cancelada.")

#inicia o bot e relaciona cada comando à sua função.
if __name__ == "__main__":
    if not TELEGRAM_TOKEN or not TMDB_TOKEN:
        raise SystemExit("Preencha TELEGRAM_TOKEN e TMDB_TOKEN no arquivo .env")

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", iniciar))
    app.add_handler(CommandHandler("ajuda", iniciar))
    app.add_handler(CommandHandler("buscar", buscar))
    app.add_handler(CommandHandler(["acao", "terror", "comedia"], recomendar))
    app.add_handler(CommandHandler("recomendacao", recomendacao))
    app.add_handler(CommandHandler("cancelar", cancelar))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receber_genero))

    print("CineBot iniciado! Abra o Telegram e envie /start.")
    app.run_polling()