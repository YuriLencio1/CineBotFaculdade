"""Etapa 6: ponto de entrada. Aqui existe UM único bot do Telegram."""

from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from comandos import (
    aleatorio, breve, buscar, cancelar, em_cartaz, menu, pedir_ano,
    pedir_ator, pedir_decada, pedir_parecido, populares, receber_texto,
    recomendacao, recomendar, top,
)
from config import TELEGRAM_TOKEN, TMDB_TOKEN
from quiz import quiz, responder_quiz


def criar_app():
    """Registra cada comando apenas uma vez e devolve a aplicação pronta."""
    if not TELEGRAM_TOKEN or not TMDB_TOKEN:
        raise SystemExit('Configure TELEGRAM_TOKEN e TMDB_TOKEN no arquivo .env')

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Menus e pesquisa por nome.
    app.add_handler(CommandHandler(['start', 'ajuda', 'menu'], menu))
    app.add_handler(CommandHandler('buscar', buscar))
    app.add_handler(CommandHandler(['acao', 'terror', 'comedia'], recomendar))

    # Comandos com pergunta: usam UM único gerenciador de estado.
    app.add_handler(CommandHandler('recomendacao', recomendacao))
    app.add_handler(CommandHandler('ano', pedir_ano))
    app.add_handler(CommandHandler('decada', pedir_decada))
    app.add_handler(CommandHandler('ator', pedir_ator))
    app.add_handler(CommandHandler('parecido', pedir_parecido))
    app.add_handler(CommandHandler('cancelar', cancelar))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receber_texto))

    # Filmes em destaque.
    app.add_handler(CommandHandler('populares', populares))
    app.add_handler(CommandHandler('top', top))
    app.add_handler(CommandHandler('emcartaz', em_cartaz))
    app.add_handler(CommandHandler('breve', breve))
    app.add_handler(CommandHandler('aleatorio', aleatorio))

    # Quiz de filmes e cliques nos botões.
    app.add_handler(CommandHandler('quiz', quiz))
    app.add_handler(CallbackQueryHandler(responder_quiz, pattern=r'^quiz:[0-3]$'))

    return app


if __name__ == '__main__':
    app = criar_app()
    print('CineBot iniciado! Abra o Telegram e envie /start.')
    app.run_polling()
