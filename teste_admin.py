# ============================================================
# TESTE_ADMIN.PY
#
# Testa a camada administrativa do sistema.
#
# Este arquivo NÃO altera viagens.
#
# Exibe:
#
# - histórico de ajustes manuais;
# - situação atual da Valencia;
# - situação atual de todas as balsas;
# - tempo em viagem;
# - tempo aguardando carregamento;
# - prazo;
# - tempo restante;
# - tempo excedido;
# - situação do prazo;
# - último ponto confirmado;
# - próximo ponto previsto;
# - ETA base do destino;
# - ETA do próximo ponto;
# - ETA atualizada do destino;
# - fonte utilizada no cálculo do ETA.
# ============================================================


from admin import (
    listar_ajustes,
    consultar_situacao_balsa,
    consultar_situacao_todas_balsas
)


# ============================================================
# FUNÇÃO AUXILIAR PARA FORMATAR DATAS
# ============================================================

def formatar_data(data):

    # Caso não exista uma data.
    if data is None:
        return None

    # Caso já seja datetime.
    if hasattr(data, "strftime"):

        return data.strftime(
            "%d/%m/%Y %H:%M"
        )

    # Caso esteja armazenada como texto.
    return data


# ============================================================
# 1. AJUSTES MANUAIS
# ============================================================

ajustes = listar_ajustes()


print(
    "\n========================================"
)

print(
    " AJUSTES REGISTRADOS"
)

print(
    "========================================"
)


print(
    "Total de ajustes:",
    len(ajustes)
)


# Caso ainda não existam ajustes no banco novo.
if not ajustes:

    print(
        "Nenhum ajuste manual registrado."
    )


else:

    for ajuste in ajustes:

        print(
            "\n--------------------------------"
        )

        print(
            "Balsa:",
            ajuste["placa"]
        )

        print(
            "Viagem:",
            ajuste["codigo_viagem"]
        )

        print(
            "Tipo:",
            ajuste["tipo_ajuste"]
        )

        print(
            "Anterior:",
            ajuste["valor_anterior"]
        )

        print(
            "Novo:",
            ajuste["valor_novo"]
        )

        print(
            "Motivo:",
            ajuste["motivo"]
        )

        print(
            "Data:",
            ajuste["data_ajuste"]
        )


# ============================================================
# 2. SITUAÇÃO ATUAL DA VALENCIA
# ============================================================

situacao = consultar_situacao_balsa(
    "VAL0009"
)


print(
    "\n========================================"
)

print(
    " SITUAÇÃO ATUAL DA VALENCIA"
)

print(
    "========================================"
)


if situacao is None:

    print(
        "Nenhuma viagem aberta encontrada."
    )


else:

    print(
        "Balsa:",
        situacao["balsa"]
    )

    print(
        "Viagem:",
        situacao["codigo_viagem"]
    )

    print(
        "Status:",
        situacao["status"]
    )


    # ========================================================
    # VALENCIA EM VIAGEM
    # ========================================================

    if situacao["status"] == "Em viagem":

        print(
            "Trajeto:",
            situacao["trajeto"]
        )

        print(
            "Carga:",
            situacao["carga"]
        )

        print(
            "Início:",
            situacao["data_inicio"]
        )

        print(
            "Tempo em viagem:",
            situacao["tempo_em_viagem"]
        )

        print(
            "Prazo:",
            situacao["prazo_horas"],
            "horas"
        )


        # --------------------------------------------
        # TEMPO RESTANTE
        # --------------------------------------------

        if (
            situacao["tempo_restante"]
            is not None
        ):

            print(
                "Tempo restante:",
                situacao["tempo_restante"]
            )


        # --------------------------------------------
        # TEMPO EXCEDIDO
        # --------------------------------------------

        elif (
            situacao["tempo_excedido"]
            is not None
        ):

            print(
                "Tempo excedido:",
                situacao["tempo_excedido"]
            )


        print(
            "Situação do prazo:",
            situacao["situacao_prazo"]
        )


        # ====================================================
        # ETA
        # ====================================================

        print(
            "Último ponto:",
            situacao["ultimo_ponto"]
        )

        print(
            "Data último ponto:",
            situacao["data_ultimo_ponto"]
        )

        print(
            "Próximo ponto:",
            situacao["proximo_ponto"]
        )

        print(
            "ETA base destino:",
            formatar_data(
                situacao["eta_base_destino"]
            )
        )

        print(
            "ETA próximo ponto:",
            formatar_data(
                situacao["eta_proximo_ponto"]
            )
        )

        print(
            "ETA destino:",
            formatar_data(
                situacao["eta_destino"]
            )
        )

        print(
            "Fonte ETA:",
            situacao["fonte_eta"]
        )


    # ========================================================
    # VALENCIA AGUARDANDO CARREGAMENTO
    # ========================================================

    elif (
        situacao["status"]
        == "Aguardando carregamento"
    ):

        print(
            "Porto atual:",
            situacao["porto_atual"]
        )

        print(
            "Tempo aguardando:",
            situacao["tempo_aguardando"]
        )


# ============================================================
# 3. SITUAÇÃO DE TODAS AS BALSAS
# ============================================================

situacoes = (
    consultar_situacao_todas_balsas()
)


print(
    "\n========================================"
)

print(
    " SITUAÇÃO ATUAL DAS BALSAS"
)

print(
    "========================================"
)


print(
    "Total de balsas:",
    len(situacoes)
)


# ============================================================
# 4. EXIBIR CADA BALSA
# ============================================================

for balsa in situacoes:

    print(
        "\n--------------------------------"
    )


    print(
        "Balsa:",
        balsa["balsa"]
    )

    print(
        "Placa:",
        balsa["placa"]
    )

    print(
        "Viagem:",
        balsa["codigo_viagem"]
    )

    print(
        "Status:",
        balsa["status"]
    )


    # ========================================================
    # BALSA EM VIAGEM
    # ========================================================

    if balsa["status"] == "Em viagem":

        print(
            "Trajeto:",
            balsa["trajeto"]
        )

        print(
            "Carga:",
            balsa["carga"]
        )

        print(
            "Início:",
            balsa["data_inicio"]
        )

        print(
            "Tempo em viagem:",
            balsa["tempo_em_viagem"]
        )

        print(
            "Prazo:",
            balsa["prazo_horas"],
            "horas"
        )


        # ====================================================
        # TEMPO RESTANTE
        # ====================================================

        if (
            balsa["tempo_restante"]
            is not None
        ):

            print(
                "Tempo restante:",
                balsa["tempo_restante"]
            )


        # ====================================================
        # TEMPO EXCEDIDO
        # ====================================================

        elif (
            balsa["tempo_excedido"]
            is not None
        ):

            print(
                "Tempo excedido:",
                balsa["tempo_excedido"]
            )


        print(
            "Situação do prazo:",
            balsa["situacao_prazo"]
        )


        # ====================================================
        # ACOMPANHAMENTO DE ROTA / ETA
        # ====================================================

        print(
            "Último ponto confirmado:",
            balsa["ultimo_ponto"]
        )

        print(
            "Data do último ponto:",
            balsa["data_ultimo_ponto"]
        )

        print(
            "Próximo ponto:",
            balsa["proximo_ponto"]
        )

        print(
            "ETA base destino:",
            formatar_data(
                balsa["eta_base_destino"]
            )
        )

        print(
            "ETA próximo ponto:",
            formatar_data(
                balsa["eta_proximo_ponto"]
            )
        )

        print(
            "ETA destino:",
            formatar_data(
                balsa["eta_destino"]
            )
        )

        print(
            "Fonte ETA:",
            balsa["fonte_eta"]
        )


    # ========================================================
    # BALSA AGUARDANDO CARREGAMENTO
    # ========================================================

    elif (
        balsa["status"]
        == "Aguardando carregamento"
    ):

        print(
            "Porto atual:",
            balsa["porto_atual"]
        )


        if (
            balsa["tempo_aguardando"]
            is not None
        ):

            print(
                "Tempo aguardando:",
                balsa["tempo_aguardando"]
            )


        else:

            print(
                "Tempo aguardando: "
                "não foi possível calcular"
            )


    # ========================================================
    # BALSA SEM VIAGEM ABERTA
    # ========================================================

    elif (
        balsa["status"]
        == "Sem viagem aberta"
    ):

        print(
            "Nenhuma viagem aberta encontrada."
        )