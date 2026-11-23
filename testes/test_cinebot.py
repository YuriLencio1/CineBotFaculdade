"""Testes sem acessar Internet e sem precisar dos tokens reais."""

import asyncio
import json
import unittest
from unittest.mock import patch, Mock

import api_telegram
import bot
import comandos
import quiz


class TestesCineBot(unittest.TestCase):
    def setUp(self):
        bot.DADOS_DOS_CHATS.clear()

    def test_get_updates_usa_get_e_offset(self):
        resposta = Mock()
        resposta.json.return_value = {'ok': True, 'result': [{'update_id': 10}]}
        with patch.object(api_telegram.requests, 'get', return_value=resposta) as chamada:
            resultado = api_telegram.get_updates(9)
        self.assertEqual(resultado[0]['update_id'], 10)
        self.assertEqual(chamada.call_args.kwargs['params']['offset'], 9)
        self.assertEqual(json.loads(chamada.call_args.kwargs['params']['allowed_updates']), ['message', 'callback_query'])
        self.assertTrue(chamada.call_args.args[0].endswith('/getUpdates'))

    def test_send_message_usa_post_json(self):
        resposta = Mock()
        resposta.json.return_value = {'ok': True, 'result': {'chat': {'id': 5}, 'message_id': 22}}
        with patch.object(api_telegram.requests, 'post', return_value=resposta) as chamada:
            asyncio.run(api_telegram.enviar_mensagem(5, 'Olá!'))
        self.assertEqual(chamada.call_args.kwargs['json'], {'chat_id': 5, 'text': 'Olá!'})
        self.assertTrue(chamada.call_args.args[0].endswith('/sendMessage'))

    def test_erros_api_telegram_em_erro_http(self):
        resposta = Mock(status_code=400)
        resposta.json.return_value = {'ok': False, 'description': 'Bad Request'}
        with patch.object(api_telegram.requests, 'post', return_value=resposta):
            with self.assertRaises(api_telegram.TelegramError):
                asyncio.run(api_telegram.enviar_mensagem(5, 'teste'))

    def test_start_usa_o_menu(self):
        registro = []
        def api_falsa(metodo, dados=None, **kwargs):
            registro.append((metodo, dados))
            return {'chat': {'id': 44}, 'message_id': 33, 'text': dados.get('text', '')}
        with patch.object(api_telegram, 'chamar_api', side_effect=api_falsa):
            asyncio.run(bot.processar_atualizacao({
                'update_id': 1,
                'message': {'chat': {'id': 44}, 'message_id': 1, 'from': {'id': 12}, 'text': '/start'}
            }))
        self.assertEqual(registro[0][0], 'sendMessage')
        self.assertIn('MENU COMPLETO DO CINEBOT', registro[0][1]['text'])

    def test_busca_filme_pelo_nome(self):
        registro = []
        def api_falsa(metodo, dados=None, **kwargs):
            registro.append((metodo, dados))
            return {'chat': {'id': 44}, 'message_id': 33, 'text': dados.get('text', '')}
        async def consulta_falsa(*args, **kwargs):
            return {'results': [
                {'title': 'Interestelar', 'release_date': '2014-11-07', 'vote_average': 9.0,
                 'overview': 'Espaço.', 'poster_path': None}
            ]}
        with patch.object(api_telegram, 'chamar_api', side_effect=api_falsa), patch.object(
                comandos, 'consultar_api', side_effect=consulta_falsa):
            asyncio.run(bot.processar_atualizacao({
                'update_id': 2,
                'message': {'chat': {'id': 44}, 'message_id': 2, 'from': {'id': 12}, 'text': '/buscar Interestelar'}
            }))
        self.assertTrue(any('Interestelar' in dados['text'] for metodo, dados in registro if metodo == 'sendMessage'))

    def test_ano_com_resposta_digitada(self):
        registro = []
        def api_falsa(metodo, dados=None, **kwargs):
            registro.append((metodo, dados))
            return {'chat': {'id': 44}, 'message_id': 33, 'text': dados.get('text', '')}
        with patch.object(api_telegram, 'chamar_api', side_effect=api_falsa):
            asyncio.run(bot.processar_atualizacao({
                'update_id': 3,
                'message': {'chat': {'id': 44}, 'message_id': 3, 'from': {'id': 12}, 'text': '/ano'}
            }))
        self.assertEqual(bot.DADOS_DOS_CHATS[44]['modos'][12], 'ano')
        with patch.object(comandos, 'sortear_filme') as sorteio:
            async def retorna_filme(*args, **kwargs):
                return {'title': 'Filme escolhido', 'overview': 'Sinopse', 'poster_path': None}
            sorteio.side_effect = retorna_filme
            with patch.object(api_telegram, 'chamar_api', side_effect=api_falsa):
                asyncio.run(bot.processar_atualizacao({
                    'update_id': 4,
                    'message': {'chat': {'id': 44}, 'message_id': 4, 'from': {'id': 12}, 'text': '1999'}
                }))
        self.assertTrue(any('Filme escolhido' in dados['text'] for metodo, dados in registro if metodo == 'sendMessage'))
        self.assertIsNone(bot.DADOS_DOS_CHATS[44]['modos'].get(12))

    def test_quiz_envia_botoes_e_recebe_resposta(self):
        registro = []
        def api_falsa(metodo, dados=None, **kwargs):
            registro.append((metodo, dados))
            return {'chat': {'id': 44}, 'message_id': 555, 'text': dados.get('text', '')}

        pergunta_api = {'response_code': 0, 'results': [{
            'question': 'Question?', 'correct_answer': 'Right',
            'incorrect_answers': ['Wrong 1', 'Wrong 2', 'Wrong 3'], 'difficulty': 'easy'
        }]}
        with patch.object(api_telegram, 'chamar_api', side_effect=api_falsa), patch.object(
                quiz, '_buscar_pergunta_sincrona', return_value=pergunta_api), patch.object(
                quiz, '_traduzir_sincrono', return_value='Pergunta?'):
            asyncio.run(bot.processar_atualizacao({
                'update_id': 5, 'message': {
                    'chat': {'id': 44}, 'message_id': 5, 'from': {'id': 12}, 'text': '/quiz'}
            }))
            botoes = registro[-1][1]['reply_markup']['inline_keyboard'][0]
            indice_correto = bot.DADOS_DOS_CHATS[44]['quizzes'][555]['opcoes'].index('Right')
            self.assertEqual(len(botoes), 4)
            asyncio.run(bot.processar_atualizacao({
                'update_id': 6, 'callback_query': {
                    'id': 'cb1', 'from': {'id': 12}, 'data': f'quiz:{indice_correto}',
                    'message': {'chat': {'id': 44}, 'message_id': 555, 'text': 'Pergunta?'}
                }
            }))
        self.assertIn('answerCallbackQuery', [metodo for metodo, _ in registro])
        editado = next(dados for metodo, dados in registro if metodo == 'editMessageText')
        self.assertIn('Acertou!', editado['text'])
        self.assertEqual(bot.DADOS_DOS_CHATS[44]['placares'][12], [1, 1])

    def test_outro_usuario_nao_pode_responder_quiz(self):
        bot.DADOS_DOS_CHATS[44] = {'quizzes': {555: {
            'correta': 'R', 'opcoes': ['R','A','B','C'], 'criador_id': 12
        }}}
        registro = []
        def api_falsa(metodo, dados=None, **kwargs):
            registro.append((metodo, dados))
            return True
        with patch.object(api_telegram, 'chamar_api', side_effect=api_falsa):
            asyncio.run(bot.processar_atualizacao({
                'update_id': 7, 'callback_query': {
                    'id': 'cb2', 'from': {'id': 42}, 'data': 'quiz:0',
                    'message': {'chat': {'id': 44}, 'message_id': 555, 'text': 'Pergunta?'}
                }
            }))
        self.assertEqual([m for m, d in registro], ['answerCallbackQuery'])
        self.assertIn('Somente', registro[0][1]['text'])


if __name__ == '__main__':
    unittest.main()
