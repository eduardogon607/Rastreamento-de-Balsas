# ============================================================
# PROCESSAMENTO_TRECHOS.PY
#
# Responsável por transformar eventos reais da TotalTrack
# em histórico de trechos para o ETA.
#
# PRINCIPAIS REGRAS:
#
# - utiliza eventos "Entrada" nos pontos da rota;
# - compara pontos consecutivos;
# - calcula a duração real de cada trecho;
# - compara com a média vigente;
# - tolerância inicial: ±3 horas;
# - trechos atípicos permanecem salvos para auditoria;
# - nenhum trecho entra imediatamente no aprendizado;
# - somente após a viagem terminar ela é classificada;
# - apenas viagens completas e não atípicas alimentam o ETA;
# - viagens anteriores ao corte das novas geofences
#   nunca alimentam a média dinâmica.
#
# IMPORTANTE:
#
# A data de corte das geofences agora é consultada
# diretamente no banco SQLite.
#
# O arquivo balsas.py não é mais necessário neste módulo.
# ============================================================


from datetime import datetime


# ============================================================
# ROTAS
# ============================================================

from rotas import obter_rota


# ============================================================
# ETA
# ============================================================

from eta import (
    obter_media_atual_trecho,
    localizar_ponto
)


# ============================================================
# BANCO
# ============================================================

from banco import (
    salvar_historico_trecho,
    buscar_trechos_viagem,
    atualizar_uso_eta_trechos_viagem,
    atualizar_classificacao_eta_viagem,
    buscar_data_corte_geofence
)


# ============================================================
# CONFIGURAÇÃO DE ATIPICIDADE
# ============================================================

# Tolerância máxima permitida em relação
# à média vigente do trecho.
TOLERANCIA_ATIPICO_HORAS = 3

TOLERANCIA_ATIPICO_MINUTOS = (
    TOLERANCIA_ATIPICO_HORAS * 60
)


# ============================================================
# CONVERTER DATA
# ============================================================

def converter_data(
    data
):

    # Caso já seja datetime.
    if isinstance(
        data,
        datetime
    ):
        return data


    # Caso venha como texto.
    return datetime.strptime(
        data,
        "%Y-%m-%d %H:%M:%S"
    )


# ============================================================
# OBTER DATA DE CORTE DAS GEOFENCES
# ============================================================

def obter_data_corte_geofence():
    """
    Consulta no banco a data oficial de corte
    das novas geofences e retorna como datetime.

    Essa função substitui o antigo uso direto de
    DATA_CORTE_GEOFENCE do arquivo balsas.py.
    """

    data_corte_banco = (
        buscar_data_corte_geofence()
    )


    if data_corte_banco is None:

        raise RuntimeError(
            "Não foi encontrada no banco a data oficial "
            "de corte das novas geofences."
        )


    try:

        return converter_data(
            data_corte_banco
        )

    except ValueError as erro:

        raise RuntimeError(
            "A data de corte das geofences registrada "
            "no banco possui formato inválido."
        ) from erro


# ============================================================
# VERIFICAR SE PONTO PERTENCE À ROTA
# ============================================================

def ponto_pertence_rota(
    rota,
    ponto
):

    indice = localizar_ponto(
        rota,
        ponto
    )


    return indice is not None


# ============================================================
# VERIFICAR SE PONTOS SÃO CONSECUTIVOS
# ============================================================

def pontos_sao_consecutivos(
    rota,
    ponto_origem,
    ponto_destino
):

    indice_origem = localizar_ponto(
        rota,
        ponto_origem
    )

    indice_destino = localizar_ponto(
        rota,
        ponto_destino
    )


    # ========================================================
    # PROTEÇÃO
    # ========================================================

    if (
        indice_origem is None
        or indice_destino is None
    ):
        return False


    # O destino precisa estar exatamente
    # uma posição depois da origem.
    return (
        indice_destino
        == indice_origem + 1
    )


# ============================================================
# PROCESSAR UM TRECHO REAL
# ============================================================

def processar_trecho(
    viagem,
    evento_origem,
    evento_destino
):

    # ========================================================
    # PROTEÇÕES BÁSICAS
    # ========================================================

    if viagem is None:
        return False

    if evento_origem is None:
        return False

    if evento_destino is None:
        return False


    # ========================================================
    # DADOS DA VIAGEM
    # ========================================================

    placa = (
        viagem["placa"]
    )

    balsa = (
        viagem["balsa"]
    )

    codigo_viagem = (
        viagem["codigo_viagem"]
    )

    origem_viagem = (
        viagem["origem"]
    )

    destino_viagem = (
        viagem["destino"]
    )


    # ========================================================
    # OBTER ROTA DA VIAGEM
    # ========================================================

    rota = obter_rota(
        origem_viagem,
        destino_viagem
    )


    if rota is None:
        return False


    # ========================================================
    # EVENTOS PRECISAM REPRESENTAR ENTRADAS
    # ========================================================

    # O evento inicial virtual criado pelo main.py
    # também utiliza "Entrada", justamente para permitir
    # que o primeiro trecho seja tratado da mesma forma.
    if (
        evento_origem["evento"]
        != "Entrada"
    ):
        return False


    if (
        evento_destino["evento"]
        != "Entrada"
    ):
        return False


    # ========================================================
    # PONTOS DO TRECHO
    # ========================================================

    ponto_origem = (
        evento_origem["area"]
    )

    ponto_destino = (
        evento_destino["area"]
    )


    # ========================================================
    # VALIDAR PONTOS
    # ========================================================

    if not ponto_pertence_rota(
        rota,
        ponto_origem
    ):
        return False


    if not ponto_pertence_rota(
        rota,
        ponto_destino
    ):
        return False


    # ========================================================
    # VALIDAR SE SÃO PONTOS CONSECUTIVOS
    # ========================================================

    if not pontos_sao_consecutivos(
        rota,
        ponto_origem,
        ponto_destino
    ):
        return False


    # ========================================================
    # CONVERTER DATAS
    # ========================================================

    data_origem = converter_data(
        evento_origem["dataGPS"]
    )

    data_destino = converter_data(
        evento_destino["dataGPS"]
    )


    # ========================================================
    # PROTEÇÃO CONTRA DATAS INVÁLIDAS
    # ========================================================

    if data_destino <= data_origem:
        return False


    # ========================================================
    # CALCULAR DURAÇÃO REAL
    # ========================================================

    duracao = (
        data_destino
        - data_origem
    )


    duracao_minutos = (
        duracao.total_seconds()
        / 60
    )


    # ========================================================
    # OBTER MÉDIA VIGENTE DO TRECHO
    # ========================================================

    media = obter_media_atual_trecho(
        origem_viagem=
            origem_viagem,

        destino_viagem=
            destino_viagem,

        ponto_origem=
            ponto_origem,

        ponto_destino=
            ponto_destino,

        rota=
            rota
    )


    if media is None:
        return False


    media_referencia = (
        media["media_minutos"]
    )


    fonte_media = (
        media["fonte"]
    )


    # ========================================================
    # CALCULAR DESVIO
    # ========================================================

    desvio_minutos = (
        duracao_minutos
        - media_referencia
    )


    # ========================================================
    # CLASSIFICAR ATIPICIDADE DO TRECHO
    # ========================================================

    atipico = (
        abs(
            desvio_minutos
        )
        > TOLERANCIA_ATIPICO_MINUTOS
    )


    # ========================================================
    # USO NO ETA
    # ========================================================

    # Nenhum trecho entra imediatamente no aprendizado.
    #
    # A viagem inteira precisa terminar antes.
    #
    # Depois da chegada:
    #
    # - se a viagem for completa;
    # - se tiver começado depois do corte;
    # - se nenhum trecho for atípico;
    #
    # então todos os trechos recebem usar_no_eta = 1.
    usar_no_eta = False


    # ========================================================
    # SALVAR HISTÓRICO
    # ========================================================

    salvar_historico_trecho(
        placa=
            placa,

        balsa=
            balsa,

        codigo_viagem=
            codigo_viagem,

        origem_viagem=
            origem_viagem,

        destino_viagem=
            destino_viagem,

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
            media_referencia,

        desvio_minutos=
            desvio_minutos,

        atipico=
            atipico,

        fonte_media=
            fonte_media,

        usar_no_eta=
            usar_no_eta,

        data_registro=
            datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
    )


    # ========================================================
    # RETORNO PARA CONFERÊNCIA
    # ========================================================

    return {

        "codigo_viagem":
            codigo_viagem,

        "ponto_origem":
            ponto_origem,

        "ponto_destino":
            ponto_destino,

        "duracao_minutos":
            duracao_minutos,

        "media_referencia_minutos":
            media_referencia,

        "desvio_minutos":
            desvio_minutos,

        "atipico":
            atipico,

        "usar_no_eta":
            usar_no_eta,

        "fonte_media":
            fonte_media
    }


# ============================================================
# CLASSIFICAR VIAGEM COMPLETA PARA O ETA
# ============================================================

def classificar_viagem_para_eta(
    viagem
):

    # ========================================================
    # PROTEÇÕES
    # ========================================================

    if viagem is None:
        return None


    if viagem["data_inicio"] is None:
        return None


    # ========================================================
    # DADOS DA VIAGEM
    # ========================================================

    codigo_viagem = (
        viagem["codigo_viagem"]
    )

    origem = (
        viagem["origem"]
    )

    destino = (
        viagem["destino"]
    )


    data_inicio = converter_data(
        viagem["data_inicio"]
    )


    # ========================================================
    # DATA DE CORTE DAS GEOFENCES
    # ========================================================

    # Agora consultamos o banco em vez de utilizar
    # DATA_CORTE_GEOFENCE do balsas.py.

    data_corte = (
        obter_data_corte_geofence()
    )


    # ========================================================
    # REGRA 1
    # VIAGEM ANTERIOR AO CORTE
    # ========================================================

    if data_inicio < data_corte:

        # Nenhum trecho pode alimentar o ETA.
        atualizar_uso_eta_trechos_viagem(
            codigo_viagem=
                codigo_viagem,

            usar_no_eta=
                False
        )


        motivo = (
            "Viagem iniciada antes do corte "
            "das novas geofences."
        )


        atualizar_classificacao_eta_viagem(
            codigo_viagem=
                codigo_viagem,

            viagem_atipica=
                False,

            usar_no_eta=
                False,

            motivo_eta=
                motivo
        )


        return {

            "codigo_viagem":
                codigo_viagem,

            "valida_eta":
                False,

            "viagem_atipica":
                False,

            "motivo":
                motivo
        }


    # ========================================================
    # IDENTIFICAR ROTA
    # ========================================================

    rota = obter_rota(
        origem,
        destino
    )


    if rota is None:

        motivo = (
            "Rota da viagem não identificada."
        )


        atualizar_uso_eta_trechos_viagem(
            codigo_viagem=
                codigo_viagem,

            usar_no_eta=
                False
        )


        atualizar_classificacao_eta_viagem(
            codigo_viagem=
                codigo_viagem,

            viagem_atipica=
                False,

            usar_no_eta=
                False,

            motivo_eta=
                motivo
        )


        return {

            "codigo_viagem":
                codigo_viagem,

            "valida_eta":
                False,

            "viagem_atipica":
                False,

            "motivo":
                motivo
        }


    # ========================================================
    # QUANTIDADE DE TRECHOS ESPERADOS
    # ========================================================

    # Se a rota possui:
    #
    # Porto
    # Ponto A
    # Ponto B
    # Destino
    #
    # então existem 3 trechos.
    total_trechos_esperados = (
        len(rota) - 1
    )


    # ========================================================
    # BUSCAR TRECHOS REGISTRADOS
    # ========================================================

    trechos = buscar_trechos_viagem(
        codigo_viagem
    )


    total_trechos_registrados = (
        len(trechos)
    )


    # ========================================================
    # REGRA 2
    # VIAGEM INCOMPLETA
    # ========================================================

    if (
        total_trechos_registrados
        != total_trechos_esperados
    ):

        atualizar_uso_eta_trechos_viagem(
            codigo_viagem=
                codigo_viagem,

            usar_no_eta=
                False
        )


        motivo = (
            f"Viagem incompleta para aprendizado. "
            f"Trechos esperados: "
            f"{total_trechos_esperados}. "
            f"Trechos registrados: "
            f"{total_trechos_registrados}."
        )


        atualizar_classificacao_eta_viagem(
            codigo_viagem=
                codigo_viagem,

            viagem_atipica=
                False,

            usar_no_eta=
                False,

            motivo_eta=
                motivo
        )


        return {

            "codigo_viagem":
                codigo_viagem,

            "valida_eta":
                False,

            "viagem_atipica":
                False,

            "motivo":
                motivo
        }


    # ========================================================
    # CONTAR TRECHOS ATÍPICOS
    # ========================================================

    trechos_atipicos = [

        trecho

        for trecho in trechos

        if trecho["atipico"] == 1
    ]


    quantidade_atipicos = len(
        trechos_atipicos
    )


    # ========================================================
    # REGRA 3
    # VIAGEM COM TRECHO ATÍPICO
    # ========================================================

    if quantidade_atipicos > 0:

        atualizar_uso_eta_trechos_viagem(
            codigo_viagem=
                codigo_viagem,

            usar_no_eta=
                False
        )


        motivo = (
            f"Viagem possui "
            f"{quantidade_atipicos} "
            f"trecho(s) atípico(s)."
        )


        atualizar_classificacao_eta_viagem(
            codigo_viagem=
                codigo_viagem,

            viagem_atipica=
                True,

            usar_no_eta=
                False,

            motivo_eta=
                motivo
        )


        return {

            "codigo_viagem":
                codigo_viagem,

            "valida_eta":
                False,

            "viagem_atipica":
                True,

            "motivo":
                motivo
        }


    # ========================================================
    # VIAGEM VÁLIDA PARA O ETA
    # ========================================================

    # Se chegou aqui:
    #
    # - começou depois do corte;
    # - rota foi identificada;
    # - todos os trechos foram registrados;
    # - nenhum trecho foi atípico.
    atualizar_uso_eta_trechos_viagem(
        codigo_viagem=
            codigo_viagem,

        usar_no_eta=
            True
    )


    motivo = (
        "Viagem completa e sem trechos atípicos."
    )


    atualizar_classificacao_eta_viagem(
        codigo_viagem=
            codigo_viagem,

        viagem_atipica=
            False,

        usar_no_eta=
            True,

        motivo_eta=
            motivo
    )


    return {

        "codigo_viagem":
            codigo_viagem,

        "valida_eta":
            True,

        "viagem_atipica":
            False,

        "motivo":
            motivo
    }