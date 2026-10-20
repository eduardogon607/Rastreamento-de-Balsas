# ============================================================
# MAIN.PY
#
# Orquestrador principal do sistema.
#
# FLUXO:
#
# 1. Verificar se as viagens atuais foram inicializadas
# 2. Buscar eventos na API TotalTrack
# 3. Tratar os registros recebidos
# 4. Salvar os eventos em area_restrita
# 5. Processar os trechos reais das viagens
# 6. Processar saídas e chegadas
# 7. Classificar viagens finalizadas para o ETA
# 8. Exibir resumo para conferência
#
# REGRAS IMPORTANTES:
#
# - O histórico de trechos é processado antes da finalização
#   das viagens.
#
# - Isso garante que o último trecho até o porto de destino
#   seja registrado ainda na viagem correta.
#
# - Nenhum trecho alimenta imediatamente a média dinâmica.
#
# - Somente depois da viagem terminar ela é classificada.
#
# - Apenas viagens completas e sem trechos atípicos podem
#   alimentar o ETA dinâmico.
#
# - O ETA utiliza as 3 últimas viagens válidas quando houver
#   histórico suficiente para aquele trecho.
#
# - Balsas em stand-by (sem viagem aberta mas com histórico
#   finalizado) NÃO travam a execução — apenas são reportadas.
# ============================================================


from datetime import datetime


# ============================================================
# API TOTALTRACK
# ============================================================

from totaltrack import buscar_dados, ErroTotalTrack


# ============================================================
# TRATAMENTO DOS DADOS
# ============================================================

from tratamento import tratar_dados


# ============================================================
# ROTAS
# ============================================================

from rotas import obter_rota


# ============================================================
# BANCO DE DADOS
# ============================================================

from banco import (
    salvar_dados,
    consultar_dados,
    contar_registros,
    consultar_viagens,
    consultar_eventos_cronologicos,
    buscar_viagem_aberta,
    buscar_balsas_ativas,
    buscar_ultima_viagem_finalizada,
)


# ============================================================
# REGRAS DAS VIAGENS
# ============================================================

from viagem import (
    iniciar_viagem,
    finalizar_viagem
)


# ============================================================
# PROCESSAMENTO DOS TRECHOS / ETA
# ============================================================

from processamento_trechos import (
    processar_trecho,
    classificar_viagem_para_eta
)


# ============================================================
# CONVERTER DATA
# ============================================================

def converter_data(data):

    # Caso já seja datetime.
    if isinstance(data, datetime):
        return data

    # Caso venha como texto do SQLite.
    return datetime.strptime(
        data,
        "%Y-%m-%d %H:%M:%S"
    )


# ============================================================
# OBTER VIAGENS ATUALMENTE ABERTAS
# ============================================================

def obter_viagens_abertas():

    viagens = consultar_viagens()

    viagens_abertas = []

    for viagem in viagens:

        if viagem["data_fim"] is None:

            viagens_abertas.append(
                viagem
            )

    return viagens_abertas


# ============================================================
# PREPARAR EVENTOS DA ROTA DE UMA VIAGEM
# ============================================================

def preparar_eventos_rota(viagem, eventos, data_limite=None):
    """Seleciona uma única passagem pela rota, dentro do período da viagem."""

    if viagem["data_inicio"] is None:
        return []

    rota = obter_rota(viagem["origem"], viagem["destino"])

    if not rota:
        return []

    pontos = [trecho["ponto"] for trecho in rota]

    inicio = converter_data(viagem["data_inicio"])

    limites = [
        converter_data(data)
        for data in (viagem.get("data_fim"), data_limite)
        if data is not None
    ]

    fim = min(limites) if limites else None

    resultado = [{
        "placa": viagem["placa"],
        "balsa": viagem["balsa"],
        "evento": "Entrada",
        "area": pontos[0],
        "dataGPS": viagem["data_inicio"],
    }]

    candidatos = []

    for evento in eventos:

        if evento["placa"] != viagem["placa"] or evento["evento"] != "Entrada":
            continue

        if evento["area"] not in pontos:
            continue

        data = converter_data(evento["dataGPS"])

        if data < inicio or (fim is not None and data > fim):
            continue

        candidatos.append(evento)

    candidatos.sort(key=lambda evento: converter_data(evento["dataGPS"]))

    ultimo_indice = 0

    for evento in candidatos:

        indice = pontos.index(evento["area"])
        data = converter_data(evento["dataGPS"])

        # Entrada na origem exatamente no início não representa um retorno.
        if indice == 0 and data == inicio:
            continue

        # Um retorno à origem torna a continuação ambígua.
        if indice == 0:
            print(f"Atenção: {viagem['codigo_viagem']} retornou à origem em "
                  f"{evento['dataGPS']}. Confira as datas da viagem.")
            break

        if indice == ultimo_indice:
            continue

        if indice < ultimo_indice:
            print(f"Atenção: {viagem['codigo_viagem']} tem pontos fora da "
                  "sequência. Continuação dos trechos suspensa para conferência.")
            break

        resultado.append(evento)
        ultimo_indice = indice

        # A primeira chegada ao destino encerra esta passagem pela rota.
        if indice == len(pontos) - 1:
            break

    return resultado


# ============================================================
# PROCESSAR HISTÓRICO DOS TRECHOS
# ============================================================

def processar_historico_trechos(viagem_alvo=None, data_limite=None):

    print(
        "\n--- PROCESSAMENTO DOS TRECHOS ---"
    )

    # ========================================================
    # BUSCAR EVENTOS SALVOS
    # ========================================================

    eventos = (
        consultar_eventos_cronologicos()
    )

    # ========================================================
    # BUSCAR VIAGENS ABERTAS
    # ========================================================

    viagens_abertas = (
        [viagem_alvo] if viagem_alvo is not None else obter_viagens_abertas()
    )

    total_processados = 0
    total_atipicos = 0

    # ========================================================
    # PERCORRER VIAGENS
    # ========================================================

    for viagem in viagens_abertas:

        # ====================================================
        # SOMENTE VIAGENS EM ANDAMENTO
        # ====================================================

        if (
            viagem["status"]
            != "Em viagem"
        ):
            continue

        if viagem["data_inicio"] is None:
            continue

        # ====================================================
        # PREPARAR SEQUÊNCIA DOS PONTOS
        # ====================================================

        eventos_rota = (
            preparar_eventos_rota(
                viagem,
                eventos,
                data_limite=data_limite
            )
        )

        # Precisamos de pelo menos:
        #
        # origem + destino do trecho.
        if len(eventos_rota) < 2:
            continue

        # ====================================================
        # PROCESSAR PARES CONSECUTIVOS
        # ====================================================

        for indice in range(
            len(eventos_rota) - 1
        ):

            evento_origem = (
                eventos_rota[
                    indice
                ]
            )

            evento_destino = (
                eventos_rota[
                    indice + 1
                ]
            )

            resultado = (
                processar_trecho(
                    viagem=
                        viagem,

                    evento_origem=
                        evento_origem,

                    evento_destino=
                        evento_destino
                )
            )

            # Pontos não consecutivos,
            # dados inválidos etc.
            if not resultado:
                continue

            total_processados += 1

            if resultado["atipico"]:
                total_atipicos += 1

            # =================================================
            # LOG DO TRECHO
            # =================================================

            print(
                "\n",
                resultado[
                    "codigo_viagem"
                ],
                "|",
                resultado[
                    "ponto_origem"
                ],
                "->",
                resultado[
                    "ponto_destino"
                ]
            )

            duracao_horas = (
                resultado[
                    "duracao_minutos"
                ]
                / 60
            )

            media_horas = (
                resultado[
                    "media_referencia_minutos"
                ]
                / 60
            )

            desvio_horas = (
                resultado[
                    "desvio_minutos"
                ]
                / 60
            )

            print(
                "Real:",
                round(
                    duracao_horas,
                    2
                ),
                "h"
            )

            print(
                "Referência:",
                round(
                    media_horas,
                    2
                ),
                "h"
            )

            print(
                "Desvio:",
                round(
                    desvio_horas,
                    2
                ),
                "h"
            )

            print(
                "Fonte:",
                resultado[
                    "fonte_media"
                ]
            )

            print(
                "Atípico:",
                resultado[
                    "atipico"
                ]
            )

            print(
                "Liberado para ETA:",
                resultado[
                    "usar_no_eta"
                ]
            )

    # ========================================================
    # RESUMO
    # ========================================================

    print(
        "\nTrechos analisados:",
        total_processados
    )

    print(
        "Trechos atípicos encontrados:",
        total_atipicos
    )


# ============================================================
# 1. VERIFICAR SE O BANCO FOI INICIALIZADO
# ============================================================
#
# Consultamos as viagens já existentes no SQLite.
#
# Uma viagem é considerada aberta quando data_fim é None.
# Isso inclui tanto uma viagem em andamento quanto uma
# viagem aguardando carregamento, conforme as regras
# operacionais definidas no módulo viagem.py.
#
# REGRA NOVA:
#
# Uma balsa ativa sem viagem aberta NÃO é mais tratada
# automaticamente como inconsistência. Precisamos distinguir:
#
#   1. Balsa em stand-by (já finalizou viagem e ainda não
#      começou a próxima). Isso é NORMAL no fluxo operacional.
#      NÃO trava a execução.
#
#   2. Balsa nunca inicializada (nenhuma viagem registrada
#      nem aberta nem finalizada). Isso PRECISA ser conferido
#      antes de consultar a API. TRAVA a execução.
#
#   3. Balsa com múltiplas viagens abertas simultâneas.
#      Isso é corrupção real. TRAVA a execução.
# ============================================================

viagens_existentes = (
    consultar_viagens()
)


# ============================================================
# IDENTIFICAR PLACAS COM VIAGEM ABERTA
# ============================================================

# Conjunto de placas com pelo menos uma viagem aberta
placas_inicializadas = {
    viagem["placa"]
    for viagem in viagens_existentes
    if viagem["data_fim"] is None
}


# ============================================================
# DETECTAR PLACAS COM MÚLTIPLAS VIAGENS ABERTAS
# ============================================================

# Conta quantas viagens abertas cada placa tem.
# Se alguma tiver mais de uma, é inconsistência real.
from collections import Counter

contagem_abertas = Counter(
    viagem["placa"]
    for viagem in viagens_existentes
    if viagem["data_fim"] is None
)

placas_com_multiplas_abertas = {
    placa
    for placa, qtd in contagem_abertas.items()
    if qtd > 1
}


# ============================================================
# CONSULTAR BALSAS ATIVAS
# ============================================================

balsas_ativas = (
    buscar_balsas_ativas()
)

placas_ativas = set(
    balsas_ativas
)

total_balsas = len(
    placas_ativas
)


# ============================================================
# IDENTIFICAR BALSAS SEM VIAGEM ABERTA
# ============================================================

placas_sem_viagem = (
    placas_ativas
    - placas_inicializadas
)


# ============================================================
# CLASSIFICAR BALSAS SEM VIAGEM ABERTA
# ============================================================
#
# Para cada balsa ativa sem viagem aberta, decidimos se ela:
#
#   - está em stand-by legítimo (tem histórico finalizado)
#     → OK, não trava.
#
#   - nunca foi inicializada (nenhum histórico)
#     → PRECISA conferência, trava.
# ============================================================

balsas_em_standby = []
balsas_nunca_inicializadas = []

for placa in sorted(placas_sem_viagem):

    ultima_finalizada = buscar_ultima_viagem_finalizada(placa)

    if ultima_finalizada is not None:
        balsas_em_standby.append(placa)
    else:
        balsas_nunca_inicializadas.append(placa)


# ============================================================
# PROTEÇÃO — INCONSISTÊNCIAS REAIS
# ============================================================
#
# Só travamos se houver:
#
#   1. Balsa ativa que nunca teve viagem (precisa inicializar).
#   2. Balsa com múltiplas viagens abertas ao mesmo tempo
#      (corrupção de dados).
#
# Balsas em stand-by são apenas reportadas e o processamento
# continua normalmente.
# ============================================================

precisa_travar = False

if balsas_nunca_inicializadas:
    precisa_travar = True

if placas_com_multiplas_abertas:
    precisa_travar = True


if precisa_travar:

    print(
        "\nATENÇÃO:"
    )

    print(
        "Foram encontradas inconsistências que impedem "
        "a execução segura."
    )

    print(
        "Balsas cadastradas:",
        total_balsas
    )

    print(
        "Balsas ativas com viagem aberta:",
        len(
            placas_ativas
            & placas_inicializadas
        )
    )

    # --------------------------------------------------------
    # BALSAS NUNCA INICIALIZADAS
    # --------------------------------------------------------

    if balsas_nunca_inicializadas:

        print(
            "\nBalsas ativas SEM NENHUMA viagem registrada "
            "(precisam ser inicializadas):"
        )

        for placa in balsas_nunca_inicializadas:
            print(
                "- Placa:",
                placa
            )

    # --------------------------------------------------------
    # BALSAS COM MÚLTIPLAS VIAGENS ABERTAS
    # --------------------------------------------------------

    if placas_com_multiplas_abertas:

        print(
            "\nBalsas com MAIS DE UMA viagem aberta "
            "(corrupção — conferir manualmente):"
        )

        for placa in sorted(placas_com_multiplas_abertas):
            print(
                "- Placa:",
                placa,
                "| quantidade de viagens abertas:",
                contagem_abertas[placa]
            )

    print(
        "\nConfira as viagens dessas balsas "
        "antes de continuar."
    )

    print(
        "\nProcesso encerrado por segurança."
    )

    raise SystemExit(1)


# ============================================================
# BALSAS EM STAND-BY — APENAS INFORMATIVO
# ============================================================
#
# Balsas que finalizaram a viagem anterior e ainda não
# começaram a próxima estão em stand-by. Isso é normal.
# Reportamos para visibilidade, mas NÃO travamos.
# ============================================================

if balsas_em_standby:

    print(
        "\nInformação: balsas em stand-by "
        "(aguardando próxima viagem):"
    )

    for placa in balsas_em_standby:

        ultima = buscar_ultima_viagem_finalizada(placa)

        print(
            "- Placa:",
            placa,
            "| última viagem finalizada em:",
            ultima.get("data_fim") if ultima else "—"
        )

    print(
        "Essas balsas não bloqueiam a execução."
    )


# ============================================================
# VALIDAÇÃO CONCLUÍDA
# ============================================================

print(
    "\nValidação OK:",
    total_balsas,
    "balsas ativas verificadas."
)

print(
    "Balsas com viagem aberta:",
    len(placas_ativas & placas_inicializadas)
)

if balsas_em_standby:
    print(
        "Balsas em stand-by:",
        len(balsas_em_standby)
    )


# ============================================================
# 2. BUSCAR DADOS DA TOTALTRACK
# ============================================================

# Uma falha de coleta encerra com código 1 antes de salvar qualquer evento.
try:
    registros = buscar_dados()
except ErroTotalTrack as erro:
    print(f"\nFalha na coleta TotalTrack: {erro}")
    print("Nenhum evento desta coleta foi salvo. Tente novamente após verificar a falha.")
    raise SystemExit(1) from erro


# ============================================================
# API SEM RETORNO
# ============================================================

if not registros:

    print(
        "Nenhum registro foi retornado."
    )

    print(
        "Processo encerrado!"
    )

    exit()


print(
    "Registros recebidos da API:",
    len(registros)
)


# ============================================================
# 3. TRATAR DADOS
# ============================================================

df = tratar_dados(
    registros
)


print(
    "Registros após tratamento:",
    len(df)
)


# ============================================================
# DATAFRAME VAZIO
# ============================================================

if df.empty:

    print(
        "\nNenhum evento das balsas "
        "monitoradas foi encontrado."
    )

    print(
        "Processo encerrado sem alterações."
    )

    exit()


# ============================================================
# 4. SALVAR EVENTOS
# ============================================================

salvar_dados(
    df
)


# ============================================================
# 5. HISTÓRICO DOS TRECHOS
# Os trechos são calculados antes de cada chegada ao destino e, ao final,
# para as viagens que continuam abertas. Isso inclui saídas deste lote.
# ============================================================


# ============================================================
# 6. PROCESSAR EVENTOS DAS VIAGENS
# ============================================================

for _, linha in df.iterrows():

    # ========================================================
    # EVENTO DE SAÍDA
    # ========================================================

    if linha["evento"] == "Saída":

        resultado_inicio = (
            iniciar_viagem(
                placa=
                    linha["placa"],

                balsa=
                    linha["balsa"],

                evento=
                    linha["evento"],

                area=
                    linha["area"],

                dataGPS=
                    linha["dataGPS"]
            )
        )

        if resultado_inicio:

            print(
                "\n========================================"
            )

            print(
                " VIAGEM INICIADA"
            )

            print(
                "========================================"
            )

            print(
                "Balsa:",
                linha["balsa"]
            )

            print(
                "Porto:",
                linha["area"]
            )

            print(
                "Data:",
                linha["dataGPS"]
            )

    # ========================================================
    # EVENTO DE ENTRADA
    # ========================================================

    elif linha["evento"] == "Entrada":

        # ====================================================
        # GUARDAR A VIAGEM ANTES DA FINALIZAÇÃO
        # ====================================================

        # Isso é MUITO importante.
        #
        # finalizar_viagem() finaliza a viagem atual
        # e cria imediatamente a próxima.
        #
        # Portanto precisamos guardar qual viagem estava
        # aberta ANTES de chamar finalizar_viagem().
        viagem_antes_finalizar = (
            buscar_viagem_aberta(
                linha["placa"]
            )
        )

        # ====================================================
        # TENTAR FINALIZAR
        # ====================================================

        if viagem_antes_finalizar and viagem_antes_finalizar["data_inicio"]:

            rota_chegada = obter_rota(
                viagem_antes_finalizar["origem"],
                viagem_antes_finalizar["destino"]
            )

            if (rota_chegada
                    and linha["area"] == rota_chegada[-1]["ponto"]
                    and converter_data(linha["dataGPS"]) >= converter_data(
                        viagem_antes_finalizar["data_inicio"])):

                processar_historico_trechos(
                    viagem_alvo=viagem_antes_finalizar,
                    data_limite=linha["dataGPS"]
                )

        resultado_fim = (
            finalizar_viagem(
                placa=
                    linha["placa"],

                evento=
                    linha["evento"],

                area=
                    linha["area"],

                dataGPS=
                    linha["dataGPS"]
            )
        )

        # ====================================================
        # VIAGEM REALMENTE FINALIZADA
        # ====================================================

        if resultado_fim:

            print(
                "\n========================================"
            )

            print(
                " VIAGEM FINALIZADA"
            )

            print(
                "========================================"
            )

            print(
                "Balsa:",
                linha["balsa"]
            )

            print(
                "Porto:",
                linha["area"]
            )

            print(
                "Data:",
                linha["dataGPS"]
            )

            # =================================================
            # CLASSIFICAR PARA O ETA
            # =================================================

            if (
                viagem_antes_finalizar
                is not None
            ):

                classificacao = (
                    classificar_viagem_para_eta(
                        viagem_antes_finalizar
                    )
                )

                if classificacao is not None:

                    print(
                        "\n--- CLASSIFICAÇÃO ETA ---"
                    )

                    print(
                        "Viagem:",
                        classificacao[
                            "codigo_viagem"
                        ]
                    )

                    print(
                        "Válida para ETA:",
                        classificacao[
                            "valida_eta"
                        ]
                    )

                    print(
                        "Viagem atípica:",
                        classificacao[
                            "viagem_atipica"
                        ]
                    )

                    print(
                        "Motivo:",
                        classificacao[
                            "motivo"
                        ]
                    )


# ============================================================
# PROCESSAR AS VIAGENS QUE CONTINUAM EM ANDAMENTO
# ============================================================

processar_historico_trechos()


# ============================================================
# 7. RESUMO FINAL
# ============================================================

total_banco = (
    contar_registros()
)

print(
    "\n========================================"
)

print(
    " PROCESSO FINALIZADO"
)

print(
    "========================================"
)

print(
    "Total de eventos no banco:",
    total_banco
)


# ============================================================
# 8. EVENTOS MAIS RECENTES
# ============================================================

dados_banco = (
    consultar_dados()
)

print(
    "\n--- EVENTOS MAIS RECENTES ---"
)

for registro in dados_banco[:10]:

    print(
        registro
    )


# ============================================================
# 9. VIAGENS MAIS RECENTES
# ============================================================

viagens_banco = (
    consultar_viagens()
)

print(
    "\n--- VIAGENS MAIS RECENTES ---"
)

for viagem in viagens_banco[:20]:

    print(
        viagem
    )