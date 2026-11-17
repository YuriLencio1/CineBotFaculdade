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


# ======================= NOVAS OPÇÕES DE PESQUISA =======================

#chats esperando uma resposta nos novos menus: {chat_id: "modo"}
aguardando_busca = {}


async def menu(update, context):
    """Menu completo com todas as opções do bot."""
    await update.message.reply_text(
        "🎬 MENU COMPLETO DO CINEBOT\n\n"
        "🔎 PESQUISAR\n"
        "/buscar nome — pesquisar filme pelo nome\n"
        "/ano — digite um ano e recomendamos um filme\n"
        "/decada — digite uma década (ex: 90) e recomendamos\n"
        "/ator — digite um ator/atriz e recomendamos\n"
        "/parecido — digite um filme e sugerimos parecidos\n\n"
        "🎭 POR GÊNERO\n"
        "/acao — recomendar ação\n"
        "/terror — recomendar terror\n"
        "/comedia — recomendar comédia\n"
        "/recomendacao — escolher qualquer gênero (mais bem avaliados)\n\n"
        "🔥 DESTAQUES\n"
        "/populares — filmes em alta agora\n"
        "/top — melhores filmes de todos os tempos\n"
        "/emcartaz — em cartaz nos cinemas\n"
        "/breve — próximos lançamentos\n"
        "/aleatorio — surpreenda-me!\n\n"
        "🎯 JOGOS\n"
        "/quiz — quiz de perguntas sobre filmes\n\n"
        "/cancelar — cancelar a pergunta atual"
    )


async def sortear_da_lista(update, endereco, parametros, pagina_max=1):
    """Consulta o TMDB e mostra um filme sorteado da lista retornada."""
    try:
        parametros = {**parametros, "page": random.randint(1, pagina_max)}
        dados = consultar_api(endereco, parametros)
        filmes = dados.get("results", [])
        await mostrar_filme(update, random.choice(filmes) if filmes else None)
    except requests.RequestException:
        await update.message.reply_text("Erro ao consultar o TMDB. Tente novamente.")


# ---------- comandos que perguntam algo ao usuário ----------

async def pedir_ano(update, context):
    chat_id = update.effective_chat.id
    aguardando_genero.discard(chat_id)
    aguardando_busca[chat_id] = "ano"
    await update.message.reply_text("📅 Digite o ano do filme (ex: 1999):\n\n(/cancelar para sair)")


async def pedir_decada(update, context):
    chat_id = update.effective_chat.id
    aguardando_genero.discard(chat_id)
    aguardando_busca[chat_id] = "decada"
    await update.message.reply_text("🕰️ Digite a década (ex: 80, 90, 2000):\n\n(/cancelar para sair)")


async def pedir_ator(update, context):
    chat_id = update.effective_chat.id
    aguardando_genero.discard(chat_id)
    aguardando_busca[chat_id] = "ator"
    await update.message.reply_text("🎭 Digite o nome de um ator ou atriz:\n\n(/cancelar para sair)")


async def pedir_parecido(update, context):
    chat_id = update.effective_chat.id
    aguardando_genero.discard(chat_id)
    aguardando_busca[chat_id] = "parecido"
    await update.message.reply_text("🎞️ Digite o nome de um filme que você gosta:\n\n(/cancelar para sair)")


async def receber_busca(update, context):
    """Recebe a resposta digitada nos novos menus (ano, década, ator, parecido)."""
    chat_id = update.effective_chat.id
    modo = aguardando_busca.get(chat_id)
    if not modo:
        return  #chat não está esperando nada dos novos menus

    texto = update.message.text.strip()

    try:
        if modo == "ano":
            if not (texto.isdigit() and len(texto) == 4 and 1900 <= int(texto) <= 2035):
                await update.message.reply_text("Ano inválido 😕 Digite 4 números (ex: 2005) ou /cancelar.")
                return
            aguardando_busca.pop(chat_id, None)
            await sortear_da_lista(
                update, "/discover/movie",
                {"primary_release_year": texto, "sort_by": "vote_count.desc",
                 "vote_count.gte": 100},
                pagina_max=3,
            )

        elif modo == "decada":
            numeros = "".join(c for c in texto if c.isdigit())
            if len(numeros) == 2:
                inicio = 2000 + int(numeros) if int(numeros) <= 30 else 1900 + int(numeros)
            elif len(numeros) == 4:
                inicio = int(numeros) // 10 * 10
            else:
                await update.message.reply_text("Não entendi 😕 Digite algo como 90 ou 1990, ou /cancelar.")
                return
            aguardando_busca.pop(chat_id, None)
            await sortear_da_lista(
                update, "/discover/movie",
                {"primary_release_date.gte": f"{inicio}-01-01",
                 "primary_release_date.lte": f"{inicio + 9}-12-31",
                 "sort_by": "vote_count.desc", "vote_count.gte": 200},
                pagina_max=3,
            )

        elif modo == "ator":
            pessoas = consultar_api("/search/person", {"query": texto}).get("results", [])
            if not pessoas:
                await update.message.reply_text("Não encontrei esse ator 😕 Tente outro nome ou /cancelar.")
                return
            aguardando_busca.pop(chat_id, None)
            await update.message.reply_text(f"🎭 Filme com {pessoas[0].get('name', texto)}:")
            await sortear_da_lista(
                update, "/discover/movie",
                {"with_cast": pessoas[0]["id"], "sort_by": "vote_count.desc",
                 "vote_count.gte": 100},
            )

        elif modo == "parecido":
            filmes = consultar_api("/search/movie", {"query": texto}).get("results", [])
            if not filmes:
                await update.message.reply_text("Não encontrei esse filme 😕 Tente outro nome ou /cancelar.")
                return
            aguardando_busca.pop(chat_id, None)
            await update.message.reply_text(f"🎞️ Parecido com {filmes[0].get('title', texto)}:")
            await sortear_da_lista(update, f"/movie/{filmes[0]['id']}/recommendations", {})

    except requests.RequestException:
        await update.message.reply_text("Erro ao consultar o TMDB. Tente novamente.")


async def cancelar_busca(update, context):
    """Limpa também as perguntas dos novos menus (roda junto com o /cancelar original)."""
    aguardando_busca.pop(update.effective_chat.id, None)


# ---------- comandos diretos (sem perguntar nada) ----------

async def populares(update, context):
    await sortear_da_lista(update, "/movie/popular", {}, pagina_max=3)


async def top(update, context):
    await sortear_da_lista(update, "/movie/top_rated", {}, pagina_max=5)


async def em_cartaz(update, context):
    await sortear_da_lista(update, "/movie/now_playing", {"region": "BR"})


async def breve(update, context):
    await sortear_da_lista(update, "/movie/upcoming", {"region": "BR"})


async def aleatorio(update, context):
    await sortear_da_lista(
        update, "/discover/movie",
        {"sort_by": "vote_count.desc", "vote_count.gte": 500},
        pagina_max=20,
    )

# ========================================================================


# ======================= QUIZ DE FILMES (API OpenTDB) =======================
#API gratuita, sem token: https://opentdb.com  (categoria 11 = Filmes)
import html
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler

#pergunta em aberto de cada mensagem: {(chat_id, message_id): {"correta": ..., "opcoes": [...]}}
quiz_atual = {}
#placar de cada chat: {chat_id: [acertos, total]}
placar = {}


#dificuldades da OpenTDB em português
DIFICULDADES = {"easy": "fácil", "medium": "médio", "hard": "difícil"}


def traduzir(texto):
    """Traduz inglês -> português com a API MyMemory. Se falhar, devolve o texto original."""
    try:
        resposta = requests.get(
            "https://api.mymemory.translated.net/get",
            params={"q": texto, "langpair": "en|pt-BR"},
            timeout=15,
        )
        resposta.raise_for_status()
        dados = resposta.json()
        traduzido = html.unescape(dados["responseData"]["translatedText"])
        #se o limite diário acabou, a API devolve um aviso no lugar da tradução
        if str(dados.get("responseStatus")) != "200" or "MYMEMORY WARNING" in traduzido.upper():
            return texto
        return traduzido
    except (requests.RequestException, ValueError, KeyError):
        return texto


async def quiz(update, context):
    """Busca uma pergunta de cinema na OpenTDB, traduz e mostra com botões A/B/C/D."""
    try:
        resposta = requests.get(
            "https://opentdb.com/api.php",
            params={"amount": 1, "category": 11, "type": "multiple"},
            timeout=15,
        )
        resposta.raise_for_status()
        dados = resposta.json()
    except (requests.RequestException, ValueError):
        await update.message.reply_text("Erro ao buscar a pergunta. Tente novamente.")
        return

    #a OpenTDB só aceita 1 pedido a cada 5 segundos (response_code diferente de 0)
    if dados.get("response_code") != 0 or not dados.get("results"):
        await update.message.reply_text("O quiz está ocupado 😕 Espere uns 5 segundos e tente de novo.")
        return

    p = dados["results"][0]
    #a API manda símbolos como &quot;; a pergunta é traduzida, as alternativas (nomes de filmes, atores) ficam no original
    pergunta = traduzir(html.unescape(p["question"]))
    correta = html.unescape(p["correct_answer"])
    opcoes = [html.unescape(o) for o in p["incorrect_answers"]] + [correta]
    random.shuffle(opcoes)

    letras = "ABCD"
    texto = (
        f"🎯 QUIZ DE FILMES ({DIFICULDADES.get(p['difficulty'], p['difficulty'])})\n\n"
        f"{pergunta}\n\n"
        + "\n".join(f"{letras[i]}) {o}" for i, o in enumerate(opcoes))
    )
    botoes = [[InlineKeyboardButton(letras[i], callback_data=f"quiz:{i}") for i in range(len(opcoes))]]

    msg = await update.message.reply_text(texto, reply_markup=InlineKeyboardMarkup(botoes))
    quiz_atual[(msg.chat_id, msg.message_id)] = {"correta": correta, "opcoes": opcoes}


async def responder_quiz(update, context):
    """Chamado quando o usuário clica em um botão do quiz."""
    query = update.callback_query
    chave = (query.message.chat_id, query.message.message_id)
    dados = quiz_atual.pop(chave, None)   #pop: cada pergunta só pode ser respondida uma vez

    if not dados:
        await query.answer("Essa pergunta já foi respondida.")
        return

    escolhida = dados["opcoes"][int(query.data.split(":")[1])]
    acertou = escolhida == dados["correta"]

    pontos = placar.setdefault(query.message.chat_id, [0, 0])
    pontos[1] += 1
    if acertou:
        pontos[0] += 1

    resultado = "✅ Acertou!" if acertou else f"❌ Errou! A resposta era: {dados['correta']}"
    await query.answer()
    await query.edit_message_text(   #sem reply_markup, os botões somem
        f"{query.message.text}\n\n{resultado}\n"
        f"🏆 Placar: {pontos[0]}/{pontos[1]}\n\n"
        "/quiz para outra pergunta"
    )

# ============================================================================


#inicia o bot e relaciona cada comando à sua função.
if __name__ == "__main__":
    if not TELEGRAM_TOKEN or not TMDB_TOKEN:
        raise SystemExit("Preencha TELEGRAM_TOKEN e TMDB_TOKEN no arquivo .env")

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", menu))
    app.add_handler(CommandHandler("ajuda", menu))
    app.add_handler(CommandHandler("buscar", buscar))
    app.add_handler(CommandHandler(["acao", "terror", "comedia"], recomendar))
    app.add_handler(CommandHandler("recomendacao", recomendacao))
    app.add_handler(CommandHandler("cancelar", cancelar))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receber_genero))

    #novos menus
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(CommandHandler("ano", pedir_ano))
    app.add_handler(CommandHandler("decada", pedir_decada))
    app.add_handler(CommandHandler("ator", pedir_ator))
    app.add_handler(CommandHandler("parecido", pedir_parecido))
    app.add_handler(CommandHandler("populares", populares))
    app.add_handler(CommandHandler("top", top))
    app.add_handler(CommandHandler("emcartaz", em_cartaz))
    app.add_handler(CommandHandler("breve", breve))
    app.add_handler(CommandHandler("aleatorio", aleatorio))

    #group=1 faz esses handlers rodarem JUNTO com os originais, sem substituí-los
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receber_busca), group=1)
    app.add_handler(CommandHandler("cancelar", cancelar_busca), group=1)

    #quiz
    app.add_handler(CommandHandler("quiz", quiz))
    app.add_handler(CallbackQueryHandler(responder_quiz, pattern="^quiz:"))

    print("CineBot iniciado! Abra o Telegram e envie /start.")
    app.run_polling()
