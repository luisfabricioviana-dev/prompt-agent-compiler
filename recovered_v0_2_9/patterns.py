
PATTERNS = {
    "P01": {"name": "BUILD", "complexity_cost": 2},
    "P02": {"name": "REFACTOR", "complexity_cost": 2},
    "P03": {"name": "DEBUG", "complexity_cost": 2},
    "P04": {"name": "SYSTEM_DESIGN", "complexity_cost": 3},
    "P05": {"name": "OPTIMIZE", "complexity_cost": 2},
    "P06": {"name": "CLEAN_ARCHITECTURE", "complexity_cost": 3},
    "P07": {"name": "MULTI_AGENT", "complexity_cost": 4},
    "P08": {"name": "PRODUCTION_UI", "complexity_cost": 2},
}

STRONG_SIGNALS = {
    "P01": ("crie", "implemente", "construa", "desenvolva", "adicione"),
    "P02": ("refatore", "reorganize", "sem alterar", "preservando comportamento"),
    "P03": ("erro", "falhou", "não funciona", "bug", "conserte", "corrija", "retornando"),
    "P04": ("arquitetura", "projete", "sistema", "plataforma", "componentes", "fluxo de dados"),
    "P05": ("otimize", "otimização", "lenta", "latência", "performance", "desempenho"),
    "P06": ("acoplamento", "responsabilidades", "módulos", "boundaries", "persistência", "regras de negócio"),
    "P07": ("vários agentes", "multiagente", "revisão independente", "especialistas independentes"),
    "P08": ("formulário", "frontend", "interface", "ui", "responsivo", "acessível", "dashboard"),
}
