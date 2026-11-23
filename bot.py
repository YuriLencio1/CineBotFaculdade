"""Inicia o CineBot por chamadas HTTP diretas ao Telegram (sem telegram.ext)."""

import asyncio

from config import TELEGRAM_TOKEN, TMDB_TOKEN

import requests

from api_telegram import Atualizacao, TelegramError, get_updates
from comandos import (
    aleatorio, breve, buscar, cancelar, em_cartaz, menu, pedir_ano,
    pedir_ator, pedir_decada, pedir_parecido, populares, receber_texto,
    recomendacao, recomendar, top,
)
from quiz import quiz, responder_quiz

# Cada conversa tem seus próprios modos de perguntas e quizzes.
DADOS_DOS_CHATS = {}


class Contexto:
    """Guarda argumentos e dados de cada chat sem depender de biblioteca Telegram."""

    def __init__(self, chat_id, args=None):
        self.chat_data = DADOS_DOS_CHATS.setdefault(chat_id, {})
        self.args = args or []


# Comandos registrados em um dicionário comum do Python, sem CommandHandler.
COMANDOS = {
    'start': menu, 'ajuda': menu, 'menu': menu,
    'buscar': buscar, 'acao': recomendar, 'terror': recomendar, 'comedia': recomendar,
    'recomendacao': recomendacao, 'ano': pedir_ano, 'decada': pedir_decada,
    'ator': pedir_ator, 'parecido': pedir_parecido, 'cancelar': cancelar,
    'populares': populares, 'top': top, 'emcartaz': em_cartaz,
    'breve': breve, 'aleatorio': aleatorio, 'quiz': quiz,
}


async def processar_atualizacao(dados):
    """Decide qual função executar para cada mensagem/callback recebido em JSON."""
    if 'message' not in dados and 'callback_query' not in dados:
        return
    update = Atualizacao(dados)

    if update.callback_query is not None:
        # O botão chega como callback_query, não como uma mensagem de texto.
        if update.callback_query.data.startswith('quiz:'):
            chat_id = update.callback_query.message.chat_id if update.callback_query.message else None
            context = Contexto(chat_id)
            await responder_quiz(update, context)
        else:
            await update.callback_query.answer('Botão desconhecido.')
        return

    texto = update.message.text.strip()
    if not texto:
        return
    context = Contexto(update.message.chat_id)

    if texto.startswith('/'):
        comando, *argumentos = texto.split()
        comando = comando[1:].split('@')[0].lower()
        context.args = argumentos
        funcao = COMANDOS.get(comando)
        if funcao:
            await funcao(update, context)
        else:
            await update.message.reply_text('Comando desconhecido. Use /menu para ver as opções.')
    else:
        await receber_texto(update, context)


async def iniciar_bot():
    if not TELEGRAM_TOKEN or not TMDB_TOKEN:
        raise SystemExit('Configure TELEGRAM_TOKEN e TMDB_TOKEN no arquivo .env')

    print('CineBot iniciado com a API HTTP direta! Abra o Telegram e envie /start.')
    offset = None
    while True:
        try:
            # GET: consulta o endpoint getUpdates da API oficial.
            atualizacoes = await asyncio.to_thread(get_updates, offset)
        except (requests.RequestException, TelegramError, ValueError) as erro:
            erro_sem_token = str(erro).replace(TELEGRAM_TOKEN, '[TOKEN]')
            print(f'Erro ao consultar o Telegram: {erro_sem_token}')
            await asyncio.sleep(5)
            continue

        for dados in atualizacoes:
            # A próxima busca usará o ID seguinte, evitando mensagens repetidas.
            offset = dados['update_id'] + 1
            try:
                await processar_atualizacao(dados)
            except (requests.RequestException, TelegramError, ValueError, KeyError) as erro:
                print(f'Erro ao processar mensagem: {erro}')
                mensagem = dados.get('message')
                if mensagem and 'chat' in mensagem:
                    try:
                        from api_telegram import enviar_mensagem
                        await enviar_mensagem(mensagem['chat']['id'], 'Ocorreu um erro. Tente novamente.')
                    except (requests.RequestException, TelegramError):
                        pass


if __name__ == '__main__':
    try:
        asyncio.run(iniciar_bot())
    except KeyboardInterrupt:
        print('\nCineBot finalizado.')
