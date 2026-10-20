# ============================================================
# ADMIN.PY
#
# Camada administrativa do sistema.
#
# Reúne operações que exigem intervenção manual,
# consultas da situação atual das balsas e cálculos
# administrativos.
#
# Também integra:
#
# - tempo em viagem;
# - tempo aguardando carregamento;
# - situação do prazo;
# - ETA base;
# - último ponto confirmado;
# - próximo ponto previsto;
# - ETA do próximo ponto;
# - ETA do destino final.
#
# As regras de negócio continuam em viagem.py
# e o acesso ao banco continua em banco.py.
# ============================================================


from datetime import datetime


# ============================================================
# REGRAS DE VIAGEM
# ============================================================

from viagem import (
    corrigir_chegada_manual,
    corrigir_saida_manual
)


# ============================================================
# ACESSO AO BANCO
# ============================================================

from banco import (
    consultar_ajustes,
    buscar_viagem_aberta,
    buscar_ultima_viagem_finalizada,
    buscar_ultimo_ponto_rota,
    buscar_referencia_balsa,
    buscar_balsas_ativas
)


# ============================================================
# ROTAS E ETA
# ============================================================

from rotas import obter_rota

from eta import (
    calcular_eta_base,
    calcular_eta_por_ponto
)


# ============================================================
# FORMATAR HORAS PARA TEXTO
# ============================================================

def formatar_duracao_horas(horas):

    # Caso não exista valor para calcular.
    if horas is None:
        return None

    # Converte o total de horas para minutos inteiros.
    total_minutos = round(horas * 60)

    # Calcula os dias completos.
    dias = total_minutos // 1440

    # Minutos restantes depois dos dias.
    minutos_restantes = total_minutos % 1440

    # Calcula as horas restantes.
    horas_restantes = minutos_restantes // 60

    # Calcula os minutos restantes.
    minutos = minutos_restantes % 60

    partes = []


    # ========================================================
    # DIAS
    # ========================================================

    if dias > 0:

        partes.append(
            f"{dias} dia"
            if dias == 1
            else f"{dias} dias"
        )


    # ========================================================
    # HORAS
    # ========================================================

    if horas_restantes > 0:

        partes.append(
            f"{horas_restantes} hora"
            if horas_restantes == 1
            else f"{horas_restantes} horas"
        )


    # ========================================================
    # MINUTOS
    # ========================================================

    if minutos > 0:

        partes.append(
            f"{minutos} minuto"
            if minutos == 1
            else f"{minutos} minutos"
        )


    # Caso o tempo seja inferior a 1 minuto.
    if not partes:

        return "Menos de 1 minuto"


    return ", ".join(partes)


# ============================================================
# REGISTRAR CHEGADA MANUAL
# ============================================================

def registrar_chegada_manual(
    placa,
    data_chegada,
    motivo
):

    # Converte a data recebida como texto para datetime.
    data_chegada = datetime.strptime(
        data_chegada,
        "%Y-%m-%d %H:%M:%S"
    )

    # Encaminha a correção para viagem.py.
    return corrigir_chegada_manual(
        placa=placa,
        data_chegada=data_chegada,
        motivo=motivo
    )


# ============================================================
# REGISTRAR SAÍDA MANUAL
# ============================================================

def registrar_saida_manual(
    placa,
    data_saida,
    motivo
):

    # Converte a data recebida como texto para datetime.
    data_saida = datetime.strptime(
        data_saida,
        "%Y-%m-%d %H:%M:%S"
    )

    # Encaminha a correção para viagem.py.
    return corrigir_saida_manual(
        placa=placa,
        data_saida=data_saida,
        motivo=motivo
    )


# ============================================================
# LISTAR AJUSTES REALIZADOS
# ============================================================

def listar_ajustes():

    return consultar_ajustes()


# ============================================================
# CONSULTAR SITUAÇÃO ATUAL DA BALSA
# ============================================================

def consultar_situacao_balsa(placa):

    # ========================================================
    # BUSCAR VIAGEM ATUAL
    # ========================================================

    viagem = buscar_viagem_aberta(
        placa
    )

    if viagem is None:
        return None


    # ========================================================
    # DADOS BÁSICOS
    # ========================================================

    situacao = {

        "placa":
            viagem["placa"],

        "balsa":
            viagem["balsa"],

        "codigo_viagem":
            viagem["codigo_viagem"],

        "origem":
            viagem["origem"],

        "destino":
            viagem["destino"],

        "trajeto":
            viagem["trajeto"],

        "carga":
            viagem["carga"],

        "prazo_horas":
            viagem["prazo_horas"],

        "data_inicio":
            viagem["data_inicio"],

        "status":
            viagem["status"],


        # ====================================================
        # TEMPOS NUMÉRICOS
        # ====================================================

        "horas_em_viagem": None,
        "horas_aguardando": None,
        "horas_restantes": None,
        "horas_excedidas": None,


        # ====================================================
        # TEMPOS FORMATADOS
        # ====================================================

        "tempo_em_viagem": None,
        "tempo_aguardando": None,
        "tempo_restante": None,
        "tempo_excedido": None,


        # ====================================================
        # PRAZO / LOCALIZAÇÃO
        # ====================================================

        "situacao_prazo": None,
        "porto_atual": None,


        # ====================================================
        # ETA
        # ====================================================

        "ultimo_ponto": None,
        "data_ultimo_ponto": None,

        "proximo_ponto": None,

        "eta_base_destino": None,
        "eta_proximo_ponto": None,
        "eta_destino": None,

        "fonte_eta": None
    }


    # Momento atual utilizado nos cálculos.
    agora = datetime.now()


    # ========================================================
    # BALSA EM VIAGEM
    # ========================================================

    if viagem["status"] == "Em viagem":


        # ====================================================
        # PROTEÇÃO CONTRA DATA DE INÍCIO VAZIA
        # ====================================================
        #
        # Uma viagem marcada como "Em viagem" deveria SEMPRE
        # ter data_inicio preenchida. Se vier vazia ou None,
        # retornamos a situação parcial em vez de estourar.
        # ====================================================

        if not viagem.get("data_inicio"):
            return situacao


        # ====================================================
        # CONVERTER DATA DE INÍCIO
        # ====================================================

        try:
            inicio = datetime.strptime(
                viagem["data_inicio"],
                "%Y-%m-%d %H:%M:%S"
            )
        except (ValueError, TypeError):
            return situacao


        # ====================================================
        # CALCULAR TEMPO EM VIAGEM
        # ====================================================

        duracao = (
            agora - inicio
        )

        horas_em_viagem = (
            duracao.total_seconds()
            / 3600
        )


        situacao["horas_em_viagem"] = (
            horas_em_viagem
        )


        situacao["tempo_em_viagem"] = (
            formatar_duracao_horas(
                horas_em_viagem
            )
        )


        # ====================================================
        # CALCULAR DIFERENÇA PARA O PRAZO
        # ====================================================

        prazo_horas = viagem.get("prazo_horas") or 0

        diferenca = (
            horas_em_viagem
            - prazo_horas
        )


        # ====================================================
        # VIAGEM DENTRO DO PRAZO
        # ====================================================

        if diferenca < 0:

            horas_restantes = abs(
                diferenca
            )

            situacao["horas_restantes"] = (
                horas_restantes
            )

            situacao["tempo_restante"] = (
                formatar_duracao_horas(
                    horas_restantes
                )
            )


            # --------------------------------------------
            # MAIS DE 24 HORAS RESTANTES
            # --------------------------------------------

            if horas_restantes > 24:

                situacao["situacao_prazo"] = (
                    "Dentro do prazo"
                )


            # --------------------------------------------
            # ENTRE 12 E 24 HORAS
            # --------------------------------------------

            elif horas_restantes > 12:

                situacao["situacao_prazo"] = (
                    "Atenção"
                )


            # --------------------------------------------
            # ATÉ 12 HORAS
            # --------------------------------------------

            else:

                situacao["situacao_prazo"] = (
                    "Próxima do prazo"
                )


        # ====================================================
        # PRAZO EXATAMENTE ATINGIDO
        # ====================================================

        elif diferenca == 0:

            situacao["situacao_prazo"] = (
                "No prazo"
            )

            situacao["horas_restantes"] = 0

            situacao["tempo_restante"] = (
                "Prazo atingido"
            )


        # ====================================================
        # ATRASO DE ATÉ 4 HORAS
        # ====================================================

        elif diferenca <= 4:

            situacao["situacao_prazo"] = (
                "Atrasada"
            )

            situacao["horas_excedidas"] = (
                diferenca
            )

            situacao["tempo_excedido"] = (
                formatar_duracao_horas(
                    diferenca
                )
            )


        # ====================================================
        # ATRASO CRÍTICO
        # ====================================================

        else:

            situacao["situacao_prazo"] = (
                "Atraso Crítico"
            )

            situacao["horas_excedidas"] = (
                diferenca
            )

            situacao["tempo_excedido"] = (
                formatar_duracao_horas(
                    diferenca
                )
            )


        # ====================================================
        # CALCULAR ETA
        # ====================================================

        rota = obter_rota(
            viagem["origem"],
            viagem["destino"]
        )


        if rota is not None:


            # =================================================
            # LISTA DE PONTOS VÁLIDOS
            # =================================================

            pontos_validos = [

                trecho["ponto"]

                for trecho in rota
            ]


            # =================================================
            # ETA BASE DO DESTINO
            # =================================================

            eta_base = calcular_eta_base(
                data_inicio=
                    viagem["data_inicio"],

                origem=
                    viagem["origem"],

                destino=
                    viagem["destino"]
            )


            situacao["eta_base_destino"] = (
                eta_base
            )


            # =================================================
            # BUSCAR ÚLTIMO PONTO REAL
            # =================================================

            ultimo_evento = (
                buscar_ultimo_ponto_rota(
                    placa=placa,

                    data_inicio=
                        viagem["data_inicio"],

                    pontos_validos=
                        pontos_validos
                )
            )


            # =================================================
            # EXISTE PONTO REAL CONFIRMADO
            # =================================================

            if ultimo_evento is not None:

                ponto_atual = (
                    ultimo_evento["area"]
                )

                data_ponto = (
                    ultimo_evento["dataGPS"]
                )


                resultado_eta = (
                    calcular_eta_por_ponto(
                        data_ponto=
                            data_ponto,

                        ponto_atual=
                            ponto_atual,

                        origem=
                            viagem["origem"],

                        destino=
                            viagem["destino"]
                    )
                )


                if resultado_eta is not None:

                    situacao["ultimo_ponto"] = (
                        ponto_atual
                    )

                    situacao["data_ultimo_ponto"] = (
                        data_ponto
                    )

                    situacao["proximo_ponto"] = (
                        resultado_eta[
                            "proximo_ponto"
                        ]
                    )

                    situacao[
                        "eta_proximo_ponto"
                    ] = (
                        resultado_eta[
                            "eta_proximo_ponto"
                        ]
                    )

                    situacao["eta_destino"] = (
                        resultado_eta[
                            "eta_destino"
                        ]
                    )

                    situacao["fonte_eta"] = (
                        "Último ponto confirmado"
                    )


            # =================================================
            # AINDA NÃO EXISTE PONTO REAL
            # =================================================

            else:

                # Enquanto nenhuma entrada em ponto da rota
                # existir no banco novo, utilizamos o ETA
                # calculado diretamente da saída.
                situacao["eta_destino"] = (
                    eta_base
                )


                # Primeiro ponto após o porto.
                if len(rota) > 1:

                    situacao["proximo_ponto"] = (
                        rota[1]["ponto"]
                    )


                situacao["fonte_eta"] = (
                    "Média base desde a saída"
                )


    # ========================================================
    # BALSA AGUARDANDO CARREGAMENTO
    # ========================================================

    elif viagem["status"] == "Aguardando carregamento":


        # ====================================================
        # IDENTIFICAR PORTO ATUAL
        # ====================================================

        origem = (
            viagem["origem"]
        )


        if origem == "BEL":

            situacao["porto_atual"] = (
                "Belém"
            )


        elif origem == "MAO":

            situacao["porto_atual"] = (
                "Manaus"
            )


        else:

            situacao["porto_atual"] = (
                origem
            )


        # ====================================================
        # BUSCAR VIAGEM ANTERIOR
        # ====================================================

        viagem_anterior = (
            buscar_ultima_viagem_finalizada(
                placa
            )
        )


        # ====================================================
        # POSSUI HISTÓRICO NO BANCO
        # ====================================================
        #
        # Protegemos contra data_fim vazia (None ou "")
        # para não estourar o strptime.
        # ====================================================

        if viagem_anterior is not None and viagem_anterior.get("data_fim"):

            try:
                data_chegada = (
                    datetime.strptime(
                        viagem_anterior["data_fim"],
                        "%Y-%m-%d %H:%M:%S"
                    )
                )
            except (ValueError, TypeError):
                return situacao


        # ====================================================
        # BANCO NOVO / FOTOGRAFIA INICIAL
        # ====================================================

        else:

            dados_balsa = (
                buscar_referencia_balsa(
                    placa
                )
            )


            if dados_balsa is None:
                return situacao


            data_chegada_texto = (
                dados_balsa.get(
                    "data_chegada_referencia"
                )
            )


            if not data_chegada_texto:
                return situacao


            try:
                data_chegada = (
                    datetime.strptime(
                        data_chegada_texto,
                        "%Y-%m-%d %H:%M:%S"
                    )
                )
            except (ValueError, TypeError):
                return situacao


        # ====================================================
        # CALCULAR TEMPO AGUARDANDO
        # ====================================================

        permanencia = (
            agora - data_chegada
        )

        horas_aguardando = (
            permanencia.total_seconds()
            / 3600
        )


        situacao["horas_aguardando"] = (
            horas_aguardando
        )


        situacao["tempo_aguardando"] = (
            formatar_duracao_horas(
                horas_aguardando
            )
        )


    return situacao


# ============================================================
# CONSULTAR SITUAÇÃO DE TODAS AS BALSAS
# ============================================================

def consultar_situacao_todas_balsas():

    situacoes = []


    # Consulta somente as balsas ativas no cadastro SQLite.
    balsas_ativas = buscar_balsas_ativas()

    for placa, dados_balsa in balsas_ativas.items():

        try:
            situacao = (
                consultar_situacao_balsa(
                    placa
                )
            )
        except Exception:
            # Se uma balsa específica falhar, não deixamos o
            # painel inteiro cair. Registramos uma situação
            # parcial vazia no lugar.
            situacao = None


        # ====================================================
        # BALSA COM VIAGEM ABERTA
        # ====================================================

        if situacao is not None:

            situacoes.append(
                situacao
            )


        # ====================================================
        # BALSA SEM VIAGEM ABERTA
        # ====================================================

        else:

            situacoes.append({

                "placa":
                    placa,

                "balsa":
                    dados_balsa["nome"],

                "codigo_viagem":
                    None,

                "origem":
                    None,

                "destino":
                    None,

                "trajeto":
                    None,

                "carga":
                    None,

                "prazo_horas":
                    None,

                "data_inicio":
                    None,

                "status":
                    "Sem viagem aberta",


                # ============================================
                # TEMPOS
                # ============================================

                "horas_em_viagem":
                    None,

                "horas_aguardando":
                    None,

                "horas_restantes":
                    None,

                "horas_excedidas":
                    None,

                "tempo_em_viagem":
                    None,

                "tempo_aguardando":
                    None,

                "tempo_restante":
                    None,

                "tempo_excedido":
                    None,


                # ============================================
                # SITUAÇÃO
                # ============================================

                "situacao_prazo":
                    None,

                "porto_atual":
                    None,


                # ============================================
                # ETA
                # ============================================

                "ultimo_ponto":
                    None,

                "data_ultimo_ponto":
                    None,

                "proximo_ponto":
                    None,

                "eta_base_destino":
                    None,

                "eta_proximo_ponto":
                    None,

                "eta_destino":
                    None,

                "fonte_eta":
                    None
            })


    return situacoes