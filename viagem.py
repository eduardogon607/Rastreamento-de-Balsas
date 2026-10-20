# ============================================================
# VIAGEM.PY
#
# Regras de negócio responsáveis pelo ciclo das viagens.
#
# Este arquivo NÃO executa SQL diretamente.
#
# Toda comunicação com SQLite passa pelo banco.py.
#
# Responsabilidades:
#
# - identificar início e fim das viagens;
# - consultar cadastro das balsas;
# - gerar códigos de viagem;
# - validar origem e destino;
# - calcular duração;
# - classificar prazo;
# - iniciar e finalizar viagens;
# - criar automaticamente a próxima viagem;
# - realizar correções manuais;
# - registrar auditoria.
# ============================================================


from datetime import datetime


from banco import (
    criar_tabela_viagens,
    buscar_ultima_viagem,
    salvar_viagem,
    buscar_viagem_aberta,
    finalizar_viagem_banco,
    iniciar_viagem_banco,
    criar_tabela_ajustes,
    registrar_ajuste,

    # Cadastro das balsas agora vem do SQLite.
    buscar_balsa
)


# ============================================================
# CONFIGURAÇÃO DAS ROTAS
# ============================================================

# BEL -> MAO
#
# Número de viagem:
# ímpar
#
# Carga:
# Cargas Diversas
#
# Prazo:
# 168 horas
#
#
# MAO -> BEL
#
# Número de viagem:
# par
#
# Carga:
# Motos Honda
#
# Prazo:
# 96 horas


GARAGENS = {

    "Porto Combitrans - Belém": {

        "origem": "BEL",

        "destino": "MAO",

        "trajeto": "↑ BEL x MAO",

        "carga": "Cargas Diversas",

        "prazo": 168
    },


    "Porto Combitrans - Manaus": {

        "origem": "MAO",

        "destino": "BEL",

        "trajeto": "↓ MAO x BEL",

        "carga": "Motos Honda",

        "prazo": 96
    }

}


# ============================================================
# CONVERTER DATA PARA DATETIME
# ============================================================

def converter_para_datetime(data):
    """
    Garante que as regras de viagem trabalhem sempre
    com objetos datetime.

    Aceita:

        datetime

    ou:

        "2026-08-17 13:27:00"
    """

    if isinstance(data, datetime):
        return data


    if isinstance(data, str):

        return datetime.strptime(
            data,
            "%Y-%m-%d %H:%M:%S"
        )


    raise TypeError(
        "A data deve ser datetime ou texto "
        "no formato YYYY-MM-DD HH:MM:SS."
    )


# ============================================================
# CONVERTER DATA PARA TEXTO
# ============================================================

def converter_data_para_texto(data):
    """
    Converte qualquer datetime para o formato padrão
    utilizado pelo SQLite.
    """

    data = converter_para_datetime(data)

    return data.strftime(
        "%Y-%m-%d %H:%M:%S"
    )


# ============================================================
# CONSULTAR BALSA
# ============================================================

def obter_dados_balsa(placa):
    """
    Consulta os dados cadastrais da balsa no SQLite.

    Antes:

        viagem.py
            ↓
        balsas.py

    Agora:

        viagem.py
            ↓
        banco.py
            ↓
        SQLite
            ↓
        tabela balsas

    Retorna:

        dicionário da balsa

    ou:

        None
    """

    dados_balsa = buscar_balsa(
        placa
    )


    # Balsa não cadastrada.
    if dados_balsa is None:
        return None


    # Uma balsa inativa não deve iniciar novas viagens.
    if dados_balsa["ativa"] == 0:
        return None


    return dados_balsa


# ============================================================
# CONSULTAR DADOS DO TRAJETO
# ============================================================

def obter_dados_trajeto(area):
    """
    Retorna as regras correspondentes a uma garagem.
    """

    return GARAGENS.get(
        area
    )


# ============================================================
# LOCALIZAR GARAGEM POR CIDADE
# ============================================================

def obter_garagem_por_origem(origem):
    """
    Localiza a garagem correspondente ao código da cidade.

    Exemplo:

        MAO

    retorna:

        Porto Combitrans - Manaus
    """

    for area, dados in GARAGENS.items():

        if dados["origem"] == origem:

            return area, dados


    return None, None


# ============================================================
# IDENTIFICAR INÍCIO DA VIAGEM
# ============================================================

def eh_inicio_viagem(
    evento,
    area
):
    """
    Uma viagem pode começar quando ocorre:

        evento = Saída

    em uma das garagens oficiais.
    """

    return (
        evento == "Saída"
        and
        area in GARAGENS
    )


# ============================================================
# IDENTIFICAR POSSÍVEL FIM DE VIAGEM
# ============================================================

def eh_fim_viagem(
    evento,
    area
):
    """
    Uma possível chegada ocorre quando existe:

        evento = Entrada

    em uma garagem oficial.

    O destino ainda será validado posteriormente.
    """

    return (
        evento == "Entrada"
        and
        area in GARAGENS
    )


# ============================================================
# GERAR CÓDIGO DA VIAGEM
# ============================================================

def gerar_codigo_viagem(
    placa,
    origem
):
    """
    Gera o código da próxima viagem.

    Primeiro procura a viagem mais recente no banco.

    Se nenhuma viagem existir, utiliza:

        ultima_viagem_referencia

    armazenada no cadastro da balsa.

    Regras:

        BEL -> MAO = número ímpar

        MAO -> BEL = número par
    """


    # ========================================================
    # CONSULTAR CADASTRO
    # ========================================================

    dados_balsa = obter_dados_balsa(
        placa
    )


    if dados_balsa is None:
        return None


    prefixo = dados_balsa[
        "prefixo"
    ]


    # ========================================================
    # CONSULTAR ÚLTIMA VIAGEM
    # ========================================================

    ultima_viagem_banco = (
        buscar_ultima_viagem(
            placa
        )
    )


    # ========================================================
    # JÁ EXISTE HISTÓRICO
    # ========================================================

    if ultima_viagem_banco is not None:

        codigo_anterior = (
            ultima_viagem_banco[
                "codigo_viagem"
            ]
        )


        try:

            # Exemplo:
            #
            # AN-12155
            #
            # rsplit("-", 1)
            #
            # ["AN", "12155"]

            numero = int(
                codigo_anterior.rsplit(
                    "-",
                    1
                )[1]
            ) + 1


        except (
            ValueError,
            IndexError
        ):

            return None


    # ========================================================
    # PRIMEIRA VIAGEM CONHECIDA
    # ========================================================

    else:

        numero = dados_balsa[
            "ultima_viagem_referencia"
        ]


        if numero is None:
            return None


    # ========================================================
    # VALIDAR PARIDADE
    # ========================================================

    # BEL -> MAO
    #
    # precisa ser ímpar.

    if (
        origem == "BEL"
        and
        numero % 2 == 0
    ):

        numero += 1


    # MAO -> BEL
    #
    # precisa ser par.

    elif (
        origem == "MAO"
        and
        numero % 2 != 0
    ):

        numero += 1


    return (
        f"{prefixo}-{numero}"
    )


# ============================================================
# CRIAR PRÓXIMA VIAGEM
# ============================================================

def criar_proxima_viagem(
    placa,
    balsa,
    dados_trajeto
):
    """
    Cria uma nova viagem com status:

        Aguardando carregamento

    Esta função centraliza a criação de viagens.
    """


    codigo_viagem = (
        gerar_codigo_viagem(
            placa,
            dados_trajeto["origem"]
        )
    )


    if codigo_viagem is None:
        return False


    salvar_viagem(

        codigo_viagem=codigo_viagem,

        placa=placa,

        balsa=balsa,

        origem=dados_trajeto[
            "origem"
        ],

        destino=dados_trajeto[
            "destino"
        ],

        trajeto=dados_trajeto[
            "trajeto"
        ],

        carga=dados_trajeto[
            "carga"
        ],

        prazo_horas=dados_trajeto[
            "prazo"
        ]

    )


    return True


# ============================================================
# INICIAR VIAGEM
# ============================================================

def iniciar_viagem(
    placa,
    balsa,
    evento,
    area,
    dataGPS
):
    """
    Processa automaticamente uma saída da garagem.

    Fluxo:

        Saída
          ↓
        identificar rota
          ↓
        buscar viagem aberta
          ↓
        validar origem
          ↓
        registrar data_inicio
          ↓
        status = Em viagem
    """


    # ========================================================
    # VALIDAR EVENTO
    # ========================================================

    if not eh_inicio_viagem(
        evento,
        area
    ):

        return False


    criar_tabela_viagens()


    # ========================================================
    # VALIDAR BALSA
    # ========================================================

    dados_balsa = obter_dados_balsa(
        placa
    )


    if dados_balsa is None:
        return False


    # ========================================================
    # IDENTIFICAR ROTA
    # ========================================================

    dados_trajeto = (
        obter_dados_trajeto(
            area
        )
    )


    if dados_trajeto is None:
        return False


    # ========================================================
    # BUSCAR VIAGEM ATUAL
    # ========================================================

    viagem_aberta = (
        buscar_viagem_aberta(
            placa
        )
    )


    # ========================================================
    # NÃO EXISTE VIAGEM
    # ========================================================

    if viagem_aberta is None:

        criou_viagem = (
            criar_proxima_viagem(

                placa=placa,

                balsa=dados_balsa[
                    "nome"
                ],

                dados_trajeto=dados_trajeto

            )
        )


        if not criou_viagem:
            return False


        viagem_aberta = (
            buscar_viagem_aberta(
                placa
            )
        )


        if viagem_aberta is None:
            return False


    # ========================================================
    # DADOS DA VIAGEM
    # ========================================================

    id_viagem = (
        viagem_aberta["id"]
    )


    origem_viagem = (
        viagem_aberta["origem"]
    )


    status_viagem = (
        viagem_aberta["status"]
    )


    garagem_atual = (
        dados_trajeto["origem"]
    )


    # ========================================================
    # VALIDAR ORIGEM
    # ========================================================

    if (
        garagem_atual
        !=
        origem_viagem
    ):

        return False


    # ========================================================
    # VALIDAR STATUS
    # ========================================================

    if (
        status_viagem
        !=
        "Aguardando carregamento"
    ):

        return False


    # ========================================================
    # REGISTRAR SAÍDA
    # ========================================================

    data_inicio = (
        converter_para_datetime(
            dataGPS
        )
    )


    iniciar_viagem_banco(

        id_viagem=id_viagem,

        data_inicio=data_inicio

    )


    return True


# ============================================================
# CLASSIFICAR PRAZO
# ============================================================

def classificar_viagem(
    data_inicio,
    data_fim,
    prazo_horas
):
    """
    Calcula:

    - duração da viagem;
    - diferença para o prazo;
    - classificação operacional.
    """


    inicio = (
        converter_para_datetime(
            data_inicio
        )
    )


    fim = (
        converter_para_datetime(
            data_fim
        )
    )


    # ========================================================
    # VALIDAR CRONOLOGIA
    # ========================================================

    if fim < inicio:

        raise ValueError(
            "A chegada não pode ocorrer "
            "antes da saída."
        )


    # ========================================================
    # CALCULAR DURAÇÃO
    # ========================================================

    duracao = (
        fim - inicio
    )


    duracao_horas = (
        duracao.total_seconds()
        /
        3600
    )


    diferenca = (
        duracao_horas
        -
        prazo_horas
    )


    # ========================================================
    # CLASSIFICAR
    # ========================================================

    if diferenca < 0:

        status = "Adiantada"


    elif diferenca == 0:

        status = "No Prazo"


    elif diferenca <= 4:

        status = "Atrasada"


    else:

        status = "Atraso Crítico"


    return (
        status,
        duracao_horas,
        diferenca
    )


# ============================================================
# CONCLUIR VIAGEM
# ============================================================

def concluir_viagem(
    viagem_aberta,
    data_chegada
):
    """
    Centraliza o encerramento da viagem.

    Pode ser utilizado tanto pela chegada automática
    quanto pela correção manual.
    """


    id_viagem = (
        viagem_aberta["id"]
    )


    prazo_horas = (
        viagem_aberta[
            "prazo_horas"
        ]
    )


    data_inicio = (
        viagem_aberta[
            "data_inicio"
        ]
    )


    if data_inicio is None:
        return None


    # ========================================================
    # CALCULAR RESULTADO
    # ========================================================

    (
        status_prazo,
        duracao_horas,
        diferenca_horas

    ) = classificar_viagem(

        data_inicio,

        data_chegada,

        prazo_horas

    )


    # ========================================================
    # FINALIZAR NO BANCO
    # ========================================================

    data_chegada = (
        converter_para_datetime(
            data_chegada
        )
    )


    finalizar_viagem_banco(

        id_viagem=id_viagem,

        data_fim=data_chegada,

        duracao_horas=duracao_horas,

        diferenca_horas=diferenca_horas,

        status_prazo=status_prazo

    )


    return (
        status_prazo,
        duracao_horas,
        diferenca_horas
    )


# ============================================================
# FINALIZAR VIAGEM AUTOMATICAMENTE
# ============================================================

def finalizar_viagem(
    placa,
    evento,
    area,
    dataGPS
):
    """
    Processa a chegada automática ao destino.
    """


    # ========================================================
    # VALIDAR EVENTO
    # ========================================================

    if not eh_fim_viagem(
        evento,
        area
    ):

        return False


    # ========================================================
    # BUSCAR VIAGEM
    # ========================================================

    viagem_aberta = (
        buscar_viagem_aberta(
            placa
        )
    )


    if viagem_aberta is None:
        return False


    # Viagem ainda não saiu.
    if (
        viagem_aberta[
            "data_inicio"
        ]
        is None
    ):

        return False


    # ========================================================
    # IDENTIFICAR GARAGEM
    # ========================================================

    dados_garagem = (
        obter_dados_trajeto(
            area
        )
    )


    if dados_garagem is None:
        return False


    garagem_atual = (
        dados_garagem[
            "origem"
        ]
    )


    destino_viagem = (
        viagem_aberta[
            "destino"
        ]
    )


    # ========================================================
    # VALIDAR DESTINO
    # ========================================================

    if (
        garagem_atual
        !=
        destino_viagem
    ):

        return False


    # ========================================================
    # CONCLUIR
    # ========================================================

    resultado = (
        concluir_viagem(

            viagem_aberta,

            dataGPS

        )
    )


    if resultado is None:
        return False


    # ========================================================
    # CRIAR PRÓXIMA VIAGEM
    # ========================================================

    criou_proxima = (
        criar_proxima_viagem(

            placa=placa,

            balsa=viagem_aberta[
                "balsa"
            ],

            dados_trajeto=dados_garagem

        )
    )


    if not criou_proxima:
        return False


    return True


# ============================================================
# CORRIGIR CHEGADA MANUALMENTE
# ============================================================

def corrigir_chegada_manual(
    placa,
    data_chegada,
    motivo
):
    """
    Corrige manualmente uma chegada não detectada
    corretamente pela TotalTrack.

    A alteração fica registrada na auditoria.
    """


    criar_tabela_ajustes()


    viagem_aberta = (
        buscar_viagem_aberta(
            placa
        )
    )


    if viagem_aberta is None:
        return False


    if (
        viagem_aberta[
            "data_inicio"
        ]
        is None
    ):

        return False


    # ========================================================
    # IDENTIFICAR DESTINO
    # ========================================================

    destino = (
        viagem_aberta[
            "destino"
        ]
    )


    (
        area_destino,
        dados_destino

    ) = obter_garagem_por_origem(
        destino
    )


    if dados_destino is None:
        return False


    data_chegada = (
        converter_para_datetime(
            data_chegada
        )
    )


    # ========================================================
    # CONCLUIR
    # ========================================================

    resultado = (
        concluir_viagem(

            viagem_aberta,

            data_chegada

        )
    )


    if resultado is None:
        return False


    # ========================================================
    # AUDITORIA
    # ========================================================

    registrar_ajuste(

        placa=placa,

        codigo_viagem=(
            viagem_aberta[
                "codigo_viagem"
            ]
        ),

        tipo_ajuste=(
            "Chegada manual"
        ),

        valor_anterior=(
            "Em viagem"
        ),

        valor_novo=(
            "Finalizada"
        ),

        motivo=motivo,

        data_ajuste=datetime.now()

    )


    # ========================================================
    # CRIAR PRÓXIMA VIAGEM
    # ========================================================

    criou_proxima = (
        criar_proxima_viagem(

            placa=placa,

            balsa=viagem_aberta[
                "balsa"
            ],

            dados_trajeto=dados_destino

        )
    )


    if not criou_proxima:
        return False


    return True


# ============================================================
# CORRIGIR SAÍDA MANUALMENTE
# ============================================================

def corrigir_saida_manual(
    placa,
    data_saida,
    motivo
):
    """
    Registra manualmente a saída quando a TotalTrack
    não conseguiu identificar corretamente o evento.
    """


    criar_tabela_ajustes()


    viagem_aberta = (
        buscar_viagem_aberta(
            placa
        )
    )


    if viagem_aberta is None:
        return False


    id_viagem = (
        viagem_aberta["id"]
    )


    codigo_viagem = (
        viagem_aberta[
            "codigo_viagem"
        ]
    )


    status_viagem = (
        viagem_aberta[
            "status"
        ]
    )


    # ========================================================
    # VALIDAR STATUS
    # ========================================================

    if (
        status_viagem
        !=
        "Aguardando carregamento"
    ):

        return False


    # ========================================================
    # CONVERTER DATA
    # ========================================================

    data_saida = (
        converter_para_datetime(
            data_saida
        )
    )


    # ========================================================
    # REGISTRAR SAÍDA
    # ========================================================

    iniciar_viagem_banco(

        id_viagem=id_viagem,

        data_inicio=data_saida

    )


    # ========================================================
    # AUDITORIA
    # ========================================================

    registrar_ajuste(

        placa=placa,

        codigo_viagem=codigo_viagem,

        tipo_ajuste=(
            "Saída manual"
        ),

        valor_anterior=(
            "Aguardando carregamento"
        ),

        valor_novo=(
            "Em viagem"
        ),

        motivo=motivo,

        data_ajuste=datetime.now()

    )


    return True