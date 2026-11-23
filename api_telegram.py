"""API HTTP oficial do Telegram com requests, sem bibliotecas de bots.

O Telegram envia e recebe dados no formato JSON. Este arquivo apenas organiza
as chamadas HTTP e representa mensagens com classes criadas aqui no projeto.
"""

import asyncio
import json

# Configura certificados SSL antes de importar requests.
from config import TELEGRAM_TOKEN

import requests

URL_BASE = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}'


class TelegramError(Exception):
    """Erro recebido da API HTTP do Telegram."""


def chamar_api(metodo, dados=None, http='POST', timeout=20):
    """Faz GET/POST diretamente para https://api.telegram.org/bot<TOKEN>/<metodo>."""
    url = f'{URL_BASE}/{metodo}'
    if http == 'GET':
        resposta = requests.get(url, params=dados, timeout=timeout)
    else:
        resposta = requests.post(url, json=dados or {}, timeout=timeout)

    # Primeiro interpreta a resposta JSON, inclusive erros 400/401/429 da API.
    # Isso evita exibir o token (presente na URL) em mensagens de HTTPError.
    try:
        retorno = resposta.json()
    except ValueError as erro:
        raise TelegramError(f'{metodo}: o Telegram não retornou JSON.') from erro
    if not isinstance(retorno, dict) or not retorno.get('ok'):
        descricao = retorno.get('description', 'Resposta inesperada') if isinstance(retorno, dict) else 'JSON inválido'
        raise TelegramError(f'{metodo}: {descricao}')
    return retorno['result']


def get_updates(offset=None):
    """GET getUpdates: espera até 25s por mensagens ou cliques nos botões."""
    parametros = {'timeout': 25, 'allowed_updates': json.dumps(['message', 'callback_query'])}
    if offset is not None:
        parametros['offset'] = offset
    return chamar_api('getUpdates', parametros, http='GET', timeout=35)


async def enviar_mensagem(chat_id, texto, reply_markup=None):
    """POST sendMessage: envia texto e, opcionalmente, teclado JSON."""
    dados = {'chat_id': chat_id, 'text': texto}
    if reply_markup is not None:
        dados['reply_markup'] = reply_markup
    return await asyncio.to_thread(chamar_api, 'sendMessage', dados)


async def enviar_foto(chat_id, foto, legenda):
    """POST sendPhoto: passa a URL do pôster diretamente à API do Telegram."""
    return await asyncio.to_thread(
        chamar_api, 'sendPhoto', {'chat_id': chat_id, 'photo': foto, 'caption': legenda}
    )


async def responder_callback(callback_id, texto='', show_alert=False):
    """POST answerCallbackQuery: confirma o clique no botão do quiz."""
    return await asyncio.to_thread(
        chamar_api, 'answerCallbackQuery',
        {'callback_query_id': callback_id, 'text': texto, 'show_alert': show_alert}
    )


async def editar_mensagem(chat_id, mensagem_id, texto):
    """POST editMessageText: troca a pergunta pelo resultado do quiz."""
    return await asyncio.to_thread(
        chamar_api, 'editMessageText',
        {'chat_id': chat_id, 'message_id': mensagem_id, 'text': texto}
    )


class Usuario:
    def __init__(self, dados):
        self.id = dados['id']


class Mensagem:
    """Representação pequena de uma mensagem JSON, feita pelo próprio projeto."""

    def __init__(self, dados):
        self.message_id = dados['message_id']
        self.chat_id = dados['chat']['id']
        self.text = dados.get('text') or ''

    async def reply_text(self, texto, reply_markup=None):
        resposta = await enviar_mensagem(self.chat_id, texto, reply_markup)
        return Mensagem(resposta)

    async def reply_photo(self, photo, caption):
        return await enviar_foto(self.chat_id, photo, caption)


class Callback:
    """Representa o clique em botão retornado por callback_query."""

    def __init__(self, dados):
        self.id = dados['id']
        self.data = dados.get('data') or ''
        self.from_user = Usuario(dados['from'])
        mensagem = dados.get('message')
        # Um callback pode se referir a uma mensagem já indisponível.
        self.message = Mensagem(mensagem) if isinstance(mensagem, dict) and 'chat' in mensagem else None

    async def answer(self, texto='', show_alert=False):
        return await responder_callback(self.id, texto, show_alert)

    async def edit_message_text(self, texto):
        if self.message is None:
            raise TelegramError('Mensagem do quiz indisponível.')
        return await editar_mensagem(self.message.chat_id, self.message.message_id, texto)


class Atualizacao:
    """Converte o JSON do getUpdates em atributos usados nos comandos."""

    def __init__(self, dados):
        self.message = None
        self.callback_query = None
        if 'message' in dados:
            self.message = Mensagem(dados['message'])
            self.effective_user = Usuario(dados['message']['from'])
        elif 'callback_query' in dados:
            self.callback_query = Callback(dados['callback_query'])
            self.effective_user = self.callback_query.from_user
        else:
            raise ValueError('Tipo de atualização não suportado')
