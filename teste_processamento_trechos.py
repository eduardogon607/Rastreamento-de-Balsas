# ============================================================
# TESTE_PROCESSAMENTO_TRECHOS.PY
#
# Testa o processamento e classificação dos trechos
# sem depender da API TotalTrack.
#
# Cenários:
#
# 1. Trecho normal e viagem válida para aprendizado
# 2. Trecho atípico
# 3. Viagem iniciada antes do corte das novas geofences
# ============================================================

from processamento_trechos import processar_trecho


# ============================================================
# CENÁRIO 1
# TRECHO NORMAL
# ============================================================

print("\n========================================")
print(" TESTE 1 - TRECHO NORMAL")
print("========================================")


viagem_normal = {
    "placa": "TESTE001",
    "balsa": "BALSA TESTE",
    "codigo_viagem": "ZZ-9999",

    "origem": "BEL",
    "destino": "MAO",

    # Depois do corte:
    # 17/08/2026 13:27
    "data_inicio": "2026-08-18 08:00:00"
}


# Farol do Capim → Ponta Negra
#
# Média-base = 02:30
#
# Simularemos exatamente 02:40.
evento_origem_normal = {
    "evento": "Entrada",
    "area": "Farol do Capim/PA",
    "dataGPS": "2026-08-18 13:45:00"
}


evento_destino_normal = {
    "evento": "Entrada",
    "area": "Ponta Negra/PA",
    "dataGPS": "2026-08-18 16:25:00"
}


resultado_normal = processar_trecho(
    viagem=viagem_normal,
    evento_origem=evento_origem_normal,
    evento_destino=evento_destino_normal
)


print(
    resultado_normal
)


# ============================================================
# CENÁRIO 2
# TRECHO ATÍPICO
# ============================================================

print("\n========================================")
print(" TESTE 2 - TRECHO ATÍPICO")
print("========================================")


viagem_atipica = {
    "placa": "TESTE002",
    "balsa": "BALSA TESTE 2",
    "codigo_viagem": "ZZ-10001",

    "origem": "BEL",
    "destino": "MAO",

    "data_inicio": "2026-08-18 08:00:00"
}


# Mesmo trecho:
#
# Farol do Capim → Ponta Negra
#
# Média-base = 02:30
#
# Aqui simulamos:
# 06:00
#
# Desvio:
# +03:30
#
# Portanto deve ser atípico.
evento_origem_atipico = {
    "evento": "Entrada",
    "area": "Farol do Capim/PA",
    "dataGPS": "2026-08-18 13:45:00"
}


evento_destino_atipico = {
    "evento": "Entrada",
    "area": "Ponta Negra/PA",
    "dataGPS": "2026-08-18 19:45:00"
}


resultado_atipico = processar_trecho(
    viagem=viagem_atipica,
    evento_origem=evento_origem_atipico,
    evento_destino=evento_destino_atipico
)


print(
    resultado_atipico
)


# ============================================================
# CENÁRIO 3
# VIAGEM ANTERIOR AO CORTE
# ============================================================

print("\n========================================")
print(" TESTE 3 - VIAGEM ANTERIOR AO CORTE")
print("========================================")


viagem_antiga = {
    "placa": "TESTE003",
    "balsa": "BALSA TESTE 3",
    "codigo_viagem": "ZZ-9997",

    "origem": "BEL",
    "destino": "MAO",

    # Antes de:
    # 17/08/2026 13:27
    "data_inicio": "2026-08-17 08:00:00"
}


# Trecho perfeitamente normal:
# 02:30.
evento_origem_antigo = {
    "evento": "Entrada",
    "area": "Farol do Capim/PA",
    "dataGPS": "2026-08-17 13:45:00"
}


evento_destino_antigo = {
    "evento": "Entrada",
    "area": "Ponta Negra/PA",
    "dataGPS": "2026-08-17 16:15:00"
}


resultado_antigo = processar_trecho(
    viagem=viagem_antiga,
    evento_origem=evento_origem_antigo,
    evento_destino=evento_destino_antigo
)


print(
    resultado_antigo
)


# ============================================================
# RESULTADO ESPERADO
# ============================================================

print("\n========================================")
print(" RESULTADO ESPERADO")
print("========================================")

print(
    "Teste 1:"
)

print(
    "atipico = False"
)

print(
    "usar_no_eta = True"
)


print(
    "\nTeste 2:"
)

print(
    "atipico = True"
)

print(
    "usar_no_eta = False"
)


print(
    "\nTeste 3:"
)

print(
    "atipico = False"
)

print(
    "usar_no_eta = False"
)

print(
    "\nMotivo do Teste 3:"
)

print(
    "A viagem começou antes do corte das novas geofences."
)