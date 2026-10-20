# ============================================================
# TRATAMENTO.PY
#
# Responsável pelo tratamento dos registros recebidos
# da API TotalTrack.
#
# Nesta etapa:
#
# - convertemos os registros para DataFrame;
# - consultamos no banco quais balsas estão ativas;
# - filtramos somente as balsas monitoradas;
# - adicionamos o nome da balsa;
# - convertemos dataGPS;
# - consultamos no banco a data oficial do corte;
# - removemos qualquer evento anterior ao corte oficial;
# - removemos duplicidades;
# - ordenamos cronologicamente.
#
# IMPORTANTE:
#
# O cadastro das balsas e a data de corte não vêm mais
# do arquivo balsas.py.
#
# A fonte oficial passa a ser o banco SQLite.
# ============================================================


import pandas as pd


from banco import (
    buscar_balsas_ativas,
    buscar_data_corte_geofence
)


# ============================================================
# TRATAR DADOS
# ============================================================

def tratar_dados(
    registros
):

    # ========================================================
    # CONVERTER REGISTROS PARA DATAFRAME
    # ========================================================

    df = pd.DataFrame(
        registros
    )


    # ========================================================
    # PROTEÇÃO CONTRA DATAFRAME VAZIO
    # ========================================================

    if df.empty:

        return df


    # ========================================================
    # PROTEÇÃO CONTRA CAMPOS AUSENTES
    # ========================================================

    campos_obrigatorios = {

        "placa",
        "evento",
        "area",
        "dataGPS"
    }


    if not campos_obrigatorios.issubset(
        df.columns
    ):

        print(
            "Erro: registros recebidos não possuem "
            "todos os campos obrigatórios."
        )

        return pd.DataFrame()


    # ========================================================
    # CONSULTAR BALSAS ATIVAS NO BANCO
    # ========================================================

    # A função retorna um dicionário no formato:
    #
    # {
    #     "ANT0012": {
    #         "placa": "ANT0012",
    #         "nome": "SW ANTUÉRPIA",
    #         ...
    #     }
    # }
    #
    # Isso substitui o antigo BALSAS do balsas.py.

    balsas_ativas = buscar_balsas_ativas()


    # ========================================================
    # PROTEÇÃO CONTRA CADASTRO VAZIO
    # ========================================================

    if not balsas_ativas:

        print(
            "Erro: nenhuma balsa ativa foi encontrada "
            "no banco de dados."
        )

        return pd.DataFrame()


    # ========================================================
    # FILTRAR SOMENTE BALSAS MONITORADAS
    # ========================================================

    df = df[
        df["placa"].isin(
            balsas_ativas.keys()
        )
    ].copy()


    # ========================================================
    # PROTEÇÃO APÓS FILTRO
    # ========================================================

    if df.empty:

        return df


    # ========================================================
    # ADICIONAR NOME DA BALSA
    # ========================================================

    # Agora o nome vem da tabela balsas no SQLite.

    df["balsa"] = (
        df["placa"].map(
            lambda placa:
                balsas_ativas[
                    placa
                ]["nome"]
        )
    )


    # ========================================================
    # CONVERTER DATA GPS
    # ========================================================

    # A TotalTrack envia a data no formato:
    #
    # 14/08/2026 10:31:06
    #
    # Convertemos para datetime para permitir filtros,
    # ordenações e comparações.

    df["dataGPS"] = pd.to_datetime(
        df["dataGPS"],
        format="%d/%m/%Y %H:%M:%S",
        errors="coerce"
    )


    # ========================================================
    # REMOVER DATAS INVÁLIDAS
    # ========================================================

    df = df[
        df["dataGPS"].notna()
    ].copy()


    if df.empty:

        return df


    # ========================================================
    # BUSCAR DATA DE CORTE DAS NOVAS GEOFENCES
    # ========================================================

    # A data de corte agora também vem do banco.
    #
    # Atualmente o banco deve retornar:
    #
    # 2026-08-17 13:27:00

    data_corte_banco = (
        buscar_data_corte_geofence()
    )


    # ========================================================
    # PROTEÇÃO CONTRA AUSÊNCIA DE DATA DE CORTE
    # ========================================================

    if data_corte_banco is None:

        print(
            "Erro: nenhuma data de corte das geofences "
            "foi encontrada no banco."
        )

        return pd.DataFrame()


    # ========================================================
    # CONVERTER DATA DE CORTE
    # ========================================================

    data_corte = pd.to_datetime(
        data_corte_banco,
        format="%Y-%m-%d %H:%M:%S",
        errors="coerce"
    )


    # ========================================================
    # PROTEÇÃO CONTRA DATA DE CORTE INVÁLIDA
    # ========================================================

    if pd.isna(
        data_corte
    ):

        print(
            "Erro: a data de corte das geofences "
            "registrada no banco é inválida."
        )

        return pd.DataFrame()


    # ========================================================
    # FILTRAR EVENTOS ANTERIORES AO CORTE
    # ========================================================

    df = df[
        df["dataGPS"]
        >= data_corte
    ].copy()


    # ========================================================
    # PROTEÇÃO APÓS O CORTE
    # ========================================================

    if df.empty:

        return df


    # ========================================================
    # REMOVER DUPLICIDADES
    # ========================================================

    # Consideramos duplicado:
    #
    # - mesma placa;
    # - mesmo evento;
    # - mesma área;
    # - mesmo instante.

    df = df.drop_duplicates(
        subset=[
            "placa",
            "evento",
            "area",
            "dataGPS"
        ]
    )


    # ========================================================
    # ORDENAR CRONOLOGICAMENTE
    # ========================================================

    df = df.sort_values(
        by="dataGPS"
    )


    # ========================================================
    # REORGANIZAR ÍNDICE
    # ========================================================

    df = df.reset_index(
        drop=True
    )


    # ========================================================
    # RETORNAR DADOS TRATADOS
    # ========================================================

    return df