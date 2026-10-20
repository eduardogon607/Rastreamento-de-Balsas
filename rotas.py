# ============================================================
# ROTAS.PY
#
# Contém as médias-base dos trechos das viagens.
#
# Essas médias serão utilizadas inicialmente para calcular:
#
# - ETA do próximo ponto;
# - ETA do destino final;
# - tempo previsto acumulado;
# - desvio entre previsto e realizado.
#
# FUTURAMENTE:
#
# As médias-base poderão ser substituídas automaticamente
# pela média das últimas 3 viagens válidas e não atípicas.
# ============================================================


# ============================================================
# FUNÇÃO AUXILIAR
# ============================================================

def tempo_para_minutos(tempo):
    """
    Converte um texto HH:MM para minutos.

    Exemplo:
    "05:45" -> 345 minutos
    """

    horas, minutos = tempo.split(":")

    return (
        int(horas) * 60
        + int(minutos)
    )


# ============================================================
# SUBIDA
# BELÉM → MANAUS
# ============================================================

ROTA_SUBIDA = [

    {
        "ponto": "Porto Combitrans - Belém",
        "tempo_trecho": "00:00"
    },

    {
        "ponto": "Farol do Capim/PA",
        "tempo_trecho": "05:45"
    },

    {
        "ponto": "Ponta Negra/PA",
        "tempo_trecho": "02:30"
    },

    {
        "ponto": "São Francisco do Jararaca/PA",
        "tempo_trecho": "01:15"
    },

    {
        "ponto": "Curralinho/PA",
        "tempo_trecho": "03:00"
    },

    {
        "ponto": "Farol do Buiuçu/PA",
        "tempo_trecho": "04:45"
    },

    {
        "ponto": "Breves/PA",
        "tempo_trecho": "03:15"
    },

    {
        "ponto": "Antônio Lemos/PA",
        "tempo_trecho": "05:13"
    },

    {
        "ponto": "Furo do Ituquara/PA",
        "tempo_trecho": "08:00"
    },

    {
        "ponto": "Gurupá/PA",
        "tempo_trecho": "06:30"
    },

    {
        "ponto": "Almeirin/PA",
        "tempo_trecho": "13:15"
    },

    {
        "ponto": "Prainha/PA",
        "tempo_trecho": "12:25"
    },

    {
        "ponto": "Monte Alegre/PA",
        "tempo_trecho": "07:50"
    },

    {
        "ponto": "Santarém/PA",
        "tempo_trecho": "12:00"
    },

    {
        "ponto": "Farol do Patacho/PA",
        "tempo_trecho": "07:46"
    },

    {
        "ponto": "Óbidos/PA",
        "tempo_trecho": "06:32"
    },

    {
        "ponto": "Juruti/PA",
        "tempo_trecho": "08:13"
    },

    {
        "ponto": "Serra Santa Júlia/AM",
        "tempo_trecho": "05:30"
    },

    {
        "ponto": "Parintins/AM",
        "tempo_trecho": "04:30"
    },

    {
        "ponto": "Paraná do Mocambo/AM",
        "tempo_trecho": "04:00"
    },

    {
        "ponto": "Paraná do Albano/AM",
        "tempo_trecho": "06:25"
    },

    {
        "ponto": "Urucurituba/AM",
        "tempo_trecho": "07:15"
    },

    {
        "ponto": "Paraná do Serpa/AM",
        "tempo_trecho": "06:00"
    },

    {
        "ponto": "Itacoatiara/AM",
        "tempo_trecho": "04:45"
    },

    {
        "ponto": "Ponta do Passarinho/AM",
        "tempo_trecho": "09:21"
    },

    {
        "ponto": "Ilha das Onças/AM",
        "tempo_trecho": "05:58"
    },

    {
        "ponto": "Porto Combitrans - Manaus",
        "tempo_trecho": "06:02"
    }
]


# ============================================================
# BAIXADA
# MANAUS → BELÉM
# ============================================================

ROTA_BAIXADA = [

    {
        "ponto": "Porto Combitrans - Manaus",
        "tempo_trecho": "00:00"
    },

    {
        "ponto": "Ilha das Onças/AM",
        "tempo_trecho": "04:15"
    },

    {
        "ponto": "Ponta do Passarinho/AM",
        "tempo_trecho": "03:08"
    },

    {
        "ponto": "Itacoatiara/AM",
        "tempo_trecho": "03:51"
    },

    {
        "ponto": "Paraná do Serpa/AM",
        "tempo_trecho": "02:01"
    },

    {
        "ponto": "Urucurituba/AM",
        "tempo_trecho": "02:26"
    },

    {
        "ponto": "Paraná do Albano/AM",
        "tempo_trecho": "03:45"
    },

    {
        "ponto": "Paraná do Mocambo/AM",
        "tempo_trecho": "03:29"
    },

    {
        "ponto": "Parintins/AM",
        "tempo_trecho": "02:05"
    },

    {
        "ponto": "Serra Santa Júlia/AM",
        "tempo_trecho": "02:10"
    },

    {
        "ponto": "Juruti/PA",
        "tempo_trecho": "03:07"
    },

    {
        "ponto": "Óbidos/PA",
        "tempo_trecho": "03:29"
    },

    {
        "ponto": "Farol do Patacho/PA",
        "tempo_trecho": "02:53"
    },

    {
        "ponto": "Santarém/PA",
        "tempo_trecho": "03:35"
    },

    {
        "ponto": "Monte Alegre/PA",
        "tempo_trecho": "09:39"
    },

    {
        "ponto": "Prainha/PA",
        "tempo_trecho": "03:17"
    },

    {
        "ponto": "Almeirin/PA",
        "tempo_trecho": "06:07"
    },

    {
        "ponto": "Gurupá/PA",
        "tempo_trecho": "06:09"
    },

    {
        "ponto": "Furo do Ituquara/PA",
        "tempo_trecho": "02:59"
    },

    {
        "ponto": "Antônio Lemos/PA",
        "tempo_trecho": "04:29"
    },

    {
        "ponto": "Breves/PA",
        "tempo_trecho": "03:08"
    },

    {
        "ponto": "Farol do Buiuçu/PA",
        "tempo_trecho": "02:37"
    },

    {
        "ponto": "Curralinho/PA",
        "tempo_trecho": "03:56"
    },

    {
        "ponto": "São Francisco do Jararaca/PA",
        "tempo_trecho": "04:02"
    },

    {
        "ponto": "Ponta Negra/PA",
        "tempo_trecho": "01:15"
    },

    {
        "ponto": "Farol do Capim/PA",
        "tempo_trecho": "03:01"
    },

    {
        "ponto": "Porto Combitrans - Belém",
        "tempo_trecho": "04:56"
    }
]


# ============================================================
# PRAZOS OFICIAIS
# ============================================================

PRAZOS_OFICIAIS = {
    "SUBIDA": 168,
    "BAIXADA": 96
}


# ============================================================
# OBTER ROTA PELO SENTIDO
# ============================================================

def obter_rota(origem, destino):

    if origem == "BEL" and destino == "MAO":
        return ROTA_SUBIDA

    if origem == "MAO" and destino == "BEL":
        return ROTA_BAIXADA

    return None


# ============================================================
# CALCULAR TEMPO TOTAL DA ROTA
# ============================================================

def calcular_total_rota(rota):

    total_minutos = 0

    for trecho in rota:

        total_minutos += tempo_para_minutos(
            trecho["tempo_trecho"]
        )

    return total_minutos