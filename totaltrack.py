# ============================================================
# TOTALTRACK.PY — coleta com tentativas limitadas
#
# [] significa uma consulta bem-sucedida sem eventos.
# ErroTotalTrack significa falha: o main encerra antes de salvar.
# Uma coleta parcial nunca é devolvida como se estivesse completa.
# ============================================================
import os
import time
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv
from banco import buscar_ultima_data_evento, buscar_data_corte_geofence

PASTA_PROJETO = Path(__file__).resolve().parent
load_dotenv(PASTA_PROJETO / ".env")
ARQUIVO_TOKEN = str(PASTA_PROJETO / "token_totaltrack.txt")
URL_LOGIN = "https://totaltracmanager.com.br/api_integratorsv2/login"
URL_AREA = "https://totaltracmanager.com.br/api_integratorsv2/AdmList/AreaRestrita"

# Limites de conexão e de espera pela resposta, em segundos.
TIMEOUT = (10, 60)
MAX_TENTATIVAS = 3
ESPERA_REDE = 5
ESPERA_LIMITE = 60
INTERVALO_PAGINAS = 2
MAX_PAGINAS = 1000


class ErroTotalTrack(RuntimeError):
    """Falha de autenticação, comunicação ou resposta inválida da API."""


def carregar_token():
    try:
        return Path(ARQUIVO_TOKEN).read_text(encoding="utf-8").strip() or None
    except FileNotFoundError:
        return None
    except OSError as erro:
        raise ErroTotalTrack("Não foi possível ler o arquivo do token.") from erro


def salvar_token(token):
    try:
        Path(ARQUIVO_TOKEN).write_text(token, encoding="utf-8")
    except OSError as erro:
        raise ErroTotalTrack("Não foi possível salvar o arquivo do token.") from erro


def requisitar(url, dados, contexto, headers=None):
    """Repete apenas falhas temporárias, sempre com limite de tentativas."""
    for tentativa in range(1, MAX_TENTATIVAS + 1):
        try:
            resposta = requests.post(
                url, json=dados, headers=headers, timeout=TIMEOUT
            )
        except requests.RequestException as erro:
            if tentativa == MAX_TENTATIVAS:
                raise ErroTotalTrack(
                    f"{contexto}: falha de conexão após {MAX_TENTATIVAS} tentativas."
                ) from erro
            print(f"{contexto}: falha de conexão; tentativa {tentativa}/{MAX_TENTATIVAS}.")
            time.sleep(ESPERA_REDE)
            continue

        if resposta.status_code == 429 or 500 <= resposta.status_code < 600:
            if tentativa == MAX_TENTATIVAS:
                raise ErroTotalTrack(
                    f"{contexto}: HTTP {resposta.status_code} após "
                    f"{MAX_TENTATIVAS} tentativas."
                )
            espera = ESPERA_LIMITE if resposta.status_code == 429 else ESPERA_REDE
            print(f"{contexto}: HTTP {resposta.status_code}; aguardando {espera} segundos.")
            time.sleep(espera)
            continue

        return resposta

    raise ErroTotalTrack(f"{contexto}: nenhuma resposta obtida.")


def ler_json(resposta, contexto):
    try:
        dados = resposta.json()
    except ValueError as erro:
        raise ErroTotalTrack(f"{contexto}: resposta não contém JSON válido.") from erro
    if not isinstance(dados, dict):
        raise ErroTotalTrack(f"{contexto}: formato de resposta inesperado.")
    return dados


def realizar_login():
    dados_login = {
        "cpfcnpj": os.getenv("TOTALTRACK_CPFCNPJ"),
        "senha": os.getenv("TOTALTRACK_SENHA"),
    }
    if any(not valor or not valor.strip() for valor in dados_login.values()):
        raise ErroTotalTrack("Preencha TOTALTRACK_CPFCNPJ e TOTALTRACK_SENHA no .env.")

    print("Realizando login na TotalTrack...")
    resposta = requisitar(URL_LOGIN, dados_login, "Login")
    if resposta.status_code not in (200, 201):
        raise ErroTotalTrack(f"Login recusado: HTTP {resposta.status_code}.")

    token = ler_json(resposta, "Login").get("access_token")
    if not isinstance(token, str) or not token.strip():
        raise ErroTotalTrack("Login: access_token não foi retornado corretamente.")
    token = token.strip()
    salvar_token(token)
    print("Login realizado com sucesso!")
    return token


def obter_token():
    token = carregar_token()
    if token:
        print("Token salvo encontrado. Tentando reutilizar...")
        return token
    return realizar_login()


def definir_data_inicial():

    # ========================================================
    # BUSCAR CORTE OFICIAL DAS NOVAS GEOFENCES
    # ========================================================

    # Antes:
    #
    # DATA_CORTE_GEOFENCE vinha do arquivo balsas.py.
    #
    # Agora:
    #
    # a data é consultada na tabela referencias_balsas
    # através do banco.py.

    data_corte_banco = (
        buscar_data_corte_geofence()
    )


    # ========================================================
    # PROTEÇÃO CONTRA AUSÊNCIA DO CORTE
    # ========================================================

    # Diferentemente do tratamento.py, aqui não podemos
    # simplesmente continuar sem essa informação.
    #
    # Essa data protege a consulta contra a leitura de
    # eventos das geofences antigas.
    #
    # Portanto, se ela não existir, interrompemos a execução.

    if data_corte_banco is None:

        raise RuntimeError(
            "Não foi encontrada no banco a data oficial "
            "de corte das novas geofences."
        )


    # ========================================================
    # CONVERTER DATA DO CORTE
    # ========================================================

    try:

        data_corte = datetime.strptime(
            data_corte_banco,
            "%Y-%m-%d %H:%M:%S"
        )

    except ValueError as erro:

        raise RuntimeError(
            "A data de corte das geofences registrada "
            "no banco possui formato inválido."
        ) from erro


    # ========================================================
    # ÚLTIMO EVENTO EXISTENTE NO BANCO
    # ========================================================

    ultima_data_banco = (
        buscar_ultima_data_evento()
    )


    # ========================================================
    # PRIMEIRA EXECUÇÃO
    # ========================================================

    # Se ainda não houver eventos armazenados,
    # começamos exatamente no corte oficial.

    if ultima_data_banco is None:

        return data_corte


    # ========================================================
    # EXECUÇÕES SEGUINTES
    # ========================================================

    ultima_data_dt = datetime.strptime(
        ultima_data_banco,
        "%Y-%m-%d %H:%M:%S"
    )


    # Mesmo se existir algum registro antigo
    # por engano no banco, nunca consultamos
    # antes do corte oficial.
    return max(
        ultima_data_dt,
        data_corte
    )


def buscar_dados():
    # Mantém a regra incremental e o corte oficial já existentes.
    try:
        data_inicial_dt = definir_data_inicial()
    except (RuntimeError, ValueError) as erro:
        raise ErroTotalTrack(f"Não foi possível definir o período: {erro}") from erro
    data_atual = datetime.now()
    if data_inicial_dt > data_atual:
        raise ErroTotalTrack("A data inicial está no futuro. Confira o banco e o relógio do computador.")

    data_inicial = data_inicial_dt.strftime("%Y-%m-%d %H:%M:%S")
    data_final = data_atual.strftime("%Y-%m-%d %H:%M:%S")
    token = obter_token()
    headers = {"Authorization": f"Bearer {token}"}
    renovou_token = False
    limit = 500
    todos_registros = []

    print("\n--- Período da consulta ---")
    print("Data inicial:", data_inicial)
    print("Data final:", data_final)

    for page in range(1, MAX_PAGINAS + 1):
        filtro = {
            "dataInicial": data_inicial, "dataFinal": data_final,
            "page": page, "limit": limit,
        }
        contexto = f"Página {page}"
        resposta = requisitar(URL_AREA, filtro, contexto, headers)

        # Só permitimos uma renovação por coleta: evita login em ciclo infinito.
        if resposta.status_code in (401, 403):
            if renovou_token:
                raise ErroTotalTrack(f"{contexto}: acesso recusado mesmo após renovar o token.")
            print("Token inválido ou expirado. Solicitando novo token...")
            token = realizar_login()
            headers = {"Authorization": f"Bearer {token}"}
            renovou_token = True
            resposta = requisitar(URL_AREA, filtro, contexto, headers)

        if resposta.status_code not in (200, 201):
            raise ErroTotalTrack(f"{contexto}: HTTP {resposta.status_code}. Coleta interrompida.")

        dados = ler_json(resposta, contexto)
        pagina = dados.get("data")
        if not isinstance(pagina, list):
            raise ErroTotalTrack(f"{contexto}: campo data ausente ou diferente de uma lista.")
        if any(not isinstance(registro, dict) for registro in pagina):
            raise ErroTotalTrack(f"{contexto}: a lista contém registros inválidos.")
        campos = {"placa", "evento", "area", "dataGPS"}
        if any(not campos.issubset(registro) for registro in pagina):
            raise ErroTotalTrack(f"{contexto}: registro sem os campos obrigatórios.")
        if len(pagina) > limit:
            raise ErroTotalTrack(f"{contexto}: quantidade acima do limite solicitado.")

        todos_registros.extend(pagina)
        print(f"{contexto}: {len(pagina)} registros")
        if len(pagina) < limit:
            print("\nColeta concluída. Páginas:", page)
            print("Total de registros:", len(todos_registros))
            return todos_registros
        if page < MAX_PAGINAS:
            time.sleep(INTERVALO_PAGINAS)

    raise ErroTotalTrack("Limite de páginas atingido. Coleta interrompida sem salvar dados parciais.")
