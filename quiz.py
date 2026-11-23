"""Etapa 5: quiz de cinema com OpenTDB, MyMemory e placar individual."""

import asyncio
import html
import random

import requests
from api_telegram import TelegramError

from estados import limpar_modo

DIFICULDADES = {'easy': 'fácil', 'medium': 'médio', 'hard': 'difícil'}


def _buscar_pergunta_sincrona():
    """Requisição GET à OpenTDB (categoria 11 corresponde a filmes)."""
    resposta = requests.get(
        'https://opentdb.com/api.php',
        params={'amount': 1, 'category': 11, 'type': 'multiple'},
        timeout=15,
    )
    resposta.raise_for_status()
    dados = resposta.json()
    if not isinstance(dados, dict):
        raise ValueError('A OpenTDB devolveu uma resposta inesperada.')
    return dados


def _traduzir_sincrono(texto):
    """Traduz a pergunta do inglês para português; em erro, preserva o original."""
    try:
        resposta = requests.get(
            'https://api.mymemory.translated.net/get',
            params={'q': texto, 'langpair': 'en|pt-BR'},
            timeout=15,
        )
        resposta.raise_for_status()
        dados = resposta.json()
        traducao = html.unescape(dados['responseData']['translatedText'])
        if str(dados.get('responseStatus')) != '200' or 'MYMEMORY WARNING' in traducao.upper():
            return texto
        return traducao
    except (requests.RequestException, ValueError, KeyError, TypeError):
        return texto


async def quiz(update, context):
    """Envia uma pergunta com botões A/B/C/D e registra o dono do quiz."""
    limpar_modo(context, update.effective_user.id)

    try:
        dados = await asyncio.to_thread(_buscar_pergunta_sincrona)
    except (requests.RequestException, ValueError):
        await update.message.reply_text('Erro ao buscar a pergunta. Tente novamente.')
        return

    # A OpenTDB pode indicar limite de requisições ou falta de perguntas.
    if dados.get('response_code') != 0 or not dados.get('results'):
        await update.message.reply_text('Quiz indisponível no momento. Aguarde alguns segundos e tente novamente.')
        return

    pergunta_api = dados['results'][0]
    try:
        pergunta_original = html.unescape(pergunta_api['question'])
        correta = html.unescape(pergunta_api['correct_answer'])
        erradas = [html.unescape(opcao) for opcao in pergunta_api['incorrect_answers']]
        dificuldade = pergunta_api.get('difficulty', 'easy')
    except (KeyError, TypeError):
        await update.message.reply_text('Pergunta recebida em formato inválido. Tente novamente.')
        return

    # Mantém as alternativas no idioma fornecido pela OpenTDB, para não alterar respostas.
    pergunta = await asyncio.to_thread(_traduzir_sincrono, pergunta_original)
    opcoes = erradas + [correta]
    if len(opcoes) != 4:
        await update.message.reply_text('A pergunta veio com alternativas incompletas. Tente novamente.')
        return
    random.shuffle(opcoes)

    letras = 'ABCD'
    texto = (
        f'🎯 QUIZ DE FILMES ({DIFICULDADES.get(dificuldade, dificuldade)})\n\n'
        f'{pergunta}\n\n'
        + '\n'.join(f'{letras[i]}) {opcao}' for i, opcao in enumerate(opcoes))
    )
    botoes = [[{'text': letras[i], 'callback_data': f'quiz:{i}'} for i in range(4)]]

    msg = await update.message.reply_text(texto[:3600], reply_markup={'inline_keyboard': botoes})

    # chat_data é isolado por chat. Cada pergunta registra seu criador.
    perguntas = context.chat_data.setdefault('quizzes', {})
    perguntas[msg.message_id] = {
        'correta': correta,
        'opcoes': opcoes,
        'criador_id': update.effective_user.id,
    }
    # Evita crescimento ilimitado caso os usuários nunca respondam.
    if len(perguntas) > 100:
        perguntas.pop(next(iter(perguntas)))


async def responder_quiz(update, context):
    """Só quem iniciou a pergunta pode respondê-la; placar é por usuário."""
    query = update.callback_query
    if not query.message:
        await query.answer('Essa pergunta não está disponível.', show_alert=True)
        return

    mensagem_id = query.message.message_id
    perguntas = context.chat_data.get('quizzes', {})
    dados = perguntas.get(mensagem_id)

    if dados is None:
        await query.answer('Essa pergunta já foi respondida ou expirou.')
        return

    if query.from_user.id != dados['criador_id']:
        await query.answer('Somente quem iniciou esse quiz pode responder.')
        return

    try:
        indice = int(query.data.split(':')[1])
    except (AttributeError, ValueError, IndexError):
        await query.answer('Resposta inválida.')
        return
    if not 0 <= indice < len(dados['opcoes']):
        await query.answer('Resposta inválida.')
        return

    # Só remove depois de confirmar que o usuário e a alternativa são válidos.
    perguntas.pop(mensagem_id)
    acertou = dados['opcoes'][indice] == dados['correta']
    placares = context.chat_data.setdefault('placares', {})
    pontos = placares.setdefault(query.from_user.id, [0, 0])
    pontos[1] += 1
    if acertou:
        pontos[0] += 1

    resultado = '✅ Acertou!' if acertou else f"❌ Errou! A resposta era: {dados['correta']}"
    await query.answer()
    try:
        await query.edit_message_text(
            f'{query.message.text[:3600]}\n\n{resultado[:300]}\n'
            f'🏆 Seu placar: {pontos[0]}/{pontos[1]}\n\n'
            '/quiz para outra pergunta'
        )
    except TelegramError:
        # A pergunta foi contabilizada, mas a mensagem pode ter sido apagada.
        pass
