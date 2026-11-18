# CineBot — versão organizada e corrigida

**É um único bot do Telegram**, que consulta três serviços externos:

- **TMDB**: pesquisa, listagem e recomendação de filmes.
- **OpenTDB**: perguntas do quiz de filmes.
- **MyMemory**: tradução de perguntas do quiz para português.

Todo o acesso HTTP continua sendo feito com **`requests.get()` (GET)**, conforme a atividade. As chamadas HTTP são executadas por `asyncio.to_thread()` para evitar bloquear o processamento de mensagens do Telegram.

## Etapas do projeto

| Etapa | Arquivo | Para estudar |
|---|---|---|
| 1 | `config.py` | Variáveis do `.env`, certificados SSL, IDs dos gêneros e constantes. |
| 2 | `estados.py` | Controla a pergunta pendente de cada usuário em cada chat. |
| 3 | `api_filmes.py` | Faz GET à TMDB, valida erros e escolhe páginas existentes. |
| 4 | `comandos.py` | Pesquisa, menu, recomendações, interações de ano/década/ator/parecido e respostas ao Telegram. |
| 5 | `quiz.py` | Quiz com OpenTDB, tradução com MyMemory, botões e pontuação individual. |
| 6 | `bot.py` | Importa as funções, cadastra os handlers e inicia um único bot. |
| 7 | `testes/test_cinebot.py` | Testes locais automatizados sem consultar APIs reais. |

**Fluxo:** Usuário → `bot.py` → `comandos.py` ou `quiz.py` → `api_filmes.py`/APIs → resposta no Telegram. `estados.py` auxilia nos comandos com respostas digitadas.

## Como executar no Windows (PowerShell)

1. **Extraia o ZIP** e abra a pasta `CineBot_Organizado` no VS Code.
2. Abra o terminal do VS Code nessa pasta.
3. Crie o ambiente virtual:

   ```powershell
   py -m venv .venv
   ```

4. Instale as dependências usando o Python do ambiente, sem precisar ativá-lo:

   ```powershell
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   ```

5. Crie seu `.env` com base no modelo:

   ```powershell
   Copy-Item .env.example .env
   notepad .env
   ```

6. Substitua os valores pelos seus tokens verdadeiros. No TMDB, use o **token de leitura de API (Bearer)**, não a chave API v3 tradicional.
7. Inicie o bot:

   ```powershell
   .\.venv\Scripts\python.exe bot.py
   ```

8. No Telegram, abra seu bot e envie `/start`.

**Se `py` não funcionar:** use `python -m venv .venv` na etapa 3. O método acima não requer alterar a política de execução de scripts do PowerShell.

## Testar antes de executar

Depois de instalar as dependências:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s testes -v
```

Os testes substituem as respostas das APIs por dados fictícios; não é necessário ter tokens válidos para testar as funções e os fluxos locais. Para confirmar o funcionamento real, você ainda precisa configurar o `.env` e testar os comandos no Telegram.

## Todos os comandos preservados

| Comando | O que faz |
|---|---|
| `/start`, `/ajuda`, `/menu` | Mostra o menu. |
| `/buscar Interestelar` | Busca um filme pelo nome. |
| `/acao`, `/terror`, `/comedia` | Sorteia uma recomendação do gênero. |
| `/recomendacao` | Pergunta o gênero e lista até 8 filmes com nota >= 8 e pelo menos 1000 votos. |
| `/ano` | Pergunta o ano e sorteia um filme. |
| `/decada` | Pergunta a década e sorteia um filme. |
| `/ator` | Pergunta o nome do artista e recomenda um filme. |
| `/parecido` | Pergunta o filme de referência e recomenda um parecido. |
| `/populares`, `/top`, `/emcartaz`, `/breve`, `/aleatorio` | Sorteiam filmes em diferentes seleções. |
| `/quiz` | Mostra uma pergunta de cinema com alternativas em botões. |
| `/cancelar` | Cancela a pergunta de texto que estiver pendente. |

## Problemas corrigidos

1. **Um só estado por usuário/chat**: `estados.py` substitui `aguardando_genero` e `aguardando_busca`. Iniciar outro menu substitui o anterior, sem as duas respostas se misturarem.
2. **Um único `/cancelar`**: cancela qualquer pergunta pendente, sem handlers repetidos em diferentes grupos.
3. **Um único handler de textos**: `receber_texto()` identifica o tipo de pergunta a responder.
4. **`requests` sem bloquear o bot**: requisições executadas em threads, mantendo o uso obrigatório da biblioteca.
5. **Sorteio em páginas existentes**: consulta a primeira página para descobrir `total_pages`, respeitando o máximo disponível e usando a primeira página se a página sorteada vier vazia.
6. **Conteúdo adulto desabilitado** nas consultas de pesquisa e recomendações do TMDB.
7. **Quiz com pontuação individual**: em grupo, somente o usuário que abriu uma pergunta pode respondê-la; os pontos não são compartilhados.
8. **Limites de mensagens**: separa a sinopse da foto quando ela ultrapassa o limite de legendas do Telegram.
9. **Validação de ano/década**: trata entradas inválidas sem sair da pergunta pendente.
10. **Arquivos menores e organizados**, com `.env` no `.gitignore` para evitar expor tokens no GitHub.

## Observações

- As notas são **de 0 a 10** na TMDB. A versão antiga chamava nota >= 8 de “5 estrelas”, mas essa classificação era ambígua; agora os textos mostram a nota real.
- `top` e `populares` **sorteiam um filme** dos resultados, como no arquivo original; não retornam uma lista completa.
- As perguntas e os placares ficam **apenas na memória do bot**: reiniciar o processo apaga esses dados. Isso é adequado para a versão simples de faculdade, mas não substitui um banco de dados.
- A MyMemory pode falhar ou atingir limite de uso; nesse caso a pergunta do quiz aparece em inglês, sem travar o bot. As alternativas permanecem como vieram da OpenTDB.
- Não inclua seu `.env` ao compartilhar o projeto ou enviar para o GitHub.
