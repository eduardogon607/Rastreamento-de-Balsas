# ============================================================
# TESTE_ETA.PY
#
# Testa os cálculos de ETA sem consultar a API
# e sem alterar o banco de dados.
# ============================================================

from eta import (
    calcular_eta_base,
    calcular_eta_por_ponto,
    calcular_programacao_viagem
)


# ============================================================
# TESTE 1 - ETA BASE DA VIAGEM
# ============================================================

print("\n--- ETA BASE ---")

eta_base = calcular_eta_base(
    data_inicio="2026-08-17 08:00:00",
    origem="BEL",
    destino="MAO"
)

print("Saída:", "2026-08-17 08:00:00")
print("ETA Manaus:", eta_base)


# ============================================================
# TESTE 2 - PROGRAMAÇÃO PONTO A PONTO
# ============================================================

print("\n--- PROGRAMAÇÃO DA SUBIDA ---")

programacao = calcular_programacao_viagem(
    data_inicio="2026-08-17 08:00:00",
    origem="BEL",
    destino="MAO"
)

for ponto in programacao:

    print(
        ponto["ponto"],
        "| Trecho:",
        ponto["media_minutos"],
        "min | Acumulado:",
        ponto["acumulado_minutos"],
        "min",
        "| Previsto:",
        ponto["horario_previsto"]
    )


# ============================================================
# TESTE 3 - RECÁLCULO A PARTIR DE UM PONTO REAL
# ============================================================

print("\n--- ETA RECALCULADO EM SANTARÉM ---")

resultado = calcular_eta_por_ponto(
    data_ponto="2026-08-21 00:00:00",
    ponto_atual="Santarém/PA",
    origem="BEL",
    destino="MAO"
)

if resultado is None:

    print("Não foi possível calcular o ETA.")

else:

    print(
        "Ponto atual:",
        resultado["ponto_atual"]
    )

    print(
        "Próximo ponto:",
        resultado["proximo_ponto"]
    )

    print(
        "ETA próximo ponto:",
        resultado["eta_proximo_ponto"]
    )

    print(
        "ETA destino final:",
        resultado["eta_destino"]
    )

    print(
        "Minutos restantes:",
        resultado["minutos_restantes"]
    )