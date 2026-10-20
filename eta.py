# ============================================================
# ETA.PY
#
# Motor de cálculo de previsão de chegada.
#
# Responsabilidades:
#
# - calcular ETA base do destino;
# - calcular ETA do próximo ponto;
# - recalcular ETA do destino a partir do último ponto real;
# - escolher a média vigente de cada trecho;
# - utilizar média-base enquanto não houver histórico suficiente;
# - utilizar as últimas 3 ocorrências válidas quando disponíveis.
#
# IMPORTANTE:
#
# A classificação de um trecho como válido ou atípico
# será realizada no processamento do histórico.
#
# Este arquivo apenas consulta os registros válidos
# e decide qual média utilizar.
# ============================================================


from datetime import (
    datetime,
    timedelta
)


# ============================================================
# ROTAS
# ============================================================

from rotas import (
    obter_rota,
    calcular_total_rota,
    tempo_para_minutos
)


# ============================================================
# BANCO
# ============================================================

from banco import (
    buscar_ultimos_trechos_validos
)


# ============================================================
# CONFIGURAÇÕES
# ============================================================

# Quantidade de ocorrências válidas utilizadas
# para substituir a média-base.
QUANTIDADE_MEDIA_DINAMICA = 3


# ============================================================
# CONVERTER DATA
# ============================================================

def converter_data(data):

    # Caso já seja datetime.
    if isinstance(
        data,
        datetime
    ):
        return data


    # Caso venha como texto do SQLite.
    return datetime.strptime(
        data,
        "%Y-%m-%d %H:%M:%S"
    )


# ============================================================
# CONVERTER MINUTOS PARA HORAS
# ============================================================

def minutos_para_horas(minutos):

    if minutos is None:
        return None

    return minutos / 60


# ============================================================
# LOCALIZAR PONTO NA ROTA
# ============================================================

def localizar_ponto(
    rota,
    ponto
):

    for indice, trecho in enumerate(
        rota
    ):

        if trecho["ponto"] == ponto:

            return indice


    return None


# ============================================================
# OBTER MÉDIA-BASE DE UM TRECHO
# ============================================================

def obter_media_base_trecho(
    rota,
    ponto_origem,
    ponto_destino
):

    # Localiza o ponto de destino.
    indice_destino = localizar_ponto(
        rota,
        ponto_destino
    )


    # Se o destino não existir na rota,
    # não conseguimos identificar o trecho.
    if indice_destino is None:
        return None


    # O primeiro item da rota representa o porto de origem.
    # Portanto, um trecho real precisa ter um ponto anterior.
    if indice_destino == 0:
        return None


    # Confere se o ponto imediatamente anterior
    # realmente corresponde à origem informada.
    ponto_anterior = (
        rota[
            indice_destino - 1
        ]["ponto"]
    )


    if ponto_anterior != ponto_origem:
        return None


    # Em rotas.py, o tempo_trecho armazenado no ponto
    # de destino representa o tempo gasto para chegar
    # até ele a partir do ponto anterior.
    tempo_base = (
        rota[
            indice_destino
        ]["tempo_trecho"]
    )


    return tempo_para_minutos(
        tempo_base
    )


# ============================================================
# CALCULAR MÉDIA DAS ÚLTIMAS VIAGENS VÁLIDAS
# ============================================================

def calcular_media_historica(
    registros
):

    if not registros:
        return None


    duracoes = [
        registro["duracao_minutos"]
        for registro in registros
    ]


    return (
        sum(duracoes)
        / len(duracoes)
    )


# ============================================================
# OBTER MÉDIA ATUAL DO TRECHO
# ============================================================

def obter_media_atual_trecho(
    origem_viagem,
    destino_viagem,
    ponto_origem,
    ponto_destino,
    rota=None
):

    # ========================================================
    # DESCOBRIR ROTA
    # ========================================================

    if rota is None:

        rota = obter_rota(
            origem_viagem,
            destino_viagem
        )


    if rota is None:

        return None


    # ========================================================
    # MÉDIA-BASE
    # ========================================================

    media_base = (
        obter_media_base_trecho(
            rota,
            ponto_origem,
            ponto_destino
        )
    )


    if media_base is None:

        return None


    # ========================================================
    # BUSCAR ÚLTIMAS OCORRÊNCIAS VÁLIDAS
    # ========================================================

    registros_validos = (
        buscar_ultimos_trechos_validos(
            origem_viagem=
                origem_viagem,

            destino_viagem=
                destino_viagem,

            ponto_origem=
                ponto_origem,

            ponto_destino=
                ponto_destino,

            limite=
                QUANTIDADE_MEDIA_DINAMICA
        )
    )


    quantidade_validas = len(
        registros_validos
    )


    # ========================================================
    # AINDA NÃO EXISTEM 3 REGISTROS VÁLIDOS
    # ========================================================

    if (
        quantidade_validas
        < QUANTIDADE_MEDIA_DINAMICA
    ):

        return {

            "media_minutos":
                media_base,

            "media_horas":
                minutos_para_horas(
                    media_base
                ),

            "fonte":
                "Média base",

            "quantidade_validas":
                quantidade_validas,

            "media_base_minutos":
                media_base
        }


    # ========================================================
    # EXISTEM PELO MENOS 3 REGISTROS VÁLIDOS
    # ========================================================

    media_historica = (
        calcular_media_historica(
            registros_validos
        )
    )


    return {

        "media_minutos":
            media_historica,

        "media_horas":
            minutos_para_horas(
                media_historica
            ),

        "fonte":
            "Últimas 3 válidas",

        "quantidade_validas":
            quantidade_validas,

        "media_base_minutos":
            media_base
    }


# ============================================================
# OBTER TODAS AS MÉDIAS VIGENTES DA ROTA
# ============================================================

def obter_medias_rota(
    origem,
    destino
):

    rota = obter_rota(
        origem,
        destino
    )


    if rota is None:

        return []


    medias = []


    # Começamos no índice 1,
    # pois índice 0 é o porto de origem.
    for indice in range(
        1,
        len(rota)
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


        media = obter_media_atual_trecho(
            origem_viagem=
                origem,

            destino_viagem=
                destino,

            ponto_origem=
                ponto_origem,

            ponto_destino=
                ponto_destino,

            rota=
                rota
        )


        if media is None:
            continue


        medias.append({

            "ponto_origem":
                ponto_origem,

            "ponto_destino":
                ponto_destino,

            "media_minutos":
                media["media_minutos"],

            "media_horas":
                media["media_horas"],

            "fonte":
                media["fonte"],

            "quantidade_validas":
                media[
                    "quantidade_validas"
                ],

            "media_base_minutos":
                media[
                    "media_base_minutos"
                ]
        })


    return medias


# ============================================================
# CALCULAR TEMPO TOTAL ATUAL DA ROTA
# ============================================================

def calcular_total_rota_dinamico(
    origem,
    destino
):

    medias = obter_medias_rota(
        origem,
        destino
    )


    if not medias:
        return None


    total_minutos = sum(

        trecho["media_minutos"]

        for trecho in medias
    )


    return total_minutos


# ============================================================
# CALCULAR ETA BASE DO DESTINO
# ============================================================

def calcular_eta_base(
    data_inicio,
    origem,
    destino
):

    rota = obter_rota(
        origem,
        destino
    )


    if rota is None:
        return None


    inicio = converter_data(
        data_inicio
    )


    # ========================================================
    # TENTA UTILIZAR AS MÉDIAS VIGENTES
    # ========================================================

    total_minutos = (
        calcular_total_rota_dinamico(
            origem,
            destino
        )
    )


    # Proteção:
    # se por algum motivo não for possível montar
    # as médias dinâmicas, utiliza a soma-base.
    if total_minutos is None:

        total_minutos = (
            calcular_total_rota(
                rota
            )
        )


    return (
        inicio
        + timedelta(
            minutes=
                total_minutos
        )
    )


# ============================================================
# CALCULAR TEMPO RESTANTE A PARTIR DE UM PONTO
# ============================================================

def calcular_minutos_restantes(
    rota,
    indice_atual,
    origem,
    destino
):

    total = 0


    # Percorre todos os trechos posteriores
    # ao ponto atual.
    for indice in range(
        indice_atual + 1,
        len(rota)
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


        media = obter_media_atual_trecho(
            origem_viagem=
                origem,

            destino_viagem=
                destino,

            ponto_origem=
                ponto_origem,

            ponto_destino=
                ponto_destino,

            rota=
                rota
        )


        if media is None:

            # Fallback para a média-base.
            minutos_trecho = (
                tempo_para_minutos(
                    rota[
                        indice
                    ]["tempo_trecho"]
                )
            )

        else:

            minutos_trecho = (
                media[
                    "media_minutos"
                ]
            )


        total += minutos_trecho


    return total


# ============================================================
# CALCULAR ETA A PARTIR DO ÚLTIMO PONTO
# ============================================================

def calcular_eta_por_ponto(
    data_ponto,
    ponto_atual,
    origem,
    destino
):

    rota = obter_rota(
        origem,
        destino
    )


    if rota is None:
        return None


    indice_atual = localizar_ponto(
        rota,
        ponto_atual
    )


    if indice_atual is None:
        return None


    data_atual = converter_data(
        data_ponto
    )


    # ========================================================
    # DESTINO JÁ ALCANÇADO
    # ========================================================

    if indice_atual == len(rota) - 1:

        return {

            "ponto_atual":
                ponto_atual,

            "proximo_ponto":
                None,

            "eta_proximo_ponto":
                None,

            "eta_destino":
                data_atual,

            "minutos_restantes":
                0,

            "fonte_proximo_trecho":
                None
        }


    # ========================================================
    # PRÓXIMO PONTO
    # ========================================================

    proximo_ponto = (
        rota[
            indice_atual + 1
        ]["ponto"]
    )


    # ========================================================
    # MÉDIA VIGENTE DO PRÓXIMO TRECHO
    # ========================================================

    media_proximo = (
        obter_media_atual_trecho(
            origem_viagem=
                origem,

            destino_viagem=
                destino,

            ponto_origem=
                ponto_atual,

            ponto_destino=
                proximo_ponto,

            rota=
                rota
        )
    )


    if media_proximo is None:

        minutos_proximo = (
            tempo_para_minutos(
                rota[
                    indice_atual + 1
                ]["tempo_trecho"]
            )
        )

        fonte_proximo = (
            "Média base"
        )


    else:

        minutos_proximo = (
            media_proximo[
                "media_minutos"
            ]
        )

        fonte_proximo = (
            media_proximo[
                "fonte"
            ]
        )


    # ========================================================
    # ETA DO PRÓXIMO PONTO
    # ========================================================

    eta_proximo = (
        data_atual
        + timedelta(
            minutes=
                minutos_proximo
        )
    )


    # ========================================================
    # ETA DO DESTINO FINAL
    # ========================================================

    minutos_restantes = (
        calcular_minutos_restantes(
            rota=
                rota,

            indice_atual=
                indice_atual,

            origem=
                origem,

            destino=
                destino
        )
    )


    eta_destino = (
        data_atual
        + timedelta(
            minutes=
                minutos_restantes
        )
    )


    return {

        "ponto_atual":
            ponto_atual,

        "proximo_ponto":
            proximo_ponto,

        "eta_proximo_ponto":
            eta_proximo,

        "eta_destino":
            eta_destino,

        "minutos_restantes":
            minutos_restantes,

        "fonte_proximo_trecho":
            fonte_proximo
    }


# ============================================================
# CALCULAR PROGRAMAÇÃO COMPLETA DA VIAGEM
# ============================================================

def calcular_programacao_viagem(
    data_inicio,
    origem,
    destino
):

    rota = obter_rota(
        origem,
        destino
    )


    if rota is None:
        return []


    inicio = converter_data(
        data_inicio
    )


    acumulado_minutos = 0

    programacao = []


    # ========================================================
    # PRIMEIRO PONTO = PORTO DE ORIGEM
    # ========================================================

    programacao.append({

        "ponto":
            rota[0]["ponto"],

        "ponto_anterior":
            None,

        "media_minutos":
            0,

        "fonte_media":
            None,

        "quantidade_validas":
            0,

        "acumulado_minutos":
            0,

        "horario_previsto":
            inicio
    })


    # ========================================================
    # DEMAIS PONTOS
    # ========================================================

    for indice in range(
        1,
        len(rota)
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


        media = (
            obter_media_atual_trecho(
                origem_viagem=
                    origem,

                destino_viagem=
                    destino,

                ponto_origem=
                    ponto_origem,

                ponto_destino=
                    ponto_destino,

                rota=
                    rota
            )
        )


        # ====================================================
        # FALLBACK
        # ====================================================

        if media is None:

            media_minutos = (
                tempo_para_minutos(
                    rota[
                        indice
                    ]["tempo_trecho"]
                )
            )

            fonte_media = (
                "Média base"
            )

            quantidade_validas = 0


        else:

            media_minutos = (
                media[
                    "media_minutos"
                ]
            )

            fonte_media = (
                media[
                    "fonte"
                ]
            )

            quantidade_validas = (
                media[
                    "quantidade_validas"
                ]
            )


        acumulado_minutos += (
            media_minutos
        )


        horario_previsto = (
            inicio
            + timedelta(
                minutes=
                    acumulado_minutos
            )
        )


        programacao.append({

            "ponto":
                ponto_destino,

            "ponto_anterior":
                ponto_origem,

            "media_minutos":
                media_minutos,

            "fonte_media":
                fonte_media,

            "quantidade_validas":
                quantidade_validas,

            "acumulado_minutos":
                acumulado_minutos,

            "horario_previsto":
                horario_previsto
        })


    return programacao