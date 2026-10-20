# ============================================================
# INICIALIZAR_VIAGENS.PY
#
# Cria a fotografia inicial das viagens atuais em um banco novo.
# NÃO reconstrói viagens antigas nem consulta a API TotalTrack.
# Cadastro: tabela balsas; fotografia: referencias_balsas.
#
# ATENÇÃO: execute somente ao inicializar um banco novo, após
# cadastrar as balsas e migrar suas referências operacionais.
# ============================================================

from banco import (
    criar_tabela_viagens,
    salvar_viagem,
    salvar_viagem_referencia,
    buscar_viagem_aberta,
    buscar_balsas_ativas,
    buscar_referencia_balsa,
)
from viagem import GARAGENS


# ============================================================
# INICIALIZAR VIAGENS
# ============================================================

def inicializar_viagens():
    print("\n========================================")
    print(" INICIALIZAÇÃO DAS VIAGENS")
    print("========================================")

    criar_tabela_viagens()

    total_criadas = 0
    total_ignoradas = 0
    total_erros = 0

    # Somente embarcações ativas participam da inicialização.
    balsas_ativas = buscar_balsas_ativas()

    for placa, dados_balsa in balsas_ativas.items():
        nome_balsa = dados_balsa["nome"]
        prefixo = dados_balsa["prefixo"]

        # A fotografia inicial é independente do cadastro atual.
        referencia = buscar_referencia_balsa(placa)
        if referencia is None:
            print(
                f"[ERRO] {nome_balsa} | {placa} | "
                "sem referência operacional no banco."
            )
            total_erros += 1
            continue

        numero_viagem = referencia["viagem_referencia"]
        status_referencia = referencia["status_referencia"]
        data_inicio = referencia["data_inicio_referencia"]

        if numero_viagem is None or prefixo is None:
            print(
                f"[ERRO] {nome_balsa} | {placa} | "
                "número de referência ou prefixo ausente."
            )
            total_erros += 1
            continue

        try:
            numero_viagem = int(numero_viagem)
        except (TypeError, ValueError):
            print(
                f"[ERRO] {nome_balsa} | {placa} | "
                f"número de referência inválido: {numero_viagem!r}."
            )
            total_erros += 1
            continue

        # Não cria outra viagem se já existe uma aberta.
        viagem_existente = buscar_viagem_aberta(placa)
        if viagem_existente is not None:
            print(
                f"[IGNORADA] {nome_balsa} | "
                f"{viagem_existente['codigo_viagem']} | "
                "já possui viagem aberta."
            )
            total_ignoradas += 1
            continue

        # Ímpar: BEL → MAO. Par: MAO → BEL.
        if numero_viagem % 2 != 0:
            dados_trajeto = GARAGENS["Porto Combitrans - Belém"]
        else:
            dados_trajeto = GARAGENS["Porto Combitrans - Manaus"]

        codigo_viagem = f"{prefixo}-{numero_viagem}"

        if status_referencia == "Em viagem":
            if data_inicio is None:
                print(
                    f"[ERRO] {nome_balsa} | {codigo_viagem} | "
                    "está 'Em viagem', mas não possui "
                    "data_inicio_referencia."
                )
                total_erros += 1
                continue

            salvar_viagem_referencia(
                codigo_viagem=codigo_viagem,
                placa=placa,
                balsa=nome_balsa,
                origem=dados_trajeto["origem"],
                destino=dados_trajeto["destino"],
                trajeto=dados_trajeto["trajeto"],
                carga=dados_trajeto["carga"],
                prazo_horas=dados_trajeto["prazo"],
                data_inicio=data_inicio,
            )
            print(
                f"[CRIADA] {nome_balsa} | {codigo_viagem} | "
                f"{dados_trajeto['trajeto']} | Em viagem | "
                f"Início: {data_inicio}"
            )

        elif status_referencia == "Aguardando carregamento":
            salvar_viagem(
                codigo_viagem=codigo_viagem,
                placa=placa,
                balsa=nome_balsa,
                origem=dados_trajeto["origem"],
                destino=dados_trajeto["destino"],
                trajeto=dados_trajeto["trajeto"],
                carga=dados_trajeto["carga"],
                prazo_horas=dados_trajeto["prazo"],
            )
            print(
                f"[CRIADA] {nome_balsa} | {codigo_viagem} | "
                f"{dados_trajeto['trajeto']} | Aguardando carregamento"
            )

        else:
            print(
                f"[ERRO] {nome_balsa} | {codigo_viagem} | "
                f"status_referencia desconhecido: {status_referencia}"
            )
            total_erros += 1
            continue

        total_criadas += 1

    print("\n========================================")
    print(" RESUMO DA INICIALIZAÇÃO")
    print("========================================")
    print("Balsas ativas cadastradas:", len(balsas_ativas))
    print("Viagens criadas:", total_criadas)
    print("Viagens ignoradas:", total_ignoradas)
    print("Balsas com erro:", total_erros)
    print("\nInicialização finalizada!")


if __name__ == "__main__":
    inicializar_viagens()
