# ============================================================
# TESTE_CLASSIFICACAO_VIAGEM_ETA.PY
#
# Testa a classificação de uma VIAGEM COMPLETA para o ETA.
#
# Cenários:
#
# 1. Viagem completa e sem trechos atípicos
#    → válida para aprendizado
#
# 2. Viagem completa com um trecho atípico
#    → viagem atípica
#
# 3. Viagem incompleta
#    → não pode alimentar o ETA
#
# IMPORTANTE:
#
# Os registros deste teste utilizam códigos começando
# com TESTE-ETA- e são removidos automaticamente.
# ============================================================


import sqlite3

from datetime import (
    datetime,
    timedelta
)


from banco import (
    criar_tabela_historico_trechos,
    garantir_campos_eta_viagens,
    salvar_historico_trecho,
    buscar_trechos_viagem
)


from processamento_trechos import (
    classificar_viagem_para_eta
)


from rotas import (
    obter_rota,
    tempo_para_minutos
)


# ============================================================
# CONFIGURAÇÕES
# ============================================================

BANCO = "dados_totaltrack.db"

PREFIXO_TESTE = "TESTE-ETA-"

ORIGEM = "BEL"
DESTINO = "MAO"

DATA_INICIO_BASE = datetime(
    2026,
    8,
    18,
    8,
    0,
    0
)


# ============================================================
# LIMPAR DADOS DE TESTE
# ============================================================

def limpar_dados_teste():

    conexao = sqlite3.connect(
        BANCO
    )

    cursor = conexao.cursor()


    # ========================================================
    # HISTÓRICO DOS TRECHOS
    # ========================================================

    cursor.execute("""
        DELETE FROM historico_trechos
        WHERE codigo_viagem LIKE ?
    """, (
        f"{PREFIXO_TESTE}%",
    ))


    # ========================================================
    # VIAGENS
    # ========================================================

    cursor.execute("""
        DELETE FROM viagens
        WHERE codigo_viagem LIKE ?
    """, (
        f"{PREFIXO_TESTE}%",
    ))


    conexao.commit()
    conexao.close()


# ============================================================
# CRIAR VIAGEM DE TESTE
# ============================================================

def criar_viagem_teste(
    codigo_viagem,
    data_inicio
):

    garantir_campos_eta_viagens()

    conexao = sqlite3.connect(
        BANCO
    )

    cursor = conexao.cursor()


    cursor.execute("""
        INSERT INTO viagens (
            codigo_viagem,
            placa,
            balsa,
            origem,
            destino,
            trajeto,
            carga,
            prazo_horas,
            data_inicio,
            data_fim,
            status,
            viagem_atipica,
            usar_no_eta,
            motivo_eta,
            eta_classificado
        )

        VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?
        )
    """, (

        codigo_viagem,

        codigo_viagem,

        "BALSA DE TESTE",

        ORIGEM,
        DESTINO,

        "↑ BEL x MAO",

        "Cargas Diversas",

        168,

        data_inicio.strftime(
            "%Y-%m-%d %H:%M:%S"
        ),

        (
            data_inicio
            + timedelta(hours=168)
        ).strftime(
            "%Y-%m-%d %H:%M:%S"
        ),

        "Finalizada",

        None,

        0,

        None,

        0
    ))


    conexao.commit()
    conexao.close()


# ============================================================
# CRIAR HISTÓRICO COMPLETO DA ROTA
# ============================================================

def criar_trechos_viagem(
    codigo_viagem,
    indice_atipico=None,
    remover_ultimo=False
):

    rota = obter_rota(
        ORIGEM,
        DESTINO
    )


    data_atual = (
        DATA_INICIO_BASE
    )


    # ========================================================
    # QUANTIDADE DE TRECHOS
    # ========================================================

    total_trechos = (
        len(rota) - 1
    )


    # Caso o teste seja de viagem incompleta,
    # deixamos o último trecho sem registro.
    if remover_ultimo:

        total_trechos -= 1


    # ========================================================
    # PERCORRER ROTA
    # ========================================================

    for indice in range(
        1,
        total_trechos + 1
    ):

        ponto_origem = (
            rota[
                indice - 1
            ]["ponto"]
        )

        ponto_destino = (
            rota[
                indice
            ]["ponto"]
        )


        # Média-base daquele trecho.
        media_minutos = (
            tempo_para_minutos(
                rota[
                    indice
                ]["tempo_trecho"]
            )
        )


        # ====================================================
        # TRECHO NORMAL
        # ====================================================

        duracao_minutos = (
            media_minutos
        )

        atipico = False


        # ====================================================
        # TRECHO ATÍPICO
        # ====================================================

        if (
            indice_atipico is not None
            and indice == indice_atipico
        ):

            # Colocamos 3h30 acima da média.
            #
            # Nossa tolerância é ±3h,
            # portanto deve ser atípico.
            duracao_minutos = (
                media_minutos
                + 210
            )

            atipico = True


        data_origem = (
            data_atual
        )


        data_destino = (
            data_origem
            + timedelta(
                minutes=
                    duracao_minutos
            )
        )


        desvio_minutos = (
            duracao_minutos
            - media_minutos
        )


        # ====================================================
        # SALVAR
        # ====================================================

        salvar_historico_trecho(

            placa=
                codigo_viagem,

            balsa=
                "BALSA DE TESTE",

            codigo_viagem=
                codigo_viagem,

            origem_viagem=
                ORIGEM,

            destino_viagem=
                DESTINO,

            ponto_origem=
                ponto_origem,

            ponto_destino=
                ponto_destino,

            data_origem=
                data_origem.strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),

            data_destino=
                data_destino.strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),

            duracao_minutos=
                duracao_minutos,

            media_referencia_minutos=
                media_minutos,

            desvio_minutos=
                desvio_minutos,

            atipico=
                atipico,

            # Durante a viagem, nenhum trecho
            # está liberado para aprendizado.
            fonte_media=
                "Média base",

            usar_no_eta=
                False,

            data_registro=
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
        )


        # Próximo trecho começa onde este terminou.
        data_atual = (
            data_destino
        )


# ============================================================
# CONSULTAR RESULTADO NO BANCO
# ============================================================

def consultar_viagem_teste(
    codigo_viagem
):

    conexao = sqlite3.connect(
        BANCO
    )

    conexao.row_factory = (
        sqlite3.Row
    )

    cursor = conexao.cursor()


    cursor.execute("""
        SELECT *
        FROM viagens
        WHERE codigo_viagem = ?
    """, (
        codigo_viagem,
    ))


    viagem = cursor.fetchone()

    conexao.close()


    if viagem is None:
        return None


    return dict(
        viagem
    )


# ============================================================
# PREPARAÇÃO
# ============================================================

criar_tabela_historico_trechos()

garantir_campos_eta_viagens()

limpar_dados_teste()


# ============================================================
# TESTE 1
# VIAGEM COMPLETA E VÁLIDA
# ============================================================

print(
    "\n========================================"
)

print(
    " TESTE 1 - VIAGEM COMPLETA VÁLIDA"
)

print(
    "========================================"
)


codigo_1 = (
    "TESTE-ETA-001"
)


criar_viagem_teste(
    codigo_viagem=
        codigo_1,

    data_inicio=
        DATA_INICIO_BASE
)


criar_trechos_viagem(
    codigo_viagem=
        codigo_1
)


viagem_1 = (
    consultar_viagem_teste(
        codigo_1
    )
)


resultado_1 = (
    classificar_viagem_para_eta(
        viagem_1
    )
)


print(
    resultado_1
)


trechos_1 = (
    buscar_trechos_viagem(
        codigo_1
    )
)


print(
    "Trechos registrados:",
    len(trechos_1)
)


print(
    "Trechos liberados para ETA:",
    sum(
        1
        for trecho in trechos_1
        if trecho["usar_no_eta"] == 1
    )
)


# ============================================================
# TESTE 2
# VIAGEM COM UM TRECHO ATÍPICO
# ============================================================

print(
    "\n========================================"
)

print(
    " TESTE 2 - VIAGEM ATÍPICA"
)

print(
    "========================================"
)


codigo_2 = (
    "TESTE-ETA-002"
)


criar_viagem_teste(
    codigo_viagem=
        codigo_2,

    data_inicio=
        DATA_INICIO_BASE
)


# Trecho de índice 5 será atípico.
criar_trechos_viagem(
    codigo_viagem=
        codigo_2,

    indice_atipico=
        5
)


viagem_2 = (
    consultar_viagem_teste(
        codigo_2
    )
)


resultado_2 = (
    classificar_viagem_para_eta(
        viagem_2
    )
)


print(
    resultado_2
)


trechos_2 = (
    buscar_trechos_viagem(
        codigo_2
    )
)


print(
    "Trechos registrados:",
    len(trechos_2)
)


print(
    "Trechos atípicos:",
    sum(
        1
        for trecho in trechos_2
        if trecho["atipico"] == 1
    )
)


print(
    "Trechos liberados para ETA:",
    sum(
        1
        for trecho in trechos_2
        if trecho["usar_no_eta"] == 1
    )
)


# ============================================================
# TESTE 3
# VIAGEM INCOMPLETA
# ============================================================

print(
    "\n========================================"
)

print(
    " TESTE 3 - VIAGEM INCOMPLETA"
)

print(
    "========================================"
)


codigo_3 = (
    "TESTE-ETA-003"
)


criar_viagem_teste(
    codigo_viagem=
        codigo_3,

    data_inicio=
        DATA_INICIO_BASE
)


criar_trechos_viagem(
    codigo_viagem=
        codigo_3,

    remover_ultimo=
        True
)


viagem_3 = (
    consultar_viagem_teste(
        codigo_3
    )
)


resultado_3 = (
    classificar_viagem_para_eta(
        viagem_3
    )
)


print(
    resultado_3
)


trechos_3 = (
    buscar_trechos_viagem(
        codigo_3
    )
)


print(
    "Trechos registrados:",
    len(trechos_3)
)


print(
    "Trechos liberados para ETA:",
    sum(
        1
        for trecho in trechos_3
        if trecho["usar_no_eta"] == 1
    )
)


# ============================================================
# RESULTADO ESPERADO
# ============================================================

print(
    "\n========================================"
)

print(
    " RESULTADO ESPERADO"
)

print(
    "========================================"
)


print(
    """
TESTE 1
-------
valida_eta = True
viagem_atipica = False
todos os trechos → usar_no_eta = 1


TESTE 2
-------
valida_eta = False
viagem_atipica = True
1 trecho atípico
nenhum trecho → usar_no_eta = 1


TESTE 3
-------
valida_eta = False
viagem_atipica = False
motivo = viagem incompleta
nenhum trecho → usar_no_eta = 1
"""
)


# ============================================================
# LIMPEZA
# ============================================================

limpar_dados_teste()


print(
    "Dados fictícios removidos do banco."
)