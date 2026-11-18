"""Etapa 2: um único controle de perguntas pendentes por usuário e chat."""


def definir_modo(context, usuario_id, modo):
    """Salva o tipo de resposta esperado: genero, ano, decada, ator ou parecido."""
    context.chat_data.setdefault('modos', {})[usuario_id] = modo


def obter_modo(context, usuario_id):
    """Devolve o modo atual ou None, caso não exista pergunta pendente."""
    return context.chat_data.get('modos', {}).get(usuario_id)


def limpar_modo(context, usuario_id):
    """Remove somente a pergunta pendente deste usuário neste chat."""
    return context.chat_data.get('modos', {}).pop(usuario_id, None)
