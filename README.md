# CineBot — Telegram por API HTTP direta (sem biblioteca do Telegram)

Projeto acadêmico de bot de filmes em Python. O programa **não usa `python-telegram-bot`, `telebot` nem `telegram.ext`**: ele se conecta diretamente à [API HTTP oficial do Telegram](https://core.telegram.org/bots/api) com a biblioteca `requests`.

Os conteúdos são consultados em APIs externas:

- **TMDB:** busca e recomendação de filmes, pôsteres e sinopses.
- **OpenTDB:** perguntas do quiz de cinema.
- **MyMemory:** tradução das perguntas (se não funcionar, usa a pergunta original).

## Como funciona

```text
Usuário escreve /buscar Interestelar no Telegram
            ↓
bot.py recebe JSON por GET /getUpdates
            ↓
comandos.py interpreta /buscar e chama api_filmes.py
            ↓
api_filmes.py faz GET https://api.themoviedb.org/3/search/movie
            ↓
api_telegram.py envia a resposta por POST /sendMessage ou /sendPhoto
            ↓
Usuário recebe título, nota, ano e sinopse
```

**Métodos HTTP usados para o Telegram:**

| Método da API | Uso | Requisição Python |
|---|---|---|
| `getUpdates` | Recebe mensagens e cliques dos botões | `requests.get(...)` |
| `sendMessage` | Responde com texto e teclados | `requests.post(..., json=...)` |
| `sendPhoto` | Envia o pôster de um filme | `requests.post(..., json=...)` |
| `answerCallbackQuery` | Confirma o clique no quiz | `requests.post(..., json=...)` |
| `editMessageText` | Mostra o resultado do quiz | `requests.post(..., json=...)` |

O Telegram aceita ambos os métodos HTTP. Este projeto usa GET para consultar mensagens e POST para enviar/editar respostas. **Todas as consultas de filmes à TMDB continuam usando GET**, conforme a atividade.

## Arquivos do projeto

| Arquivo | Responsabilidade |
|---|---|
| `bot.py` | Executa o polling e direciona comandos e cliques aos módulos |
| `api_telegram.py` | Faz as chamadas HTTP diretas ao Telegram e interpreta JSON |
| `api_filmes.py` | Faz requisições GET à API TMDB |
| `comandos.py` | Busca, recomendações, filtros e menu |
| `quiz.py` | OpenTDB, MyMemory, botões e placar individual |
| `estados.py` | Lembra o que cada usuário precisa responder |
| `config.py` | Tokens, IDs de gêneros e configurações |
| `.env.example` | Modelo para configurar tokens (não contém segredos) |
| `requirements.txt` | Bibliotecas necessárias (nenhuma biblioteca do Telegram) |
| `testes/` | Testes locais sem tokens reais |

As classes `Mensagem`, `Atualizacao` e `Callback` de `api_telegram.py` são **classes comuns escritas para este projeto**, e **não** fazem parte de nenhuma biblioteca do Telegram. Elas apenas facilitam trabalhar com os dicionários JSON recebidos pela API.

## Como instalar e executar no Windows (PowerShell)

1. Extraia a pasta `CineBot_API_Direta` e abra no VS Code.
2. No terminal, crie o ambiente virtual:

```powershell
python -m venv .venv
```

3. Instale as dependências usando o Python do ambiente. **Não é necessário ativar** o ambiente (evita o erro de execução de scripts do PowerShell):

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

4. Faça uma cópia do modelo de configuração e edite os tokens:

```powershell
Copy-Item .env.example .env
notepad .env
```

Seu `.env` deve conter:

```dotenv
TELEGRAM_TOKEN=TOKEN_REAL_CRIADO_NO_BOTFATHER
TMDB_TOKEN=TOKEN_BEARER_DE_LEITURA_DA_TMDB
```

5. Inicie o bot:

```powershell
.\.venv\Scripts\python.exe bot.py
```

6. No Telegram, abra seu bot e envie `/start`.

**Importante:** deixe o terminal do bot aberto. O polling só funciona enquanto o programa estiver executando. Não inicie duas instâncias do mesmo bot ao mesmo tempo. Se já houver um webhook configurado para esse token, o `getUpdates` não funciona até remover o webhook. Não compartilhe seu `.env` nem publique tokens no GitHub.

## Comandos preservados

| Comando | O que faz |
|---|---|
| `/start`, `/ajuda`, `/menu` | Exibe o menu |
| `/buscar Interestelar` | Busca um filme pelo nome |
| `/acao`, `/terror`, `/comedia` | Recomenda um filme do gênero |
| `/recomendacao` | Pergunta o gênero e mostra até 8 filmes bem avaliados |
| `/ano` | Pede um ano e sorteia um filme |
| `/decada` | Pede uma década e sorteia um filme |
| `/ator` | Pede ator ou atriz e recomenda um filme |
| `/parecido` | Pede um filme e recomenda outro parecido |
| `/populares` | Sorteia um dos populares |
| `/top` | Sorteia um dos mais bem avaliados |
| `/emcartaz` | Recomenda um filme em cartaz |
| `/breve` | Recomenda um próximo lançamento |
| `/aleatorio` | Sorteia uma recomendação surpresa |
| `/quiz` | Abre pergunta com botões A/B/C/D |
| `/cancelar` | Cancela pergunta pendente |

## Testes

Para verificar as funções sem usar APIs reais, rode:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s testes -v
```

Os testes simulam respostas da API. A comunicação externa real com Telegram e TMDB deve ser confirmada manualmente com os tokens no `.env`.

## Observações

- O código usa **long polling** com `getUpdates` (aguarda mensagens por até 25 segundos a cada consulta).
- O parâmetro `offset` impede que o bot processe repetidamente atualizações que já recebeu.
- Os botões são objetos JSON, não classes `InlineKeyboardButton`.
- Modos de pergunta e pontuação do quiz ficam na memória: reiniciar o programa zera essas informações.
- Se o Telegram não conseguir buscar a imagem do pôster, o bot tenta enviar apenas o texto.
- Algumas mensagens podem demorar durante consultas de APIs externas, pois o exemplo processa as atualizações sequencialmente; isso mantém o código fácil de estudar.
