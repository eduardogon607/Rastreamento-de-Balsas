# ============================================================
# TESTE_MEDIA_DINAMICA.PY
#
# Valida a troca automática:
#
# Média base
#      ↓
# 3 registros válidos
#      ↓
# Média das últimas 3 válidas
#
# Também valida que um registro atípico não entra no cálculo.
# ============================================================


from datetime import datetime

from banco import (
    criar_tabela_historico_trechos,
    salvar_historico_trecho
)

from eta import (
    obter_media_atual_trecho
)


# ============================================================
# CONFIGURAÇÃO DO TRECHO DE TESTE
# ============================================================

ORIGEM_VIAGEM = "BEL"
DESTINO_VIAGEM = "MAO"

PONTO_ORIGEM = "Farol do Capim/PA"
PONTO_DESTINO = "Ponta Negra/PA"


# Média-base desse trecho:
#
# 02:30
# =
# 150 minutos


# ============================================================
# FUNÇÃO AUXILIAR
# ============================================================

def mostrar_media(titulo):

    print("\n========================================")
    print(titulo)
    print("========================================")

    media = obter_media_atual_trecho(
        origem_viagem=ORIGEM_VIAGEM,
        destino_viagem=DESTINO_VIAGEM,
        ponto_origem=PONTO_ORIGEM,
        ponto_destino=PONTO_DESTINO
    )

    print(
        "Média minutos:",
        media["media_minutos"]
    )

    print(
        "Média horas:",
        round(
            media["media_horas"],
            2
        )
    )

    print(
        "Fonte:",
        media["fonte"]
    )

    print(
        "Quantidade válidas:",
        media["quantidade_validas"]
    )


# ============================================================
# GARANTIR TABELA
# ============================================================

criar_tabela_historico_trechos()


# ============================================================
# SITUAÇÃO INICIAL
# ============================================================

mostrar_media(
    "ANTES DOS TESTES"
)


# ============================================================
# REGISTRO 1
#
# 02:20
# 140 minutos
# ============================================================

salvar_historico_trecho(
    placa="TESTE101",
    balsa="BALSA TESTE 101",
    codigo_viagem="TESTE-101",

    origem_viagem=ORIGEM_VIAGEM,
    destino_viagem=DESTINO_VIAGEM,

    ponto_origem=PONTO_ORIGEM,
    ponto_destino=PONTO_DESTINO,

    data_origem="2026-08-18 10:00:00",
    data_destino="2026-08-18 12:20:00",

    duracao_minutos=140,

    media_referencia_minutos=150,
    desvio_minutos=-10,

    atipico=False,
    fonte_media="Média base",

    usar_no_eta=True,

    data_registro=datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )
)


mostrar_media(
    "APÓS 1 REGISTRO VÁLIDO"
)


# ============================================================
# REGISTRO 2
#
# 02:30
# 150 minutos
# ============================================================

salvar_historico_trecho(
    placa="TESTE102",
    balsa="BALSA TESTE 102",
    codigo_viagem="TESTE-102",

    origem_viagem=ORIGEM_VIAGEM,
    destino_viagem=DESTINO_VIAGEM,

    ponto_origem=PONTO_ORIGEM,
    ponto_destino=PONTO_DESTINO,

    data_origem="2026-08-19 10:00:00",
    data_destino="2026-08-19 12:30:00",

    duracao_minutos=150,

    media_referencia_minutos=150,
    desvio_minutos=0,

    atipico=False,
    fonte_media="Média base",

    usar_no_eta=True,

    data_registro=datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )
)


mostrar_media(
    "APÓS 2 REGISTROS VÁLIDOS"
)


# ============================================================
# REGISTRO ATÍPICO
#
# 06:00
# 360 minutos
#
# Deve ficar salvo,
# mas não entrar na média.
# ============================================================

salvar_historico_trecho(
    placa="TESTE999",
    balsa="BALSA TESTE ATÍPICA",
    codigo_viagem="TESTE-999",

    origem_viagem=ORIGEM_VIAGEM,
    destino_viagem=DESTINO_VIAGEM,

    ponto_origem=PONTO_ORIGEM,
    ponto_destino=PONTO_DESTINO,

    data_origem="2026-08-20 10:00:00",
    data_destino="2026-08-20 16:00:00",

    duracao_minutos=360,

    media_referencia_minutos=150,
    desvio_minutos=210,

    atipico=True,
    fonte_media="Média base",

    usar_no_eta=False,

    data_registro=datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )
)


mostrar_media(
    "APÓS REGISTRO ATÍPICO"
)


# ============================================================
# REGISTRO 3
#
# 02:40
# 160 minutos
#
# Agora teremos:
#
# 140
# 150
# 160
#
# Média:
# 150 minutos
# =
# 02:30
#
# A fonte deve mudar para:
#
# Últimas 3 válidas
# ============================================================

salvar_historico_trecho(
    placa="TESTE103",
    balsa="BALSA TESTE 103",
    codigo_viagem="TESTE-103",

    origem_viagem=ORIGEM_VIAGEM,
    destino_viagem=DESTINO_VIAGEM,

    ponto_origem=PONTO_ORIGEM,
    ponto_destino=PONTO_DESTINO,

    data_origem="2026-08-21 10:00:00",
    data_destino="2026-08-21 12:40:00",

    duracao_minutos=160,

    media_referencia_minutos=150,
    desvio_minutos=10,

    atipico=False,
    fonte_media="Média base",

    usar_no_eta=True,

    data_registro=datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )
)


mostrar_media(
    "APÓS 3 REGISTROS VÁLIDOS"
)


# ============================================================
# RESULTADO ESPERADO
# ============================================================

print("\n========================================")
print(" RESULTADO ESPERADO")
print("========================================")

print(
    """
Antes:
Fonte = Média base

1 válida:
Fonte = Média base

2 válidas:
Fonte = Média base

Atípico:
Continua Média base

3 válidas:
Fonte = Últimas 3 válidas

Média esperada:
(140 + 150 + 160) / 3
= 150 minutos
= 2h30
"""
)