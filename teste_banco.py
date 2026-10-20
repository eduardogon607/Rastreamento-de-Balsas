from banco import (
    contar_registros,
    consultar_eventos_cronologicos,
    consultar_viagens,
    consultar_ajustes
)


# ============================================================
# TESTE DA TABELA AREA_RESTRITA
# ============================================================

total_eventos = contar_registros()

print("\n--- EVENTOS AREA_RESTRITA ---")
print("Total de eventos:", total_eventos)


# ============================================================
# TESTE DOS EVENTOS CRONOLÓGICOS
# ============================================================

eventos = consultar_eventos_cronologicos()

print("\n--- EVENTOS CRONOLÓGICOS ---")
print("Eventos encontrados:", len(eventos))

for evento in eventos[:5]:
    print(evento)


# ============================================================
# TESTE DA TABELA VIAGENS
# ============================================================

viagens = consultar_viagens()

print("\n--- VIAGENS ---")
print("Total de viagens:", len(viagens))

for viagem in viagens:
    print(viagem)


# ============================================================
# TESTE DA TABELA DE AJUSTES
# ============================================================

ajustes = consultar_ajustes()

print("\n--- AJUSTES MANUAIS ---")
print("Total de ajustes:", len(ajustes))

for ajuste in ajustes:
    print(ajuste)
