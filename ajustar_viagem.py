from datetime import datetime

from viagem import corrigir_saida_manual


resultado = corrigir_saida_manual(
    placa="VAL0009",

    data_saida=datetime.strptime(
        "2026-08-15 08:30:00",
        "%Y-%m-%d %H:%M:%S"
    ),

    motivo=(
        "Saída do Porto Combitrans - Belém confirmada "
        "pela operação. O evento não foi registrado "
        "pela área restrita da TotalTrack."
    )
)


if resultado:
    print("Saída manual registrada com sucesso!")

else:
    print("Não foi possível registrar a saída manual.")