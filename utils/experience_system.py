"""
Sistema de Experiência - Guardião BETA
Gerencia títulos e ranks baseados na experiência dos usuários
"""

from typing import Dict, Tuple


def get_experience_rank(xp: int) -> str:
    """
    Determina o título de experiência baseado na quantidade de XP
    
    Args:
        xp: Pontos de experiência do usuário
        
    Returns:
        Título correspondente ao nível de experiência
    """
    # Sistema de ranks baseado em faixas de experiência
    experience_ranks = [
        (0, "Novato"),
        (101, "Aprendiz"),
        (201, "Iniciante"),
        (301, "Recruta"),
        (401, "Principiante"),
        (601, "Observador"),
        (801, "Vigia"),
        (1001, "Aspirante"),
        (1301, "Cadete"),
        (1601, "Sentinela"),
        (2001, "Patrulheiro"),
        (2601, "Agente"),
        (3201, "Defensor"),
        (3801, "Escudeiro"),
        (4601, "Experiente"),
        (5501, "Protetor"),
        (6501, "Guardião Júnior"),
        (7801, "Cavaleiro"),
        (9001, "Profissional"),
        (10501, "Vanguarda"),
        (12001, "Veterano"),
        (14501, "Elite"),
        (17001, "Mestre de Campo"),
        (20001, "Estrategista"),
        (23501, "Guardião Mestre"),
        (27001, "Comandante"),
        (31001, "Chefe de Patrulha"),
        (35501, "Protetor Supremo"),
        (40001, "General da Guarda"),
        (45501, "Guardião de Ferro"),
        (51001, "Guardião de Aço"),
        (57501, "Guardião Lendário"),
        (64001, "Guardião Épico"),
        (71001, "Guardião Real"),
        (78501, "Guardião Ancião"),
        (86001, "Guardião Supremo"),
        (94001, "Guardião Sagrado"),
        (102001, "Guardião Imortal"),
        (110001, "Guardião Celestial"),
        (118001, "Guardião das Sombras"),
        (126001, "Guardião da Luz"),
        (134501, "Guardião Cósmico"),
        (143001, "Guardião Estelar"),
        (152001, "Guardião Dimensional"),
        (161501, "Guardião Supremo de Elite"),
        (171001, "Guardião da Eternidade"),
        (181001, "Guardião Infinito"),
        (191001, "Guardião Divino"),
        (200001, "Guardião Absoluto"),
        (225001, "Guardião Eterno")
    ]
    
    # Encontra o título correspondente
    current_rank = "Novato"
    for min_xp, rank in experience_ranks:
        if xp >= min_xp:
            current_rank = rank
        else:
            break
    
    return current_rank


def get_experience_progress(xp: int) -> Tuple[int, int, float]:
    """
    Calcula o progresso do usuário no rank atual
    
    Args:
        xp: Pontos de experiência do usuário
        
    Returns:
        Tupla com (xp_atual, xp_proximo_rank, porcentagem_progresso)
    """
    # Faixas de experiência (mesmas do get_experience_rank)
    experience_ranks = [
        (0, "Novato"),
        (101, "Aprendiz"),
        (201, "Iniciante"),
        (301, "Recruta"),
        (401, "Principiante"),
        (601, "Observador"),
        (801, "Vigia"),
        (1001, "Aspirante"),
        (1301, "Cadete"),
        (1601, "Sentinela"),
        (2001, "Patrulheiro"),
        (2601, "Agente"),
        (3201, "Defensor"),
        (3801, "Escudeiro"),
        (4601, "Experiente"),
        (5501, "Protetor"),
        (6501, "Guardião Júnior"),
        (7801, "Cavaleiro"),
        (9001, "Profissional"),
        (10501, "Vanguarda"),
        (12001, "Veterano"),
        (14501, "Elite"),
        (17001, "Mestre de Campo"),
        (20001, "Estrategista"),
        (23501, "Guardião Mestre"),
        (27001, "Comandante"),
        (31001, "Chefe de Patrulha"),
        (35501, "Protetor Supremo"),
        (40001, "General da Guarda"),
        (45501, "Guardião de Ferro"),
        (51001, "Guardião de Aço"),
        (57501, "Guardião Lendário"),
        (64001, "Guardião Épico"),
        (71001, "Guardião Real"),
        (78501, "Guardião Ancião"),
        (86001, "Guardião Supremo"),
        (94001, "Guardião Sagrado"),
        (102001, "Guardião Imortal"),
        (110001, "Guardião Celestial"),
        (118001, "Guardião das Sombras"),
        (126001, "Guardião da Luz"),
        (134501, "Guardião Cósmico"),
        (143001, "Guardião Estelar"),
        (152001, "Guardião Dimensional"),
        (161501, "Guardião Supremo de Elite"),
        (171001, "Guardião da Eternidade"),
        (181001, "Guardião Infinito"),
        (191001, "Guardião Divino"),
        (200001, "Guardião Absoluto"),
        (225001, "Guardião Eterno")
    ]
    
    # Encontra o rank atual e o próximo
    current_min_xp = 0
    next_min_xp = 101
    
    for i, (min_xp, rank) in enumerate(experience_ranks):
        if xp >= min_xp:
            current_min_xp = min_xp
            # Próximo rank ou máximo se for o último
            if i + 1 < len(experience_ranks):
                next_min_xp = experience_ranks[i + 1][0]
            else:
                next_min_xp = experience_ranks[-1][0]  # Último rank
        else:
            break
    
    # Calcula o progresso
    xp_in_current_rank = xp - current_min_xp
    xp_needed_for_next = next_min_xp - current_min_xp
    progress_percentage = (xp_in_current_rank / xp_needed_for_next) * 100 if xp_needed_for_next > 0 else 100
    
    return xp_in_current_rank, xp_needed_for_next, progress_percentage


def get_rank_emoji(rank: str) -> str:
    """
    Retorna o emoji correspondente ao rank
    
    Args:
        rank: Nome do rank
        
    Returns:
        Emoji correspondente ao rank
    """
    rank_emojis = {
        # Ranks Iniciais (0-1000)
        "Novato": "🆕",
        "Aprendiz": "📚",
        "Iniciante": "🌱",
        "Recruta": "🎖️",
        "Principiante": "⭐",
        "Observador": "👁️",
        "Vigia": "👀",
        "Aspirante": "🎯",
        
        # Ranks Intermediários (1001-5000)
        "Cadete": "🎓",
        "Sentinela": "🛡️",
        "Patrulheiro": "🚶",
        "Agente": "🕵️",
        "Defensor": "⚔️",
        "Escudeiro": "🛡️",
        "Experiente": "🧠",
        "Protetor": "🛡️",
        "Guardião Júnior": "👶",
        "Cavaleiro": "🏇",
        "Profissional": "💼",
        "Vanguarda": "⚡",
        "Veterano": "🎖️",
        
        # Ranks Avançados (5001-15000)
        "Elite": "💎",
        "Mestre de Campo": "🏕️",
        "Estrategista": "🧩",
        "Guardião Mestre": "🎓",
        "Comandante": "👑",
        "Chefe de Patrulha": "🚔",
        "Protetor Supremo": "🛡️",
        "General da Guarda": "🎖️",
        
        # Ranks Épicos (15001-50000)
        "Guardião de Ferro": "⚒️",
        "Guardião de Aço": "🔨",
        "Guardião Lendário": "🌟",
        "Guardião Épico": "⚡",
        "Guardião Real": "👑",
        "Guardião Ancião": "🧙",
        "Guardião Supremo": "👑",
        "Guardião Sagrado": "✨",
        "Guardião Imortal": "💀",
        "Guardião Celestial": "☁️",
        "Guardião das Sombras": "🌑",
        "Guardião da Luz": "☀️",
        "Guardião Cósmico": "🌌",
        "Guardião Estelar": "⭐",
        "Guardião Dimensional": "🌀",
        "Guardião Supremo de Elite": "💫",
        "Guardião da Eternidade": "♾️",
        "Guardião Infinito": "∞",
        "Guardião Divino": "🙏",
        "Guardião Absoluto": "⚡",
        "Guardião Eterno": "♾️"
    }
    
    return rank_emojis.get(rank, "🆕")


def calculate_experience_reward(vote_type: str, is_correct: bool = True) -> int:
    """
    Calcula a recompensa de experiência baseada no tipo de voto
    
    Args:
        vote_type: Tipo do voto ("OK!", "Intimidou", "Grave")
        is_correct: Se o voto foi correto (para sistema de feedback)
        
    Returns:
        Quantidade de experiência a ser concedida
    """
    base_rewards = {
        "OK!": 10,
        "Intimidou": 15,
        "Grave": 20
    }
    
    base_xp = base_rewards.get(vote_type, 10)
    
    # Bônus por acerto (se implementado sistema de feedback)
    if is_correct:
        return base_xp
    else:
        return max(1, base_xp // 2)  # Penalidade por erro


def convert_points_to_xp(points: int) -> int:
    """
    Converte pontos para experiência
    
    Args:
        points: Quantidade de pontos
        
    Returns:
        Quantidade de XP equivalente (1 ponto = 2 XP)
    """
    return points * 2


def calculate_xp_from_points_change(points_change: int) -> int:
    """
    Calcula XP a ser adicionado/removido baseado na mudança de pontos
    
    Args:
        points_change: Mudança nos pontos (positivo ou negativo)
        
    Returns:
        XP a ser adicionado/removido
    """
    return points_change * 2


def get_rank_requirements() -> Dict[str, Dict[str, int]]:
    """
    Retorna os requisitos de cada rank
    
    Returns:
        Dicionário com informações dos ranks
    """
    return {
        # Ranks Iniciais
        "Novato": {"min_xp": 0, "description": "Iniciando a jornada como Guardião"},
        "Aprendiz": {"min_xp": 101, "description": "Aprendendo os fundamentos da moderação"},
        "Iniciante": {"min_xp": 201, "description": "Primeiros passos na moderação"},
        "Recruta": {"min_xp": 301, "description": "Demonstrando conhecimento básico"},
        "Principiante": {"min_xp": 401, "description": "Desenvolvendo habilidades moderativas"},
        "Observador": {"min_xp": 601, "description": "Observando e aprendendo"},
        "Vigia": {"min_xp": 801, "description": "Vigilante ativo da comunidade"},
        "Aspirante": {"min_xp": 1001, "description": "Aspirando a se tornar Guardião"},
        
        # Ranks Intermediários
        "Cadete": {"min_xp": 1301, "description": "Cadete em treinamento avançado"},
        "Sentinela": {"min_xp": 1601, "description": "Sentinela da ordem"},
        "Patrulheiro": {"min_xp": 2001, "description": "Patrulheiro experiente"},
        "Agente": {"min_xp": 2601, "description": "Agente especializado"},
        "Defensor": {"min_xp": 3201, "description": "Defensor da comunidade"},
        "Escudeiro": {"min_xp": 3801, "description": "Escudeiro dedicado"},
        "Experiente": {"min_xp": 4601, "description": "Guardião experiente"},
        "Protetor": {"min_xp": 5501, "description": "Protetor da paz"},
        "Guardião Júnior": {"min_xp": 6501, "description": "Guardião júnior oficial"},
        "Cavaleiro": {"min_xp": 7801, "description": "Cavaleiro da justiça"},
        "Profissional": {"min_xp": 9001, "description": "Profissional da moderação"},
        "Vanguarda": {"min_xp": 10501, "description": "Vanguarda da proteção"},
        "Veterano": {"min_xp": 12001, "description": "Veterano experiente"},
        
        # Ranks Avançados
        "Elite": {"min_xp": 14501, "description": "Elite da guarda comunitária"},
        "Mestre de Campo": {"min_xp": 17001, "description": "Mestre de campo experiente"},
        "Estrategista": {"min_xp": 20001, "description": "Estrategista da moderação"},
        "Guardião Mestre": {"min_xp": 23501, "description": "Mestre entre os Guardiões"},
        "Comandante": {"min_xp": 27001, "description": "Comandante da guarda"},
        "Chefe de Patrulha": {"min_xp": 31001, "description": "Chefe de patrulha"},
        "Protetor Supremo": {"min_xp": 35501, "description": "Protetor supremo"},
        "General da Guarda": {"min_xp": 40001, "description": "General da guarda"},
        
        # Ranks Épicos
        "Guardião de Ferro": {"min_xp": 45501, "description": "Guardião de ferro inquebrável"},
        "Guardião de Aço": {"min_xp": 51001, "description": "Guardião de aço resistente"},
        "Guardião Lendário": {"min_xp": 57501, "description": "Guardião lendário"},
        "Guardião Épico": {"min_xp": 64001, "description": "Guardião épico"},
        "Guardião Real": {"min_xp": 71001, "description": "Guardião real"},
        "Guardião Ancião": {"min_xp": 78501, "description": "Guardião ancião"},
        "Guardião Supremo": {"min_xp": 86001, "description": "Guardião supremo"},
        "Guardião Sagrado": {"min_xp": 94001, "description": "Guardião sagrado"},
        "Guardião Imortal": {"min_xp": 102001, "description": "Guardião imortal"},
        "Guardião Celestial": {"min_xp": 110001, "description": "Guardião celestial"},
        "Guardião das Sombras": {"min_xp": 118001, "description": "Guardião das sombras"},
        "Guardião da Luz": {"min_xp": 126001, "description": "Guardião da luz"},
        "Guardião Cósmico": {"min_xp": 134501, "description": "Guardião cósmico"},
        "Guardião Estelar": {"min_xp": 143001, "description": "Guardião estelar"},
        "Guardião Dimensional": {"min_xp": 152001, "description": "Guardião dimensional"},
        "Guardião Supremo de Elite": {"min_xp": 161501, "description": "Guardião supremo de elite"},
        "Guardião da Eternidade": {"min_xp": 171001, "description": "Guardião da eternidade"},
        "Guardião Infinito": {"min_xp": 181001, "description": "Guardião infinito"},
        "Guardião Divino": {"min_xp": 191001, "description": "Guardião divino"},
        "Guardião Absoluto": {"min_xp": 200001, "description": "Guardião absoluto"},
        "Guardião Eterno": {"min_xp": 225001, "description": "Guardião eterno - O mais alto título alcançável"}
    }


def format_experience_display(xp: int) -> str:
    """
    Formata a exibição da experiência de forma amigável
    
    Args:
        xp: Pontos de experiência
        
    Returns:
        String formatada com rank, emoji e progresso
    """
    rank = get_experience_rank(xp)
    emoji = get_rank_emoji(rank)
    current_xp, needed_xp, progress = get_experience_progress(xp)
    
    if rank == "Guardião Supremo":
        return f"{emoji} **{rank}** (Máximo)"
    
    return f"{emoji} **{rank}** ({current_xp}/{needed_xp} XP - {progress:.1f}%)"


# Função utilitária para debug e testes
def test_experience_system():
    """Função de teste para verificar o sistema de experiência"""
    test_xp_values = [0, 50, 150, 300, 600, 1200, 2500, 6000, 8000, 15000, 25000, 50000, 100000, 200000, 250000]
    
    print("=== Teste do Sistema de Experiência ===")
    for xp in test_xp_values:
        rank = get_experience_rank(xp)
        emoji = get_rank_emoji(rank)
        current, needed, progress = get_experience_progress(xp)
        formatted = format_experience_display(xp)
        
        print(f"XP: {xp} | {emoji} {rank} | Progresso: {current}/{needed} ({progress:.1f}%)")
        print(f"Formatado: {formatted}")
        print("-" * 80)


if __name__ == "__main__":
    test_experience_system()
