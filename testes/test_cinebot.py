"""Testes offline de lógica: sem chamadas reais ao Telegram ou às APIs."""

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

# Permite executar: python -m unittest discover -s testes -v
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import api_filmes
import comandos
import estados
import quiz as modulo_quiz


class MensagemFalsa:
    def __init__(self, texto=''):
        self.text = texto
        self.respostas = []
        self.message_id = 77

    async def reply_text(self, texto, **kwargs):
        self.respostas.append(('texto', texto))
        return SimpleNamespace(message_id=77, text=texto)

    async def reply_photo(self, photo, caption, **kwargs):
        self.respostas.append(('foto', caption))
        return SimpleNamespace(message_id=77)


class AtualizacaoFalsa:
    def __init__(self, texto='', usuario_id=10):
        self.message = MensagemFalsa(texto)
        self.effective_user = SimpleNamespace(id=usuario_id)
        self.effective_chat = SimpleNamespace(id=20)


class ContextoFalso:
    def __init__(self):
        self.chat_data = {}
        self.args = []


class TestarUtilitarios(unittest.TestCase):
    def test_normalizar_acentos(self):
        self.assertEqual(comandos.normalizar(' Ficção Científica '), 'ficcao cientifica')

    def test_interpretar_decada(self):
        self.assertEqual(comandos.interpretar_decada('90'), 1990)
        self.assertEqual(comandos.interpretar_decada('anos 80'), 1980)
        self.assertEqual(comandos.interpretar_decada('2000'), 2000)
        self.assertIsNone(comandos.interpretar_decada('não sei'))

    def test_estado_separado_por_usuario(self):
        contexto = ContextoFalso()
        estados.definir_modo(contexto, 10, 'genero')
        estados.definir_modo(contexto, 11, 'ator')
        self.assertEqual(estados.obter_modo(contexto, 10), 'genero')
        self.assertEqual(estados.obter_modo(contexto, 11), 'ator')
        estados.limpar_modo(contexto, 10)
        self.assertIsNone(estados.obter_modo(contexto, 10))
        self.assertEqual(estados.obter_modo(contexto, 11), 'ator')


class TestarAPI(unittest.IsolatedAsyncioTestCase):
    async def test_sorteio_restringe_pagina_ao_total_disponivel(self):
        resultado = {'total_pages': 1, 'results': [{'title': 'Teste A'}]}
        with patch('api_filmes.consultar_api', new_callable=AsyncMock, return_value=resultado) as consulta:
            filme = await api_filmes.sortear_filme('/movie/popular', {}, pagina_max=20)
        self.assertEqual(filme['title'], 'Teste A')
        consulta.assert_awaited_once()
        self.assertEqual(consulta.call_args.args[1]['page'], 1)

    async def test_sorteio_consulta_pagina_valida(self):
        primeira = {'total_pages': 3, 'results': [{'title': 'Primeiro'}]}
        segunda = {'total_pages': 3, 'results': [{'title': 'Segundo'}]}
        with patch('api_filmes.consultar_api', new_callable=AsyncMock, side_effect=[primeira, segunda]) as consulta, \
                patch('api_filmes.random.randint', return_value=2):
            filme = await api_filmes.sortear_filme('/movie/popular', {}, pagina_max=20)
        self.assertEqual(filme['title'], 'Segundo')
        self.assertEqual(consulta.await_args_list[1].args[1]['page'], 2)

    async def test_sorteio_retrocede_se_pagina_vier_vazia(self):
        primeira = {'total_pages': 3, 'results': [{'title': 'Primeiro'}]}
        segunda = {'total_pages': 3, 'results': []}
        with patch('api_filmes.consultar_api', new_callable=AsyncMock, side_effect=[primeira, segunda]), \
                patch('api_filmes.random.randint', return_value=2):
            filme = await api_filmes.sortear_filme('/movie/popular', {}, pagina_max=3)
        self.assertEqual(filme['title'], 'Primeiro')


class TestarComandos(unittest.IsolatedAsyncioTestCase):
    async def test_cancelar_limpa_estado(self):
        contexto = ContextoFalso()
        atualizacao = AtualizacaoFalsa()
        estados.definir_modo(contexto, 10, 'genero')
        await comandos.cancelar(atualizacao, contexto)
        self.assertIsNone(estados.obter_modo(contexto, 10))
        self.assertIn('cancelada', atualizacao.message.respostas[0][1])

    async def test_trocar_pergunta_substitui_modo_anterior(self):
        contexto = ContextoFalso()
        atualizacao = AtualizacaoFalsa()
        await comandos.recomendacao(atualizacao, contexto)
        await comandos.pedir_ator(atualizacao, contexto)
        self.assertEqual(estados.obter_modo(contexto, 10), 'ator')

    async def test_responder_ano_valido_chama_sorteio(self):
        contexto = ContextoFalso()
        atualizacao = AtualizacaoFalsa('1999')
        await comandos.pedir_ano(atualizacao, contexto)
        with patch('comandos.sortear_da_lista', new_callable=AsyncMock) as sortear:
            await comandos.receber_texto(atualizacao, contexto)
        sortear.assert_awaited_once()
        self.assertIsNone(estados.obter_modo(contexto, 10))

    async def test_ano_invalido_mantem_pergunta_pendente(self):
        contexto = ContextoFalso()
        atualizacao = AtualizacaoFalsa('19xx')
        await comandos.pedir_ano(atualizacao, contexto)
        await comandos.receber_texto(atualizacao, contexto)
        self.assertEqual(estados.obter_modo(contexto, 10), 'ano')

    async def test_buscar_sem_argumento_orienta_usuario(self):
        contexto = ContextoFalso()
        atualizacao = AtualizacaoFalsa('/buscar')
        await comandos.buscar(atualizacao, contexto)
        self.assertIn('/buscar Interestelar', atualizacao.message.respostas[0][1])


class QueryFalsa:
    def __init__(self, usuario_id, indice):
        self.message = SimpleNamespace(message_id=77, text='Pergunta original')
        self.from_user = SimpleNamespace(id=usuario_id)
        self.data = f'quiz:{indice}'
        self.avisos = []
        self.edicoes = []

    async def answer(self, texto=None, **kwargs):
        self.avisos.append(texto)

    async def edit_message_text(self, texto):
        self.edicoes.append(texto)


class TestarQuiz(unittest.IsolatedAsyncioTestCase):
    async def test_criar_quiz_sem_acessar_internet(self):
        contexto = ContextoFalso()
        atualizacao = AtualizacaoFalsa('/quiz')
        pergunta = {
            'response_code': 0,
            'results': [{
                'question': 'Movie question?',
                'correct_answer': 'A',
                'incorrect_answers': ['B', 'C', 'D'],
                'difficulty': 'easy',
            }],
        }
        with patch('quiz._buscar_pergunta_sincrona', return_value=pergunta), \
                patch('quiz._traduzir_sincrono', return_value='Pergunta de cinema?'):
            await modulo_quiz.quiz(atualizacao, contexto)
        self.assertEqual(contexto.chat_data['quizzes'][77]['criador_id'], 10)
        self.assertIn('Pergunta de cinema?', atualizacao.message.respostas[0][1])

    async def test_quiz_restringe_ao_dono_e_contabiliza_acerto(self):
        contexto = ContextoFalso()
        contexto.chat_data['quizzes'] = {
            77: {'criador_id': 10, 'opcoes': ['A', 'B', 'C', 'D'], 'correta': 'C'}
        }
        outro = QueryFalsa(usuario_id=11, indice=2)
        await modulo_quiz.responder_quiz(SimpleNamespace(callback_query=outro), contexto)
        self.assertIn(77, contexto.chat_data['quizzes'])
        self.assertFalse(outro.edicoes)

        dono = QueryFalsa(usuario_id=10, indice=2)
        await modulo_quiz.responder_quiz(SimpleNamespace(callback_query=dono), contexto)
        self.assertNotIn(77, contexto.chat_data['quizzes'])
        self.assertEqual(contexto.chat_data['placares'][10], [1, 1])
        self.assertIn('Acertou', dono.edicoes[0])


if __name__ == '__main__':
    unittest.main()
