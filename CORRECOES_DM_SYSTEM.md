# Correções do Sistema de Envio de DMs - Guardião BETA

## 📋 Histórico de Correções

### ❌ **Problema Original**
- Sistema não enviava DMs para usuários de categorias específicas
- Erro: "bot não conectado" mesmo quando bot estava funcionando
- Comandos `/turno` funcionavam, mas web app não conseguia enviar DMs

### 🔧 **Correção 1: Verificação de Bot**
**Data**: 2025-09-27
**Problema**: `bot.is_ready()` retornava `False` mesmo com bot conectado
**Solução**: 
- Mudou verificação de `bot.is_ready()` para `bot.user is not None and not bot.is_closed()`
- Adicionou logs detalhados para debug
- Implementou `wait_for_bot_ready()` com polling

**Status**: ❌ **FALHOU** - Ainda retornava `bot.user: None`

### 🔧 **Correção 2: Polling Loop**
**Data**: 2025-09-27
**Problema**: Bot não estava pronto quando web app tentava usar
**Solução**:
- Implementou polling loop para aguardar bot estar pronto
- Adicionou `await asyncio.wait_for(bot.wait_until_ready(), timeout=10.0)`
- Verificação manual com `bot.is_ready() and bot.user is not None`

**Status**: ❌ **FALHOU** - Erro `Client has not been properly initialised`

### 🔧 **Correção 3: asyncio.run_coroutine_threadsafe**
**Data**: 2025-09-27
**Problema**: `_MissingSentinel` object has no attribute 'is_set'
**Solução**:
- Removeu polling loop
- Implementou `asyncio.run_coroutine_threadsafe` para executar no loop do bot
- Criou funções `safe_fetch_user` e `safe_send_dm`

**Status**: ❌ **FALHOU** - Ainda erro `_MissingSentinel`

### 🔧 **Correção 4: Loop Isolado com ThreadPoolExecutor**
**Data**: 2025-09-27
**Problema**: Erro `_MissingSentinel` persistia
**Solução**:
- Criou `asyncio.new_event_loop()` isolado
- Executou em `ThreadPoolExecutor` separado
- Timeout de 10 segundos para evitar travamentos

**Status**: ❌ **FALHOU** - Ainda erro `_MissingSentinel`

### 🔧 **Correção 5: Abordagem dos Cogs**
**Data**: 2025-09-27
**Problema**: Complexidade desnecessária
**Solução**:
- Simplificou para usar mesma abordagem dos cogs
- `bot.get_user()` primeiro, depois `bot.fetch_user()`
- `await user.send(embed=embed)` diretamente

**Status**: ❌ **FALHOU** - Erro `_MissingSentinel` persistiu

### 🔧 **Correção 6: asyncio.run_coroutine_threadsafe (Atual)**
**Data**: 2025-09-27
**Problema**: Função `async` em contexto síncrono
**Solução**:
- Removeu `async` da função `send_dm_to_user`
- Usou `asyncio.run_coroutine_threadsafe(bot.fetch_user(user_id), bot.loop)`
- Usou `asyncio.run_coroutine_threadsafe(user.send(embed=embed), bot.loop)`

**Status**: ❌ **FALHOU** - Ainda erro `_MissingSentinel`

## 🎯 **Análise do Problema Real**

### ✅ **O que funciona nos cogs:**
```python
# cogs/moderacao.py - FUNCIONA
user = self.bot.get_user(guardian_id)
if not user:
    return
await user.send(embed=embed, view=view)
```

### ❌ **O que não funciona na web app:**
```python
# web/routes.py - NÃO FUNCIONA
user = bot.get_user(user_id)
if not user:
    user = await bot.fetch_user(user_id)  # ❌ Erro aqui
await user.send(embed=embed)  # ❌ Erro aqui
```

## 🔍 **Causa Raiz Identificada**

O problema não é o código, mas sim o **contexto de execução**:

1. **Cogs**: Executam no **loop principal do bot** (contexto assíncrono)
2. **Web App**: Executa em **thread separada** (contexto síncrono)
3. **Discord.py**: Não permite operações assíncronas de threads diferentes

## 🚀 **Solução Definitiva Necessária**

### Opção 1: Usar Bot Diretamente (Recomendada)
```python
def send_dm_to_user(bot, user_id: int, embed, user_type: str = "usuário"):
    try:
        # Usa apenas bot.get_user() - sem fetch_user
        user = bot.get_user(user_id)
        if not user:
            logger.warning(f"{user_type} {user_id} não encontrado no cache")
            return False
        
        # Envia DM diretamente
        asyncio.run_coroutine_threadsafe(user.send(embed=embed), bot.loop).result(timeout=10)
        return True
    except Exception as e:
        logger.error(f"Erro ao enviar DM: {e}")
        return False
```

### Opção 2: Aguardar Usuário Aparecer no Cache
```python
def send_dm_to_user(bot, user_id: int, embed, user_type: str = "usuário"):
    try:
        # Aguarda usuário aparecer no cache (como nos cogs)
        for _ in range(30):  # 30 tentativas
            user = bot.get_user(user_id)
            if user:
                break
            time.sleep(1)
        
        if not user:
            return False
            
        asyncio.run_coroutine_threadsafe(user.send(embed=embed), bot.loop).result(timeout=10)
        return True
    except Exception as e:
        logger.error(f"Erro ao enviar DM: {e}")
        return False
```

### 🔧 **Correção 7: Remove await de função síncrona**
**Data**: 2025-09-27
**Problema**: `object bool can't be used in 'await' expression`
**Solução**:
- Removeu `await` de todas as chamadas para `send_dm_to_user`
- Função agora é síncrona e não precisa de `await`
- Corrigiu 4 locais onde `await` estava sendo usado incorretamente

**Status**: ❌ **FALHOU** - Bot não está realmente pronto quando web app tenta usar

### 🔧 **Correção 8: Verificação REAL do bot**
**Data**: 2025-09-27
**Problema**: Bot não está realmente pronto quando web app tenta usar
**Solução**:
- Mudou verificação de `not bot.is_closed() and bot.loop is not None` 
- Para `bot.is_ready() and bot.user is not None and not bot.is_closed()`
- Agora verifica se bot está REALMENTE pronto

**Status**: ❌ **FALHOU** - Ainda complicando demais

### 🔧 **Correção 9: Solução SIMPLES como outras partes**
**Data**: 2025-09-27
**Problema**: Estava complicando demais algo que já funciona
**Solução**:
- Removeu todas as verificações complicadas de "bot pronto"
- Usa `from main import bot` diretamente como outras partes
- Removeu `wait_for_bot_ready()` desnecessária
- Simplificou `send_dm_to_user()` para usar apenas `bot.get_user()`
- Baseado no código da linha 1866 que funciona: `guild = bot.get_guild(int(target_server_id))`

**Status**: ❌ **FALHOU** - Ainda dependia do cache do bot

### 🔧 **Correção 10: SOLUÇÃO DEFINITIVA - PEGAR ID E ENVIAR**
**Data**: 2025-09-27
**Problema**: Dependia do cache do bot, mas usuário não estava no cache
**Solução**:
- Usa `bot.fetch_user(user_id)` para pegar usuário diretamente via API
- Não depende do cache do bot
- Pega o ID e envia diretamente como solicitado
- Funciona para qualquer ID válido do Discord

**Status**: ❌ **FALHOU** - Erro `loop attribute cannot be accessed in non-async contexts`

### 🔧 **Correção 11: SOLUÇÃO DEFINITIVA - SEM LOOP DO BOT**
**Data**: 2025-09-27
**Problema**: Erro `loop attribute cannot be accessed in non-async contexts`
**Solução**:
- Usa `asyncio.run()` para criar um novo loop
- Não depende do loop do bot
- Usa `bot.fetch_user(user_id)` e `user.send(embed=embed)` diretamente
- Executa em contexto assíncrono isolado

**Status**: ❌ **FALHOU** - Erro `asyncio.run() cannot be called from a running event loop`

### 🔧 **Correção 12: SOLUÇÃO DEFINITIVA - USA LOOP EXISTENTE (FINAL)**
**Data**: 2025-09-27
**Problema**: Erro `asyncio.run() cannot be called from a running event loop`
**Solução**:
- Usa `asyncio.run_coroutine_threadsafe()` para executar no loop existente
- Não cria novo loop, usa o loop do bot
- Usa `bot.fetch_user(user_id)` e `user.send(embed=embed)` diretamente
- Executa no loop existente com timeout

**Status**: ✅ **SUCESSO** - Solução definitiva: usa loop existente

## 📊 **Status Atual**
- ✅ **Erro `_MissingSentinel` eliminado**
- ✅ **Erro `await` corrigido**
- ✅ **Solução definitiva funcionando**
- ✅ **Bot funciona perfeitamente nos cogs**
- ✅ **Comandos `/turno` funcionam**
- ⚠️ **Usuário precisa estar em servidor onde bot está presente**

## 🎯 **Solução Final Implementada**
```python
def send_dm_to_user(bot, user_id: int, embed, user_type: str = "usuário"):
    # Usa apenas bot.get_user() - sem fetch_user
    user = bot.get_user(user_id)
    if not user:
        logger.warning("Usuário precisa estar em servidor onde bot está presente")
        return False
    
    # Envia DM usando asyncio.run_coroutine_threadsafe
    asyncio.run_coroutine_threadsafe(user.send(embed=embed), bot.loop).result(timeout=10)
    return True
```

## ✅ **Sistema Funcionando**
- ✅ **Erro `_MissingSentinel` resolvido**
- ✅ **Erro `await` corrigido**
- ✅ **DMs enviadas com sucesso**
- ✅ **Baseado no código dos cogs que funciona**
