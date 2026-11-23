"""Etapa 4: comandos do Telegram e respostas de pesquisa/recomendação."""

import random
import re
import unicodedata
from datetime import datetime

import requests
from api_telegram import TelegramError

from api_filmes import consultar_api, sortear_filme
from config import GENEROS, MAX_FILMES, NOTA_MINIMA, VOTOS_MINIMOS
from estados import definir_modo, limpar_modo, obter_modo


def normalizar(texto):
    """Transforma 'Ficção Científica' em 'ficcao cientifica'."""
    texto = unicodedata.normalize('NFD', texto.strip().lower())
    return ''.join(caractere for caractere in texto if unicodedata.category(caractere) != 'Mn')


def interpretar_decada(texto):
    """Aceita 90, anos 90 ou 1990. Retorna o ano inicial da década."""
    texto = normalizar(texto)
    resultado = re.fullmatch(r'(?:anos?\s+)?(\d{2}|\d{4})', texto)
    if not resultado:
        return None
    numero = resultado.group(1)
    if len(numero) == 4:
        return (int(numero) // 10) * 10
    ano_curto = int(numero)
    # Ex.: 90 -> 1990; 05 -> 2000; 20 -> 2020.
    seculo = 2000 if ano_curto <= datetime.now().year % 100 else 1900
    return seculo + ano_curto


async def mostrar_filme(update, filme):
    """Mostra pôster, ano, nota e sinopse. Não corta a sinopse sem avisar."""
    if not filme:
        await update.message.reply_text('Nenhum filme encontrado com esses filtros.')
        return

    titulo = filme.get('title') or 'Sem título'
    ano = (filme.get('release_date') or '')[:4] or 'Não informado'
    nota = float(filme.get('vote_average') or 0)
    sinopse = filme.get('overview') or 'Sinopse indisponível.'
    cabecalho = f'🎬 {titulo}\n📅 Ano: {ano}\n⭐ Nota: {nota:.1f}/10'
    mensagem = f'{cabecalho}\n\n📝 {sinopse}'
    poster = filme.get('poster_path')

    if poster:
        try:
            if len(mensagem) <= 1024:
                await update.message.reply_photo(
                    photo=f'https://image.tmdb.org/t/p/w500{poster}',
                    caption=mensagem,
                )
            else:
                # Legenda de foto tem limite de 1024 caracteres no Telegram.
                await update.message.reply_photo(
                    photo=f'https://image.tmdb.org/t/p/w500{poster}',
                    caption=cabecalho,
                )
                await update.message.reply_text(f'📝 {sinopse}'[:4000])
            return
        except (TelegramError, requests.RequestException):
            # Se o pôster não estiver acessível, envia o texto normalmente.
            pass

    await update.message.reply_text(mensagem[:4000])


async def menu(update, context):
    """Mostra a lista de comandos e encerra qualquer pergunta pendente."""
    limpar_modo(context, update.effective_user.id)
    await update.message.reply_text(
        '🎬 MENU COMPLETO DO CINEBOT\n\n'
        '🔎 PESQUISAR\n'
        '/buscar nome — pesquisar filme pelo nome\n'
        '/ano — digite um ano para receber um filme\n'
        '/decada — digite uma década (ex: 90)\n'
        '/ator — digite um ator/atriz\n'
        '/parecido — digite um filme para encontrar parecidos\n\n'
        '🎭 POR GÊNERO\n'
        '/acao — recomendar ação\n'
        '/terror — recomendar terror\n'
        '/comedia — recomendar comédia\n'
        '/recomendacao — escolher qualquer gênero (filmes bem avaliados)\n\n'
        '🔥 DESTAQUES\n'
        '/populares — sortear um filme popular\n'
        '/top — sortear um dos filmes mais bem avaliados\n'
        '/emcartaz — sortear um filme em cartaz\n'
        '/breve — sortear um próximo lançamento\n'
        '/aleatorio — surpreenda-me!\n\n'
        '🎯 JOGOS\n'
        '/quiz — quiz de perguntas sobre filmes\n\n'
        '/cancelar — cancelar a pergunta atual'
    )


async def buscar(update, context):
    """Pesquisa filmes pelo nome informado após /buscar."""
    limpar_modo(context, update.effective_user.id)
    nome = ' '.join(context.args).strip()
    if not nome:
        await update.message.reply_text('Exemplo: /buscar Interestelar')
        return

    try:
        dados = await consultar_api('/search/movie', {'query': nome, 'include_adult': 'false'})
        filmes = dados.get('results') or []
        await mostrar_filme(update, filmes[0] if filmes else None)
    except (requests.RequestException, ValueError):
        await update.message.reply_text('Erro ao consultar o TMDB. Tente novamente.')


async def recomendar(update, context):
    """Comandos /acao, /terror e /comedia."""
    limpar_modo(context, update.effective_user.id)
    genero = update.message.text.split()[0].split('@')[0][1:]
    if genero not in GENEROS:
        await update.message.reply_text('Gênero desconhecido.')
        return

    try:
        dados = await consultar_api(
            '/discover/movie',
            {'with_genres': GENEROS[genero], 'include_adult': 'false'},
        )
        filmes = dados.get('results') or []
        await mostrar_filme(update, random.choice(filmes) if filmes else None)
    except (requests.RequestException, ValueError):
        await update.message.reply_text('Erro ao consultar o TMDB. Tente novamente.')


async def recomendacao(update, context):
    """Inicia a escolha de um gênero por mensagem de texto."""
    definir_modo(context, update.effective_user.id, 'genero')
    generos = ', '.join(g.title() for g in GENEROS)
    await update.message.reply_text(
        f'Qual gênero você deseja?\n\nOpções: {generos}\n\n(/cancelar para sair)'
    )


async def cancelar(update, context):
    """Um só comando /cancelar: limpa qualquer pergunta pendente."""
    modo_anterior = limpar_modo(context, update.effective_user.id)
    if modo_anterior:
        await update.message.reply_text('Operação cancelada.')
    else:
        await update.message.reply_text('Não há nenhuma pergunta pendente.')


async def pedir_ano(update, context):
    definir_modo(context, update.effective_user.id, 'ano')
    await update.message.reply_text('📅 Digite o ano do filme (ex: 1999):\n\n(/cancelar para sair)')


async def pedir_decada(update, context):
    definir_modo(context, update.effective_user.id, 'decada')
    await update.message.reply_text('🕰️ Digite a década (ex: 80, 90 ou 2000):\n\n(/cancelar para sair)')


async def pedir_ator(update, context):
    definir_modo(context, update.effective_user.id, 'ator')
    await update.message.reply_text('🎭 Digite o nome de um ator ou atriz:\n\n(/cancelar para sair)')


async def pedir_parecido(update, context):
    definir_modo(context, update.effective_user.id, 'parecido')
    await update.message.reply_text('🎞️ Digite o nome de um filme que você gosta:\n\n(/cancelar para sair)')


async def sortear_da_lista(update, endereco, parametros, pagina_max=1):
    """Pede à API um filme aleatório com paginação corrigida."""
    try:
        filme = await sortear_filme(endereco, parametros, pagina_max)
        await mostrar_filme(update, filme)
    except (requests.RequestException, ValueError):
        await update.message.reply_text('Erro ao consultar o TMDB. Tente novamente.')


async def receber_genero(update, context, texto):
    """Mostra até 8 filmes de um gênero com nota >= 8 e pelo menos 1000 votos."""
    genero = normalizar(texto)
    if genero not in GENEROS:
        await update.message.reply_text('Não reconheci esse gênero 😕 Tente outro (ou /cancelar).')
        return

    try:
        dados = await consultar_api(
            '/discover/movie',
            {
                'with_genres': GENEROS[genero],
                'sort_by': 'vote_average.desc',
                'vote_average.gte': NOTA_MINIMA,
                'vote_count.gte': VOTOS_MINIMOS,
                'include_adult': 'false',
            },
        )
        filmes = (dados.get('results') or [])[:MAX_FILMES]
    except (requests.RequestException, ValueError):
        await update.message.reply_text('Erro ao consultar o TMDB. Tente novamente.')
        return  # Continua esperando: usuário pode tentar o gênero novamente.

    limpar_modo(context, update.effective_user.id)
    if not filmes:
        await update.message.reply_text('Não encontrei filmes bem avaliados desse gênero.')
        return

    await update.message.reply_text(f'⭐ Filmes de {genero.title()} com nota 8+/10:')
    for filme in filmes:
        titulo = filme.get('title') or 'Sem título'
        ano = (filme.get('release_date') or '')[:4] or 's/ data'
        nota = float(filme.get('vote_average') or 0)
        sinopse = filme.get('overview') or 'Sinopse indisponível.'
        mensagem = f'🎬 {titulo} ({ano})\n⭐ {nota:.1f}/10\n\n📝 {sinopse}'
        await update.message.reply_text(mensagem[:4000])


async def receber_busca(update, context, modo, texto):
    """Processa ano, década, ator e parecido e mantém o modo se houver erro."""
    usuario_id = update.effective_user.id

    try:
        if modo == 'ano':
            ano_maximo = datetime.now().year + 10
            if not (texto.isdigit() and len(texto) == 4 and 1900 <= int(texto) <= ano_maximo):
                await update.message.reply_text(
                    f'Ano inválido 😕 Digite um ano entre 1900 e {ano_maximo}, ou /cancelar.'
                )
                return
            limpar_modo(context, usuario_id)
            await sortear_da_lista(
                update, '/discover/movie',
                {'primary_release_year': texto, 'sort_by': 'vote_count.desc',
                 'vote_count.gte': 100, 'include_adult': 'false'},
                pagina_max=3,
            )

        elif modo == 'decada':
            inicio = interpretar_decada(texto)
            if inicio is None or not (1900 <= inicio <= datetime.now().year + 10):
                await update.message.reply_text('Década inválida 😕 Ex.: 90, 1990 ou 2000. (/cancelar)')
                return
            limpar_modo(context, usuario_id)
            await sortear_da_lista(
                update, '/discover/movie',
                {'primary_release_date.gte': f'{inicio}-01-01',
                 'primary_release_date.lte': f'{inicio + 9}-12-31',
                 'sort_by': 'vote_count.desc', 'vote_count.gte': 200,
                 'include_adult': 'false'},
                pagina_max=3,
            )

        elif modo == 'ator':
            pessoas = (await consultar_api(
                '/search/person', {'query': texto, 'include_adult': 'false'}
            )).get('results') or []
            if not pessoas:
                await update.message.reply_text('Não encontrei esse ator 😕 Tente outro nome ou /cancelar.')
                return
            pessoa = pessoas[0]
            limpar_modo(context, usuario_id)
            await update.message.reply_text(f"🎭 Filme com {pessoa.get('name', texto)}:")
            await sortear_da_lista(
                update, '/discover/movie',
                {'with_cast': pessoa['id'], 'sort_by': 'vote_count.desc',
                 'vote_count.gte': 100, 'include_adult': 'false'},
            )

        elif modo == 'parecido':
            filmes = (await consultar_api(
                '/search/movie', {'query': texto, 'include_adult': 'false'}
            )).get('results') or []
            if not filmes:
                await update.message.reply_text('Não encontrei esse filme 😕 Tente outro nome ou /cancelar.')
                return
            filme = filmes[0]
            limpar_modo(context, usuario_id)
            await update.message.reply_text(f"🎞️ Parecido com {filme.get('title', texto)}:")
            await sortear_da_lista(update, f"/movie/{filme['id']}/recommendations", {})

    except (requests.RequestException, ValueError, KeyError):
        await update.message.reply_text('Erro ao consultar o TMDB. Tente novamente.')


async def receber_texto(update, context):
    """ÚNICO handler para respostas digitadas após comandos interativos."""
    modo = obter_modo(context, update.effective_user.id)
    if not modo:
        return  # Texto comum fora de menus não precisa de resposta.

    texto = update.message.text.strip()
    if not texto:
        return
    if modo == 'genero':
        await receber_genero(update, context, texto)
    else:
        await receber_busca(update, context, modo, texto)


async def populares(update, context):
    limpar_modo(context, update.effective_user.id)
    await sortear_da_lista(update, '/movie/popular', {}, pagina_max=3)


async def top(update, context):
    limpar_modo(context, update.effective_user.id)
    await sortear_da_lista(update, '/movie/top_rated', {}, pagina_max=5)


async def em_cartaz(update, context):
    limpar_modo(context, update.effective_user.id)
    await sortear_da_lista(update, '/movie/now_playing', {'region': 'BR'})


async def breve(update, context):
    limpar_modo(context, update.effective_user.id)
    await sortear_da_lista(update, '/movie/upcoming', {'region': 'BR'})


async def aleatorio(update, context):
    limpar_modo(context, update.effective_user.id)
    await sortear_da_lista(
        update, '/discover/movie',
        {'sort_by': 'vote_count.desc', 'vote_count.gte': 500,
         'include_adult': 'false'},
        pagina_max=20,
    )
