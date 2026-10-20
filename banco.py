# ============================================================



# BANCO.PY



#



# Responsável por toda comunicação com o banco SQLite.



#



# Este arquivo cuida de:



#



# - conexão com o banco;



# - armazenamento dos eventos da TotalTrack;



# - cadastro das balsas;



# - criação e atualização das viagens;



# - ajustes manuais;



# - histórico dos trechos;



# - dados utilizados pelo cálculo de ETA.



#



# REGRA IMPORTANTE:



#



# Outros arquivos do projeto não devem executar SQL diretamente.



# Eles devem chamar funções deste arquivo.



#



# Exemplo:



#



# viagem.py



#     ↓



# buscar_viagem_aberta()



#     ↓



# banco.py



#     ↓



# SQLite



#



# ============================================================







import sqlite3



from datetime import datetime

# Segurança de senhas: gera e valida hashes usando Argon2id.
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError











# ============================================================



# CONFIGURAÇÃO DO BANCO



# ============================================================







NOME_BANCO = "dados_totaltrack.db"











# ============================================================



# CONEXÃO COM O BANCO



# ============================================================







def conectar_banco():
    """
    Abre uma conexão com o banco SQLite utilizado pelo DashPy.

    Configurações aplicadas:

    1. row_factory = sqlite3.Row
       Permite acessar os resultados pelo nome da coluna.

       Exemplo:

           viagem["placa"]

       em vez de:

           viagem[2]

    2. PRAGMA foreign_keys = ON
       Ativa a validação das chaves estrangeiras (FOREIGN KEY)
       para esta conexão.

       Isso impede, por exemplo, que seja criado um vínculo
       entre um usuário e um grupo que não existe.
    """

    # --------------------------------------------------------
    # ABRIR CONEXÃO
    # --------------------------------------------------------

    conexao = sqlite3.connect(NOME_BANCO)

    # Permite acessar os campos retornados pelo nome da coluna.
    conexao.row_factory = sqlite3.Row

    # --------------------------------------------------------
    # ATIVAR CHAVES ESTRANGEIRAS
    # --------------------------------------------------------
    #
    # No SQLite, as FOREIGN KEY precisam ser habilitadas
    # para cada nova conexão.
    #
    # Como todas as conexões do DashPy devem passar por esta
    # função, ativamos a proteção em um único lugar.
    # --------------------------------------------------------

    conexao.execute("PRAGMA foreign_keys = ON")

    return conexao


# ============================================================







def formatar_data_banco(data):



    """



    Padroniza datas antes de salvar no SQLite.







    Aceita:







        datetime







    ou:







        "2026-09-14 10:30:00"







    Retorna sempre:







        YYYY-MM-DD HH:MM:SS







    Se receber None, retorna None.



    """







    if data is None:



        return None







    if isinstance(data, datetime):







        return data.strftime(



            "%Y-%m-%d %H:%M:%S"



        )







    if isinstance(data, str):







        # Tentamos validar se já está no nosso formato padrão.



        try:







            data_convertida = datetime.strptime(



                data,



                "%Y-%m-%d %H:%M:%S"



            )







            return data_convertida.strftime(



                "%Y-%m-%d %H:%M:%S"



            )







        except ValueError:







            # Caso outro módulo já tenha preparado a data,



            # preservamos o texto recebido.



            return data







    raise TypeError(



        "A data deve ser datetime, string ou None."



    )











# ============================================================



# VERIFICAR SE UMA TABELA EXISTE



# ============================================================







def tabela_existe(nome_tabela):



    """



    Verifica se determinada tabela já existe no SQLite.







    Retorna:



        True



        False



    """







    conexao = conectar_banco()



    cursor = conexao.cursor()







    cursor.execute("""



        SELECT name



        FROM sqlite_master



        WHERE type = 'table'



        AND name = ?



    """, (



        nome_tabela,



    ))







    resultado = cursor.fetchone()







    conexao.close()







    return resultado is not None











# ============================================================



# EVENTOS DA TOTALTRACK



# ============================================================







def criar_tabela_area_restrita():



    """



    Cria a tabela responsável por armazenar os eventos



    recebidos da API TotalTrack.







    Um mesmo evento não pode ser salvo duas vezes.



    """







    conexao = conectar_banco()



    cursor = conexao.cursor()







    cursor.execute("""



        CREATE TABLE IF NOT EXISTS area_restrita (







            id INTEGER PRIMARY KEY AUTOINCREMENT,







            placa TEXT,







            balsa TEXT,







            evento TEXT,







            area TEXT,







            dataGPS TEXT,







            UNIQUE(



                placa,



                evento,



                area,



                dataGPS



            )



        )



    """)







    conexao.commit()



    conexao.close()











# ============================================================



# SALVAR EVENTOS DA API



# ============================================================







def salvar_dados(df):



    """



    Salva no banco os eventos tratados pelo tratamento.py.







    INSERT OR IGNORE impede que eventos repetidos da API



    sejam inseridos novamente.



    """







    criar_tabela_area_restrita()







    conexao = conectar_banco()



    cursor = conexao.cursor()







    for _, linha in df.iterrows():







        cursor.execute("""



            INSERT OR IGNORE INTO area_restrita (







                placa,



                balsa,



                evento,



                area,



                dataGPS







            )







            VALUES (?, ?, ?, ?, ?)







        """, (







            linha["placa"],



            linha["balsa"],



            linha["evento"],



            linha["area"],



            formatar_data_banco(



                linha["dataGPS"]



            )







        ))







    conexao.commit()



    conexao.close()











# ============================================================



# CONSULTAR EVENTOS



# ============================================================







def consultar_dados():



    """



    Retorna todos os eventos armazenados no banco,



    começando pelo mais recente.



    """







    criar_tabela_area_restrita()







    conexao = conectar_banco()



    cursor = conexao.cursor()







    cursor.execute("""



        SELECT *



        FROM area_restrita







        ORDER BY dataGPS DESC



    """)







    registros = cursor.fetchall()







    conexao.close()







    return [



        dict(registro)



        for registro in registros



    ]











# ============================================================



# CONSULTAR EVENTOS CRONOLOGICAMENTE



# ============================================================







def consultar_eventos_cronologicos():



    """



    Retorna os eventos da TotalTrack em ordem cronológica.







    Essa função é importante para reconstruir viagens.



    """







    criar_tabela_area_restrita()







    conexao = conectar_banco()



    cursor = conexao.cursor()







    cursor.execute("""



        SELECT *



        FROM area_restrita







        ORDER BY dataGPS ASC



    """)







    registros = cursor.fetchall()







    conexao.close()







    return [



        dict(registro)



        for registro in registros



    ]











# ============================================================



# CONTAR EVENTOS



# ============================================================







def contar_registros():



    """



    Conta quantos eventos existem na tabela area_restrita.



    """







    criar_tabela_area_restrita()







    conexao = conectar_banco()



    cursor = conexao.cursor()







    cursor.execute("""



        SELECT COUNT(*) AS total



        FROM area_restrita



    """)







    resultado = cursor.fetchone()







    conexao.close()







    return resultado["total"]











# ============================================================



# BUSCAR DATA DO ÚLTIMO EVENTO



# ============================================================







def buscar_ultima_data_evento():



    """



    Descobre qual foi o evento mais recente salvo.







    Essa informação pode ser utilizada para evitar



    consultar novamente períodos muito antigos da API.



    """







    if not tabela_existe("area_restrita"):



        return None







    conexao = conectar_banco()



    cursor = conexao.cursor()







    cursor.execute("""



        SELECT MAX(dataGPS) AS ultima_data



        FROM area_restrita



    """)







    resultado = cursor.fetchone()







    conexao.close()







    if resultado is None:



        return None







    return resultado["ultima_data"]











# ============================================================



# CADASTRO DAS BALSAS



# ============================================================







def criar_tabela_balsas():



    """



    Cria o cadastro central das balsas.







    Esta tabela futuramente substituirá o dicionário BALSAS



    existente em balsas.py.







    placa:



        identificação do rastreador.







    nome:



        nome da embarcação.







    prefixo:



        prefixo usado no código das viagens.







    ultima_viagem_referencia:



        número utilizado como referência quando ainda não



        existem viagens cadastradas no banco.







    ativa:



        1 = ativa



        0 = inativa



    """







    conexao = conectar_banco()



    cursor = conexao.cursor()







    cursor.execute("""



        CREATE TABLE IF NOT EXISTS balsas (







            id INTEGER PRIMARY KEY AUTOINCREMENT,







            placa TEXT NOT NULL UNIQUE,







            nome TEXT NOT NULL,







            prefixo TEXT NOT NULL,







            ultima_viagem_referencia INTEGER,







            ativa INTEGER DEFAULT 1,







            data_cadastro TEXT



        )



    """)







    conexao.commit()



    conexao.close()











# ============================================================



# SALVAR OU ATUALIZAR BALSA



# ============================================================







def salvar_balsa(



    placa,



    nome,



    prefixo,



    ultima_viagem_referencia=None,



    ativa=True



):



    """



    Insere uma nova balsa ou atualiza uma balsa já cadastrada.







    A placa é utilizada como identificador único.







    Isso permitirá futuramente adicionar novas balsas sem



    precisar editar o código Python.



    """







    criar_tabela_balsas()







    conexao = conectar_banco()



    cursor = conexao.cursor()







    cursor.execute("""



        INSERT INTO balsas (







            placa,



            nome,



            prefixo,



            ultima_viagem_referencia,



            ativa,



            data_cadastro







        )







        VALUES (?, ?, ?, ?, ?, ?)







        ON CONFLICT(placa)







        DO UPDATE SET







            nome = excluded.nome,



            prefixo = excluded.prefixo,



            ultima_viagem_referencia =



                excluded.ultima_viagem_referencia,



            ativa = excluded.ativa







    """, (







        placa,



        nome,



        prefixo,



        ultima_viagem_referencia,



        1 if ativa else 0,



        datetime.now().strftime(



            "%Y-%m-%d %H:%M:%S"



        )







    ))







    conexao.commit()



    conexao.close()











# ============================================================



# BUSCAR BALSA



# ============================================================







def buscar_balsa(placa):



    """



    Busca uma balsa pela placa do rastreador.







    Retorna dicionário ou None.



    """







    criar_tabela_balsas()







    conexao = conectar_banco()



    cursor = conexao.cursor()







    cursor.execute("""



        SELECT *



        FROM balsas







        WHERE placa = ?







        LIMIT 1



    """, (



        placa,



    ))







    resultado = cursor.fetchone()







    conexao.close()







    if resultado is not None:



        return dict(resultado)







    return None











# ============================================================



# CONSULTAR BALSAS



# ============================================================







def consultar_balsas(



    somente_ativas=False



):



    """



    Retorna o cadastro das balsas.







    somente_ativas=True



        retorna apenas balsas ativas.



    """







    criar_tabela_balsas()







    conexao = conectar_banco()



    cursor = conexao.cursor()







    if somente_ativas:







        cursor.execute("""



            SELECT *



            FROM balsas







            WHERE ativa = 1







            ORDER BY nome ASC



        """)







    else:







        cursor.execute("""



            SELECT *



            FROM balsas







            ORDER BY nome ASC



        """)







    registros = cursor.fetchall()







    conexao.close()







    return [



        dict(registro)



        for registro in registros



    ]











# ============================================================



# ALTERAR STATUS DA BALSA



# ============================================================







def atualizar_status_balsa(



    placa,



    ativa



):



    """



    Ativa ou desativa uma balsa sem apagar seu histórico.







    Isso será útil quando uma embarcação deixar temporariamente



    de operar ou for retirada do monitoramento.



    """







    criar_tabela_balsas()







    conexao = conectar_banco()



    cursor = conexao.cursor()







    cursor.execute("""



        UPDATE balsas







        SET ativa = ?







        WHERE placa = ?



    """, (







        1 if ativa else 0,



        placa







    ))







    conexao.commit()



    conexao.close()











# ============================================================



# TABELA DE VIAGENS



# ============================================================







def criar_tabela_viagens():



    """



    Cria a tabela principal das viagens.



    """







    conexao = conectar_banco()



    cursor = conexao.cursor()







    cursor.execute("""



        CREATE TABLE IF NOT EXISTS viagens (







            id INTEGER PRIMARY KEY AUTOINCREMENT,







            codigo_viagem TEXT UNIQUE,







            placa TEXT,







            balsa TEXT,







            origem TEXT,







            destino TEXT,







            trajeto TEXT,







            carga TEXT,







            prazo_horas INTEGER,







            data_inicio TEXT,







            data_fim TEXT,







            status TEXT,







            duracao_horas REAL,







            diferenca_horas REAL,







            status_prazo TEXT,







            email_atraso_enviado INTEGER DEFAULT 0



        )



    """)







    conexao.commit()



    conexao.close()











# ============================================================



# BUSCAR ÚLTIMA VIAGEM



# ============================================================







def buscar_ultima_viagem(placa):



    """



    Retorna o código da viagem mais recente da balsa.







    É utilizado principalmente para descobrir qual deve



    ser o próximo número de viagem.



    """







    criar_tabela_viagens()







    conexao = conectar_banco()



    cursor = conexao.cursor()







    cursor.execute("""



        SELECT codigo_viagem







        FROM viagens







        WHERE placa = ?







        ORDER BY id DESC







        LIMIT 1



    """, (



        placa,



    ))







    resultado = cursor.fetchone()







    conexao.close()







    if resultado is not None:



        return dict(resultado)







    return None











# ============================================================



# SALVAR NOVA VIAGEM



# ============================================================







def salvar_viagem(



    codigo_viagem,



    placa,



    balsa,



    origem,



    destino,



    trajeto,



    carga,



    prazo_horas



):



    """



    Cria uma nova viagem.







    Toda nova viagem criada automaticamente começa com:







        status = Aguardando carregamento







    data_inicio e data_fim ficam vazias.



    """







    criar_tabela_viagens()







    conexao = conectar_banco()



    cursor = conexao.cursor()







    cursor.execute("""



        INSERT INTO viagens (







            codigo_viagem,



            placa,



            balsa,



            origem,



            destino,



            trajeto,



            carga,



            prazo_horas,



            data_inicio,



            data_fim,



            status







        )







        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)







    """, (







        codigo_viagem,



        placa,



        balsa,



        origem,



        destino,



        trajeto,



        carga,



        prazo_horas,



        None,



        None,



        "Aguardando carregamento"







    ))







    conexao.commit()



    conexao.close()











# ============================================================



# SALVAR VIAGEM DE REFERÊNCIA



# ============================================================







def salvar_viagem_referencia(



    codigo_viagem,



    placa,



    balsa,



    origem,



    destino,



    trajeto,



    carga,



    prazo_horas,



    data_inicio



):



    """



    Cria uma viagem já em andamento.







    Essa função é utilizada quando começamos a monitorar



    uma balsa que já estava navegando antes da implantação



    do sistema.



    """







    criar_tabela_viagens()







    conexao = conectar_banco()



    cursor = conexao.cursor()







    cursor.execute("""



        INSERT INTO viagens (







            codigo_viagem,



            placa,



            balsa,



            origem,



            destino,



            trajeto,



            carga,



            prazo_horas,



            data_inicio,



            data_fim,



            status







        )







        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)







    """, (







        codigo_viagem,



        placa,



        balsa,



        origem,



        destino,



        trajeto,



        carga,



        prazo_horas,



        formatar_data_banco(data_inicio),



        None,



        "Em viagem"







    ))







    conexao.commit()



    conexao.close()











# ============================================================



# CONSULTAR TODAS AS VIAGENS



# ============================================================







def consultar_viagens():



    """



    Retorna todas as viagens cadastradas.



    """







    criar_tabela_viagens()







    conexao = conectar_banco()



    cursor = conexao.cursor()







    cursor.execute("""



        SELECT *



        FROM viagens







        ORDER BY id DESC



    """)







    registros = cursor.fetchall()







    conexao.close()







    return [



        dict(registro)



        for registro in registros



    ]











# ============================================================



# BUSCAR VIAGEM ABERTA



# ============================================================







def buscar_viagem_aberta(placa):



    """



    Busca a viagem atual da balsa.







    Uma viagem aberta é qualquer viagem que ainda não possui:







        data_fim



    """







    criar_tabela_viagens()







    conexao = conectar_banco()



    cursor = conexao.cursor()







    cursor.execute("""



        SELECT *







        FROM viagens







        WHERE placa = ?







        AND data_fim IS NULL







        ORDER BY id DESC







        LIMIT 1



    """, (



        placa,



    ))







    viagem = cursor.fetchone()







    conexao.close()







    if viagem is not None:



        return dict(viagem)







    return None











# ============================================================



# REGISTRAR SAÍDA DA VIAGEM



# ============================================================







def iniciar_viagem_banco(



    id_viagem,



    data_inicio



):



    """



    Marca uma viagem como iniciada.







    Não cria uma nova viagem.







    Apenas altera:







        data_inicio



        status = Em viagem



    """







    criar_tabela_viagens()







    conexao = conectar_banco()



    cursor = conexao.cursor()







    cursor.execute("""



        UPDATE viagens







        SET







            data_inicio = ?,



            status = ?







        WHERE id = ?







    """, (







        formatar_data_banco(



            data_inicio



        ),







        "Em viagem",







        id_viagem







    ))







    conexao.commit()



    conexao.close()











# ============================================================



# FINALIZAR VIAGEM



# ============================================================







def finalizar_viagem_banco(



    id_viagem,



    data_fim,



    duracao_horas,



    diferenca_horas,



    status_prazo



):



    """



    Finaliza uma viagem existente.







    Atualiza:







        data_fim



        status



        duracao



        diferença para o prazo



        classificação do prazo



    """







    criar_tabela_viagens()







    conexao = conectar_banco()



    cursor = conexao.cursor()







    cursor.execute("""



        UPDATE viagens







        SET







            data_fim = ?,







            status = ?,







            duracao_horas = ?,







            diferenca_horas = ?,







            status_prazo = ?







        WHERE id = ?







    """, (







        formatar_data_banco(



            data_fim



        ),







        "Finalizada",







        duracao_horas,







        diferenca_horas,







        status_prazo,







        id_viagem







    ))







    conexao.commit()



    conexao.close()











# ============================================================



# BUSCAR ÚLTIMA VIAGEM FINALIZADA



# ============================================================







def buscar_ultima_viagem_finalizada(



    placa



):



    """



    Busca a última viagem concluída de uma balsa.







    É útil para calcular tempo de permanência no porto.



    """







    criar_tabela_viagens()







    conexao = conectar_banco()



    cursor = conexao.cursor()







    cursor.execute("""



        SELECT *







        FROM viagens







        WHERE placa = ?







        AND data_fim IS NOT NULL







        ORDER BY id DESC







        LIMIT 1



    """, (



        placa,



    ))







    viagem = cursor.fetchone()







    conexao.close()







    if viagem is not None:



        return dict(viagem)







    return None











# ============================================================



# AJUSTES MANUAIS



# ============================================================







def criar_tabela_ajustes():



    """



    Cria a tabela de auditoria dos ajustes manuais.







    Nenhuma correção manual deve acontecer silenciosamente.



    """







    conexao = conectar_banco()



    cursor = conexao.cursor()







    cursor.execute("""



        CREATE TABLE IF NOT EXISTS ajustes_viagem (







            id INTEGER PRIMARY KEY AUTOINCREMENT,







            placa TEXT,







            codigo_viagem TEXT,







            tipo_ajuste TEXT,







            valor_anterior TEXT,







            valor_novo TEXT,







            motivo TEXT,







            data_ajuste TEXT



        )



    """)







    conexao.commit()



    conexao.close()











# ============================================================



# REGISTRAR AJUSTE MANUAL



# ============================================================







def registrar_ajuste(



    placa,



    codigo_viagem,



    tipo_ajuste,



    valor_anterior,



    valor_novo,



    motivo,



    data_ajuste



):



    """



    Registra uma intervenção manual realizada em uma viagem.







    Exemplo:







        Saída manual



        Chegada manual



    """







    criar_tabela_ajustes()







    conexao = conectar_banco()



    cursor = conexao.cursor()







    cursor.execute("""



        INSERT INTO ajustes_viagem (







            placa,



            codigo_viagem,



            tipo_ajuste,



            valor_anterior,



            valor_novo,



            motivo,



            data_ajuste







        )







        VALUES (?, ?, ?, ?, ?, ?, ?)







    """, (







        placa,



        codigo_viagem,



        tipo_ajuste,



        valor_anterior,



        valor_novo,



        motivo,



        formatar_data_banco(



            data_ajuste



        )







    ))







    conexao.commit()



    conexao.close()











# ============================================================



# CONSULTAR AJUSTES MANUAIS



# ============================================================







def consultar_ajustes():



    """



    Retorna o histórico das alterações manuais.



    """







    criar_tabela_ajustes()







    conexao = conectar_banco()



    cursor = conexao.cursor()







    cursor.execute("""



        SELECT *







        FROM ajustes_viagem







        ORDER BY id DESC



    """)







    registros = cursor.fetchall()







    conexao.close()







    return [



        dict(registro)



        for registro in registros



    ]







# ============================================================

# CORRIGIR DATAS DE UMA VIAGEM

# ============================================================



def corrigir_datas_viagem(
    id_viagem,
    nova_data_inicio,
    nova_data_fim,
    motivo
):
    # --------------------------------------------------------
    # VALIDAÇÃO DE FORMATO DAS DATAS
    # --------------------------------------------------------
    # Mesmo que o dashboard valide antes, esta é a última
    # barreira: nenhum dado mal-formatado chega ao SQLite.
    # --------------------------------------------------------

    for rotulo, valor in (
        ("saída", nova_data_inicio),
        ("chegada", nova_data_fim),
    ):
        if valor and isinstance(valor, str):
            try:
                datetime.strptime(valor, "%Y-%m-%d %H:%M:%S")
            except ValueError as e:
                raise ValueError(
                    f"Data de {rotulo} inválida: '{valor}'. "
                    f"Use o formato YYYY-MM-DD HH:MM:SS. "
                    f"Detalhe: {e}"
                )

    # Validação de ordem (chegada >= saída) também
    if nova_data_inicio and nova_data_fim:
        if isinstance(nova_data_inicio, str):
            ini = datetime.strptime(
                nova_data_inicio, "%Y-%m-%d %H:%M:%S"
            )
        else:
            ini = nova_data_inicio

        if isinstance(nova_data_fim, str):
            fim = datetime.strptime(
                nova_data_fim, "%Y-%m-%d %H:%M:%S"
            )
        else:
            fim = nova_data_fim

        if fim < ini:
            raise ValueError(
                "A chegada não pode ser anterior à saída."
            )

    # ... resto da função segue igual

    criar_tabela_viagens()

    criar_tabela_ajustes()



    if not motivo or not motivo.strip():

        raise ValueError(

            "Informe o motivo da correção."

        )



    conexao = conectar_banco()

    cursor = conexao.cursor()



    try:



        # ----------------------------------------------------

        # BUSCAR VIAGEM

        # ----------------------------------------------------



        cursor.execute("""

            SELECT *

            FROM viagens

            WHERE id = ?

        """, (

            id_viagem,

        ))



        viagem = cursor.fetchone()



        if viagem is None:

            raise ValueError(

                "Viagem não encontrada."

            )



        viagem = dict(viagem)



        data_inicio_anterior = viagem["data_inicio"]

        data_fim_anterior = viagem["data_fim"]



        # ----------------------------------------------------

        # FORMATAR NOVAS DATAS

        # ----------------------------------------------------



        nova_data_inicio = formatar_data_banco(

            nova_data_inicio

        )



        nova_data_fim = formatar_data_banco(

            nova_data_fim

        )



        # ----------------------------------------------------

        # VALIDAÇÕES

        # ----------------------------------------------------



        if (

            nova_data_inicio is None

            and nova_data_fim is not None

        ):

            raise ValueError(

                "Uma viagem não pode ter chegada sem saída."

            )



        inicio = None

        fim = None



        if nova_data_inicio:

            inicio = datetime.strptime(

                nova_data_inicio,

                "%Y-%m-%d %H:%M:%S"

            )



        if nova_data_fim:

            fim = datetime.strptime(

                nova_data_fim,

                "%Y-%m-%d %H:%M:%S"

            )



        if inicio and fim and fim < inicio:

            raise ValueError(

                "A chegada não pode ser anterior à saída."

            )



        # ----------------------------------------------------

        # RECALCULAR DADOS DERIVADOS

        # ----------------------------------------------------



        duracao_horas = None

        diferenca_horas = None

        status_prazo = None



        if inicio and fim:



            duracao_horas = (

                fim - inicio

            ).total_seconds() / 3600



            prazo_horas = viagem["prazo_horas"]



            if prazo_horas is not None:



                diferenca_horas = (

                    duracao_horas - prazo_horas

                )



                if diferenca_horas <= 0:

                    status_prazo = "No prazo"

                else:

                    status_prazo = "Atrasada"



            status = "Finalizada"



        elif inicio:



            status = "Em viagem"



        else:



            status = "Aguardando carregamento"



        # ----------------------------------------------------

        # ATUALIZAR VIAGEM

        # ----------------------------------------------------



        cursor.execute("""

            UPDATE viagens



            SET

                data_inicio = ?,

                data_fim = ?,

                status = ?,

                duracao_horas = ?,

                diferenca_horas = ?,

                status_prazo = ?



            WHERE id = ?

        """, (



            nova_data_inicio,

            nova_data_fim,

            status,

            duracao_horas,

            diferenca_horas,

            status_prazo,

            id_viagem



        ))



        # ----------------------------------------------------

        # REGISTRAR AUDITORIA

        # ----------------------------------------------------



        agora = datetime.now().strftime(

            "%Y-%m-%d %H:%M:%S"

        )



        if data_inicio_anterior != nova_data_inicio:



            cursor.execute("""

                INSERT INTO ajustes_viagem (

                    placa,

                    codigo_viagem,

                    tipo_ajuste,

                    valor_anterior,

                    valor_novo,

                    motivo,

                    data_ajuste

                )



                VALUES (?, ?, ?, ?, ?, ?, ?)

            """, (



                viagem["placa"],

                viagem["codigo_viagem"],

                "Correção de saída",

                data_inicio_anterior,

                nova_data_inicio,

                motivo.strip(),

                agora



            ))



        if data_fim_anterior != nova_data_fim:



            cursor.execute("""

                INSERT INTO ajustes_viagem (

                    placa,

                    codigo_viagem,

                    tipo_ajuste,

                    valor_anterior,

                    valor_novo,

                    motivo,

                    data_ajuste

                )



                VALUES (?, ?, ?, ?, ?, ?, ?)

            """, (



                viagem["placa"],

                viagem["codigo_viagem"],

                "Correção de chegada",

                data_fim_anterior,

                nova_data_fim,

                motivo.strip(),

                agora



            ))



        conexao.commit()



        # ----------------------------------------------------

        # RETORNAR VIAGEM ATUALIZADA

        # ----------------------------------------------------



        cursor.execute("""

            SELECT *

            FROM viagens

            WHERE id = ?

        """, (

            id_viagem,

        ))



        resultado = cursor.fetchone()



        return dict(resultado)



    except Exception:

        conexao.rollback()

        raise



    finally:

        conexao.close()





# ============================================================



# BUSCAR ÚLTIMO PONTO DA ROTA



# ============================================================







def buscar_ultimo_ponto_rota(



    placa,



    data_inicio,



    pontos_validos



):



    """



    Procura o ponto de rota mais recente pelo qual



    a balsa passou durante a viagem.







    Somente eventos do tipo Entrada são considerados.



    """







    if not tabela_existe(



        "area_restrita"



    ):



        return None







    if not pontos_validos:



        return None







    conexao = conectar_banco()



    cursor = conexao.cursor()











    # ========================================================



    # CRIAR PLACEHOLDERS PARA O SQL



    # ========================================================







    # Exemplo:



    #



    # 4 pontos válidos:



    #



    # ?, ?, ?, ?







    placeholders = ",".join(



        ["?"] * len(pontos_validos)



    )











    # ========================================================



    # CONSULTA



    # ========================================================







    consulta = f"""



        SELECT *







        FROM area_restrita







        WHERE placa = ?







        AND evento = 'Entrada'







        AND dataGPS >= ?







        AND area IN ({placeholders})







        ORDER BY dataGPS DESC







        LIMIT 1



    """











    parametros = [







        placa,







        formatar_data_banco(



            data_inicio



        ),







        *pontos_validos







    ]











    cursor.execute(



        consulta,



        parametros



    )











    registro = cursor.fetchone()







    conexao.close()











    if registro is not None:



        return dict(registro)







    return None











# ============================================================



# HISTÓRICO DOS TRECHOS



# ============================================================







def criar_tabela_historico_trechos():



    """



    Cria a tabela utilizada para aprender o tempo médio



    de cada trecho das rotas.







    Esses dados são utilizados futuramente pelo ETA.



    """







    conexao = conectar_banco()



    cursor = conexao.cursor()







    cursor.execute("""



        CREATE TABLE IF NOT EXISTS historico_trechos (







            id INTEGER PRIMARY KEY AUTOINCREMENT,







            placa TEXT,







            balsa TEXT,







            codigo_viagem TEXT,







            origem_viagem TEXT,







            destino_viagem TEXT,







            ponto_origem TEXT,







            ponto_destino TEXT,







            data_origem TEXT,







            data_destino TEXT,







            duracao_minutos REAL,







            media_referencia_minutos REAL,







            desvio_minutos REAL,







            atipico INTEGER DEFAULT 0,







            fonte_media TEXT,







            usar_no_eta INTEGER DEFAULT 1,







            data_registro TEXT,







            UNIQUE(



                codigo_viagem,



                ponto_origem,



                ponto_destino,



                data_destino



            )



        )



    """)







    conexao.commit()



    conexao.close()











# ============================================================



# SALVAR HISTÓRICO DE TRECHO



# ============================================================







def salvar_historico_trecho(



    placa,



    balsa,



    codigo_viagem,



    origem_viagem,



    destino_viagem,



    ponto_origem,



    ponto_destino,



    data_origem,



    data_destino,



    duracao_minutos,



    media_referencia_minutos,



    desvio_minutos,



    atipico,



    fonte_media,



    usar_no_eta,



    data_registro



):



    """



    Salva o desempenho real de um trecho percorrido.







    INSERT OR IGNORE impede registrar o mesmo trecho duas vezes.



    """







    criar_tabela_historico_trechos()







    conexao = conectar_banco()



    cursor = conexao.cursor()







    cursor.execute("""



        INSERT OR IGNORE INTO historico_trechos (







            placa,



            balsa,



            codigo_viagem,







            origem_viagem,



            destino_viagem,







            ponto_origem,



            ponto_destino,







            data_origem,



            data_destino,







            duracao_minutos,







            media_referencia_minutos,



            desvio_minutos,







            atipico,



            fonte_media,



            usar_no_eta,







            data_registro







        )







        VALUES (



            ?, ?, ?,



            ?, ?,



            ?, ?,



            ?, ?,



            ?,



            ?, ?,



            ?, ?, ?,



            ?



        )







    """, (







        placa,



        balsa,



        codigo_viagem,







        origem_viagem,



        destino_viagem,







        ponto_origem,



        ponto_destino,







        formatar_data_banco(



            data_origem



        ),







        formatar_data_banco(



            data_destino



        ),







        duracao_minutos,







        media_referencia_minutos,



        desvio_minutos,







        1 if atipico else 0,







        fonte_media,







        1 if usar_no_eta else 0,







        formatar_data_banco(



            data_registro



        )







    ))







    conexao.commit()



    conexao.close()











# ============================================================



# BUSCAR ÚLTIMOS TRECHOS VÁLIDOS



# ============================================================







def buscar_ultimos_trechos_validos(



    origem_viagem,



    destino_viagem,



    ponto_origem,



    ponto_destino,



    limite=3



):



    """



    Busca os últimos trechos considerados válidos



    para cálculo da média do ETA.







    Registros atípicos ou desativados manualmente



    não participam da consulta.



    """







    criar_tabela_historico_trechos()







    conexao = conectar_banco()



    cursor = conexao.cursor()







    cursor.execute("""



        SELECT *







        FROM historico_trechos







        WHERE origem_viagem = ?







        AND destino_viagem = ?







        AND ponto_origem = ?







        AND ponto_destino = ?







        AND atipico = 0







        AND usar_no_eta = 1







        ORDER BY data_destino DESC







        LIMIT ?







    """, (







        origem_viagem,



        destino_viagem,



        ponto_origem,



        ponto_destino,



        limite







    ))







    registros = cursor.fetchall()







    conexao.close()







    return [



        dict(registro)



        for registro in registros



    ]











# ============================================================



# CONSULTAR HISTÓRICO DOS TRECHOS



# ============================================================







def consultar_historico_trechos():



    """



    Retorna todo histórico dos trechos registrados.



    """







    criar_tabela_historico_trechos()







    conexao = conectar_banco()



    cursor = conexao.cursor()







    cursor.execute("""



        SELECT *







        FROM historico_trechos







        ORDER BY data_destino DESC



    """)







    registros = cursor.fetchall()







    conexao.close()







    return [



        dict(registro)



        for registro in registros



    ]











# ============================================================



# BUSCAR TRECHOS DE UMA VIAGEM



# ============================================================







def buscar_trechos_viagem(



    codigo_viagem



):



    """



    Retorna todos os trechos pertencentes a uma viagem,



    em ordem cronológica.



    """







    criar_tabela_historico_trechos()







    conexao = conectar_banco()



    cursor = conexao.cursor()







    cursor.execute("""



        SELECT *







        FROM historico_trechos







        WHERE codigo_viagem = ?







        ORDER BY data_destino ASC







    """, (



        codigo_viagem,



    ))







    registros = cursor.fetchall()







    conexao.close()







    return [



        dict(registro)



        for registro in registros



    ]











# ============================================================



# ALTERAR USO DOS TRECHOS NO ETA



# ============================================================







def atualizar_uso_eta_trechos_viagem(



    codigo_viagem,



    usar_no_eta



):



    """



    Permite incluir ou retirar todos os trechos de uma viagem



    do aprendizado do ETA.







    Não apagamos os registros.







    Apenas alteramos se eles podem participar do cálculo.



    """







    criar_tabela_historico_trechos()







    conexao = conectar_banco()



    cursor = conexao.cursor()







    cursor.execute("""



        UPDATE historico_trechos







        SET usar_no_eta = ?







        WHERE codigo_viagem = ?







    """, (







        1 if usar_no_eta else 0,







        codigo_viagem







    ))







    conexao.commit()



    conexao.close()











# ============================================================



# GARANTIR CAMPOS DO ETA NA TABELA DE VIAGENS



# ============================================================







def garantir_campos_eta_viagens():



    """



    Faz uma pequena migração automática do banco.







    Como o projeto evoluiu depois que a tabela viagens



    já existia, alguns bancos antigos podem não possuir



    as colunas utilizadas pelo ETA.







    Esta função adiciona apenas as colunas ausentes.



    """







    criar_tabela_viagens()







    conexao = conectar_banco()



    cursor = conexao.cursor()











    # ========================================================



    # DESCOBRIR COLUNAS EXISTENTES



    # ========================================================







    cursor.execute("""



        PRAGMA table_info(viagens)



    """)







    colunas = {







        coluna["name"]







        for coluna in cursor.fetchall()







    }











    # ========================================================



    # VIAGEM ATÍPICA



    # ========================================================







    if "viagem_atipica" not in colunas:







        cursor.execute("""



            ALTER TABLE viagens







            ADD COLUMN viagem_atipica INTEGER



        """)











    # ========================================================



    # USAR NO ETA



    # ========================================================







    if "usar_no_eta" not in colunas:







        cursor.execute("""



            ALTER TABLE viagens







            ADD COLUMN usar_no_eta INTEGER DEFAULT 0



        """)











    # ========================================================



    # MOTIVO DA CLASSIFICAÇÃO



    # ========================================================







    if "motivo_eta" not in colunas:







        cursor.execute("""



            ALTER TABLE viagens







            ADD COLUMN motivo_eta TEXT



        """)











    # ========================================================



    # CLASSIFICAÇÃO REALIZADA



    # ========================================================







    if "eta_classificado" not in colunas:







        cursor.execute("""



            ALTER TABLE viagens







            ADD COLUMN eta_classificado INTEGER DEFAULT 0



        """)











    conexao.commit()



    conexao.close()











# ============================================================



# SALVAR CLASSIFICAÇÃO ETA



# ============================================================







def atualizar_classificacao_eta_viagem(



    codigo_viagem,



    viagem_atipica,



    usar_no_eta,



    motivo_eta



):



    """



    Salva a classificação utilizada pelo sistema de ETA.







    viagem_atipica:



        indica comportamento fora do padrão.







    usar_no_eta:



        define se essa viagem participa do aprendizado.







    motivo_eta:



        registra a explicação da decisão.



    """







    garantir_campos_eta_viagens()







    conexao = conectar_banco()



    cursor = conexao.cursor()







    cursor.execute("""



        UPDATE viagens







        SET







            viagem_atipica = ?,







            usar_no_eta = ?,







            motivo_eta = ?,







            eta_classificado = 1







        WHERE codigo_viagem = ?







    """, (







        1 if viagem_atipica else 0,







        1 if usar_no_eta else 0,







        motivo_eta,







        codigo_viagem







    ))







    conexao.commit()



    conexao.close()











# ============================================================



# ESTADO DE REFERÊNCIA DAS BALSAS



# ============================================================







def criar_tabela_referencias_balsas():



    """



    Cria a tabela que guarda a fotografia operacional



    das balsas no momento de implantação das novas geofences.







    IMPORTANTE:







    Esta tabela NÃO representa o estado atual da balsa.







    Ela representa o estado conhecido no marco:







        17/08/2026 13:27:00







    Dessa forma conseguimos futuramente reconstruir



    ou reprocessar as viagens sem depender do arquivo balsas.py.



    """







    conexao = conectar_banco()



    cursor = conexao.cursor()







    cursor.execute("""



        CREATE TABLE IF NOT EXISTS referencias_balsas (







            id INTEGER PRIMARY KEY AUTOINCREMENT,







            placa TEXT NOT NULL,







            viagem_referencia INTEGER NOT NULL,







            status_referencia TEXT NOT NULL,







            data_inicio_referencia TEXT,







            data_chegada_referencia TEXT,







            referencia_confirmada INTEGER NOT NULL DEFAULT 0,







            data_corte_geofence TEXT NOT NULL,







            data_migracao TEXT,







            UNIQUE(



                placa,



                data_corte_geofence



            )



        )



    """)







    conexao.commit()



    conexao.close()











# ============================================================



# SALVAR ESTADO DE REFERÊNCIA



# ============================================================







def salvar_referencia_balsa(



    placa,



    viagem_referencia,



    status_referencia,



    data_inicio_referencia,



    data_chegada_referencia,



    referencia_confirmada,



    data_corte_geofence



):



    """



    Salva a fotografia operacional de uma balsa.







    Se essa placa já possuir referência para o mesmo



    corte de geofence, os dados são atualizados.







    Isso permite executar a migração novamente sem



    criar registros duplicados.



    """







    criar_tabela_referencias_balsas()







    conexao = conectar_banco()



    cursor = conexao.cursor()







    cursor.execute("""



        INSERT INTO referencias_balsas (







            placa,



            viagem_referencia,



            status_referencia,



            data_inicio_referencia,



            data_chegada_referencia,



            referencia_confirmada,



            data_corte_geofence,



            data_migracao







        )







        VALUES (?, ?, ?, ?, ?, ?, ?, ?)







        ON CONFLICT(



            placa,



            data_corte_geofence



        )







        DO UPDATE SET







            viagem_referencia =



                excluded.viagem_referencia,







            status_referencia =



                excluded.status_referencia,







            data_inicio_referencia =



                excluded.data_inicio_referencia,







            data_chegada_referencia =



                excluded.data_chegada_referencia,







            referencia_confirmada =



                excluded.referencia_confirmada,







            data_migracao =



                excluded.data_migracao







    """, (







        placa,







        viagem_referencia,







        status_referencia,







        formatar_data_banco(



            data_inicio_referencia



        ),







        formatar_data_banco(



            data_chegada_referencia



        ),







        1 if referencia_confirmada else 0,







        formatar_data_banco(



            data_corte_geofence



        ),







        datetime.now().strftime(



            "%Y-%m-%d %H:%M:%S"



        )







    ))







    conexao.commit()



    conexao.close()











# ============================================================



# BUSCAR REFERÊNCIA DE UMA BALSA



# ============================================================







def buscar_referencia_balsa(



    placa,



    data_corte_geofence=None



):



    """



    Busca o estado de referência de uma balsa.







    Se data_corte_geofence for informada:



        procura especificamente aquele corte.







    Se não for informada:



        retorna a referência mais recente cadastrada.



    """







    criar_tabela_referencias_balsas()







    conexao = conectar_banco()



    cursor = conexao.cursor()











    if data_corte_geofence is not None:







        cursor.execute("""



            SELECT *







            FROM referencias_balsas







            WHERE placa = ?







            AND data_corte_geofence = ?







            LIMIT 1



        """, (







            placa,







            formatar_data_banco(



                data_corte_geofence



            )







        ))











    else:







        cursor.execute("""



            SELECT *







            FROM referencias_balsas







            WHERE placa = ?







            ORDER BY data_corte_geofence DESC







            LIMIT 1



        """, (



            placa,



        ))











    resultado = cursor.fetchone()







    conexao.close()











    if resultado is not None:



        return dict(resultado)







    return None











# ============================================================



# CONSULTAR TODAS AS REFERÊNCIAS



# ============================================================







def consultar_referencias_balsas():



    """



    Retorna todas as fotografias operacionais



    cadastradas no banco.



    """







    criar_tabela_referencias_balsas()







    conexao = conectar_banco()



    cursor = conexao.cursor()







    cursor.execute("""



        SELECT *







        FROM referencias_balsas







        ORDER BY placa ASC



    """)







    registros = cursor.fetchall()







    conexao.close()







    return [



        dict(registro)



        for registro in registros



    ]











# ============================================================



# CONSULTAR BALSAS ATIVAS COMO DICIONÁRIO



# ============================================================







def buscar_balsas_ativas():



    """



    Retorna todas as balsas ativas cadastradas no banco.







    O resultado é um dicionário cuja chave é a placa.







    Exemplo:







    {



        "ANT0012": {



            "id": 1,



            "placa": "ANT0012",



            "nome": "SW ANTUÉRPIA",



            ...



        }



    }







    Isso facilita a substituição do antigo dicionário BALSAS.



    """







    registros = consultar_balsas(



        somente_ativas=True



    )







    return {



        registro["placa"]: registro



        for registro in registros



    }











# ============================================================



# BUSCAR DATA DO CORTE DAS GEOFENCES



# ============================================================







def buscar_data_corte_geofence():



    """



    Retorna a data mais recente utilizada como marco



    das referências operacionais das balsas.







    Atualmente deverá retornar:







        2026-08-17 13:27:00



    """







    criar_tabela_referencias_balsas()







    conexao = conectar_banco()



    cursor = conexao.cursor()







    cursor.execute("""



        SELECT MAX(data_corte_geofence)



        AS data_corte_geofence







        FROM referencias_balsas



    """)







    resultado = cursor.fetchone()







    conexao.close()







    if (



        resultado is None



        or



        resultado["data_corte_geofence"] is None



    ):



        return None







    return resultado[



        "data_corte_geofence"



    ]





# ============================================================

# SEGURANÇA - USUÁRIOS, GRUPOS E PERMISSÕES

# ============================================================



def criar_tabelas_seguranca():

    """

    Cria a estrutura básica de controle de acesso do DashPy.



    IMPORTANTE:

    - usuários não possuem nível fixo;

    - usuários pertencem a grupos;

    - grupos recebem permissões;

    - as permissões determinam o que cada usuário pode fazer.

    """



    conexao = conectar_banco()

    cursor = conexao.cursor()



    # --------------------------------------------------------

    # USUÁRIOS

    # --------------------------------------------------------



    cursor.execute("""

        CREATE TABLE IF NOT EXISTS usuarios (



            id INTEGER PRIMARY KEY AUTOINCREMENT,



            nome TEXT NOT NULL,



            email TEXT NOT NULL UNIQUE,



            empresa TEXT,



            cargo TEXT,



            setor TEXT,



            senha_hash TEXT NOT NULL,



            ativo INTEGER NOT NULL DEFAULT 1,



            data_cadastro TEXT NOT NULL

        )

    """)



    # --------------------------------------------------------

    # GRUPOS

    # --------------------------------------------------------



    cursor.execute("""

        CREATE TABLE IF NOT EXISTS grupos (



            id INTEGER PRIMARY KEY AUTOINCREMENT,



            nome TEXT NOT NULL UNIQUE,



            descricao TEXT,



            ativo INTEGER NOT NULL DEFAULT 1,



            data_cadastro TEXT NOT NULL

        )

    """)



    # --------------------------------------------------------

    # PERMISSÕES

    # --------------------------------------------------------



    cursor.execute("""

        CREATE TABLE IF NOT EXISTS permissoes (



            id INTEGER PRIMARY KEY AUTOINCREMENT,



            codigo TEXT NOT NULL UNIQUE,



            descricao TEXT

        )

    """)



    # --------------------------------------------------------

    # USUÁRIO <-> GRUPO

    # --------------------------------------------------------



    cursor.execute("""

        CREATE TABLE IF NOT EXISTS usuario_grupo (



            usuario_id INTEGER NOT NULL,



            grupo_id INTEGER NOT NULL,



            PRIMARY KEY (

                usuario_id,

                grupo_id

            ),



            FOREIGN KEY (usuario_id)

                REFERENCES usuarios(id),



            FOREIGN KEY (grupo_id)

                REFERENCES grupos(id)

        )

    """)



    # --------------------------------------------------------

    # GRUPO <-> PERMISSÃO

    # --------------------------------------------------------



    cursor.execute("""

        CREATE TABLE IF NOT EXISTS grupo_permissao (



            grupo_id INTEGER NOT NULL,



            permissao_id INTEGER NOT NULL,



            PRIMARY KEY (

                grupo_id,

                permissao_id

            ),



            FOREIGN KEY (grupo_id)

                REFERENCES grupos(id),



            FOREIGN KEY (permissao_id)

                REFERENCES permissoes(id)

        )

    """)



    # --------------------------------------------------------
    # SOLICITAÇÕES DE ACESSO
    # --------------------------------------------------------
    #
    # Esta tabela registra pedidos de acesso ao DashPy.
    #
    # IMPORTANTE:
    # - uma solicitação NÃO cria automaticamente um usuário;
    # - o solicitante NÃO escolhe grupos ou permissões;
    # - a solicitação nasce com status PENDENTE;
    # - um usuário autorizado fará a análise posteriormente;
    # - empresa é apenas informação cadastral e não concede
    #   acesso automaticamente.
    #
    # Fluxo esperado:
    #
    #     Pessoa solicita acesso
    #             ↓
    #     solicitação PENDENTE
    #             ↓
    #     análise por usuário autorizado
    #          ↙       ↘
    #     APROVADA    REJEITADA
    #
    # A criação da conta, associação aos grupos e definição
    # da senha serão tratadas em etapas posteriores.
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS solicitacoes_acesso (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            nome TEXT NOT NULL,

            email TEXT NOT NULL,

            empresa TEXT,

            cargo TEXT,

            setor TEXT,

            justificativa TEXT NOT NULL,

            status TEXT NOT NULL DEFAULT 'PENDENTE',

            data_solicitacao TEXT NOT NULL,

            data_analise TEXT,

            analisado_por INTEGER,

            motivo_rejeicao TEXT,

            FOREIGN KEY (analisado_por)
                REFERENCES usuarios(id)

        )
    """)


    # --------------------------------------------------------
    # EVITAR SOLICITAÇÕES PENDENTES DUPLICADAS
    # --------------------------------------------------------
    #
    # O mesmo e-mail não pode possuir duas solicitações com
    # status PENDENTE ao mesmo tempo.
    #
    # LOWER(TRIM(email)) normaliza a comparação diretamente
    # no SQLite:
    #
    #     JOAO@EMPRESA.COM
    #     joao@empresa.com
    #      joao@empresa.com
    #
    # são tratados como o mesmo endereço.
    #
    # O índice é parcial porque só considera solicitações
    # PENDENTES. Assim, uma solicitação antiga REJEITADA,
    # APROVADA ou CANCELADA não impede um novo pedido futuro.
    # --------------------------------------------------------

    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS
            idx_solicitacao_acesso_email_pendente
        ON solicitacoes_acesso (
            LOWER(TRIM(email))
        )
        WHERE status = 'PENDENTE'
    """)


    conexao.commit()

    conexao.close()





# ============================================================

# CATÁLOGO DE PERMISSÕES

# ============================================================



PERMISSOES_SISTEMA = {



    # Dashboard

    "dashboard.visualizar":

        "Visualizar o painel principal",

    # Mapa
    "mapa.visualizar":
        "Visualizar o mapa e a localização das balsas",



    # Viagens

    "viagens.visualizar":

        "Visualizar viagens",



    "viagens.editar":

        "Editar informações de viagens",



    "viagens.corrigir":

        "Realizar correções em viagens",



    # Inconsistências

    "inconsistencias.visualizar":

        "Visualizar inconsistências detectadas",



    "inconsistencias.confirmar":

        "Confirmar informações sinalizadas pelo sistema",



    # Correções

    "correcoes.solicitar":

        "Solicitar correção de informações",



    "correcoes.aprovar":

        "Aprovar solicitações de correção",



    "correcoes.rejeitar":

        "Rejeitar solicitações de correção",



    # Solicitações de acesso

    "acessos.visualizar":

        "Visualizar solicitações de acesso",



    "acessos.aprovar":

        "Aprovar solicitações de acesso",



    "acessos.rejeitar":

        "Rejeitar solicitações de acesso",



    # Usuários

    "usuarios.visualizar":

        "Visualizar usuários",



    "usuarios.criar":

        "Criar usuários",



    "usuarios.editar":

        "Editar usuários",



    "usuarios.desativar":

        "Desativar usuários",



    # Grupos

    "grupos.visualizar":

        "Visualizar grupos",



    "grupos.criar":

        "Criar grupos",



    "grupos.editar":

        "Editar grupos e suas permissões",



    # Auditoria

    "auditoria.visualizar":

        "Visualizar registros de auditoria",

}









def cadastrar_permissoes_sistema():

    """

    Garante que todas as permissões conhecidas pelo DashPy

    existam no banco.



    INSERT OR IGNORE permite executar esta função várias vezes

    sem duplicar permissões.

    """



    criar_tabelas_seguranca()



    conexao = conectar_banco()

    cursor = conexao.cursor()



    for codigo, descricao in PERMISSOES_SISTEMA.items():



        cursor.execute("""

            INSERT OR IGNORE INTO permissoes (

                codigo,

                descricao

            )

            VALUES (?, ?)

        """, (

            codigo,

            descricao

        ))



    conexao.commit()

    conexao.close()







# ============================================================

# CONSULTAR PERMISSÕES

# ============================================================



def consultar_permissoes():

    """

    Retorna todas as permissões disponíveis no DashPy.



    Antes da consulta, garante que o catálogo oficial de

    permissões esteja cadastrado no banco.



    Retorno:

        Lista de dicionários contendo os dados das permissões.



    Exemplo:



        [

            {

                "id": 1,

                "codigo": "dashboard.visualizar",

                "descricao": "Visualizar o painel principal"

            }

        ]

    """



    # --------------------------------------------------------

    # GARANTIR CATÁLOGO DE PERMISSÕES

    # --------------------------------------------------------

    #

    # Caso uma nova permissão tenha sido adicionada ao código,

    # esta chamada garante que ela também exista no banco.

    #

    # Como cadastrar_permissoes_sistema() utiliza

    # INSERT OR IGNORE, permissões existentes não serão

    # duplicadas.

    # --------------------------------------------------------



    cadastrar_permissoes_sistema()



    # --------------------------------------------------------

    # CONSULTAR BANCO

    # --------------------------------------------------------



    conexao = conectar_banco()

    cursor = conexao.cursor()



    cursor.execute("""

        SELECT *

        FROM permissoes

        ORDER BY codigo ASC

    """)



    registros = cursor.fetchall()



    conexao.close()



    # --------------------------------------------------------

    # CONVERTER RESULTADO

    # --------------------------------------------------------

    #

    # sqlite3.Row é convertido para dict para que outros

    # módulos do projeto não precisem conhecer detalhes

    # internos do SQLite.

    # --------------------------------------------------------



    return [

        dict(registro)

        for registro in registros

    ]


# ============================================================
# GERENCIAMENTO DE GRUPOS E PERMISSÕES
# ============================================================
#
# Os grupos NÃO representam regras fixas do sistema.
#
# Exemplos de nomes possíveis:
#
#     Administrador
#     Operador
#     Cliente Honda
#     Cliente LSL
#
# O nome do grupo é apenas configuração.
# O que realmente autoriza uma ação são as permissões
# associadas ao grupo.
#
# Dessa forma, o código não precisa conhecer nomes como
# "Administrador" ou "Operador".
# ============================================================


def criar_grupo(nome, descricao=None):
    """
    Cria um novo grupo de acesso.

    O nome do grupo deve ser único.

    Retorna:
        dicionário com os dados do grupo criado.

    Importante:
        criar o grupo NÃO concede nenhuma permissão
        automaticamente.
    """

    criar_tabelas_seguranca()

    # Remove espaços acidentais no início/fim.
    nome = nome.strip() if nome else ""

    if not nome:
        raise ValueError("Informe o nome do grupo.")

    descricao = descricao.strip() if descricao else None

    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute("""
            INSERT INTO grupos (
                nome,
                descricao,
                ativo,
                data_cadastro
            )
            VALUES (?, ?, 1, ?)
        """, (
            nome,
            descricao,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))

        grupo_id = cursor.lastrowid

        conexao.commit()

        cursor.execute("""
            SELECT *
            FROM grupos
            WHERE id = ?
        """, (
            grupo_id,
        ))

        return dict(cursor.fetchone())

    except sqlite3.IntegrityError as erro:
        conexao.rollback()

        # Neste momento a restrição UNIQUE relevante é o nome.
        raise ValueError(
            f"Já existe um grupo com o nome '{nome}'."
        ) from erro

    finally:
        conexao.close()


def consultar_grupos(somente_ativos=False):
    """
    Retorna os grupos cadastrados.

    somente_ativos=True:
        retorna apenas grupos com ativo = 1.
    """

    criar_tabelas_seguranca()

    conexao = conectar_banco()
    cursor = conexao.cursor()

    if somente_ativos:
        cursor.execute("""
            SELECT *
            FROM grupos
            WHERE ativo = 1
            ORDER BY nome ASC
        """)
    else:
        cursor.execute("""
            SELECT *
            FROM grupos
            ORDER BY nome ASC
        """)

    registros = cursor.fetchall()
    conexao.close()

    return [
        dict(registro)
        for registro in registros
    ]


def buscar_grupo(grupo_id):
    """
    Busca um grupo pelo ID.

    Retorna:
        dicionário com os dados do grupo;
        None quando o grupo não existir.
    """

    criar_tabelas_seguranca()

    conexao = conectar_banco()
    cursor = conexao.cursor()

    cursor.execute("""
        SELECT *
        FROM grupos
        WHERE id = ?
        LIMIT 1
    """, (
        grupo_id,
    ))

    registro = cursor.fetchone()
    conexao.close()

    if registro is None:
        return None

    return dict(registro)


def editar_grupo(
    grupo_id,
    nome=None,
    descricao=None,
    ativo=None
):
    """
    Edita os dados básicos de um grupo.

    Somente os campos informados são alterados.

    Isso permite, por exemplo:
        - renomear o grupo;
        - alterar sua descrição;
        - ativar/desativar o grupo.

    As permissões são administradas separadamente.
    """

    criar_tabelas_seguranca()

    grupo_atual = buscar_grupo(grupo_id)

    if grupo_atual is None:
        raise ValueError("Grupo não encontrado.")

    novo_nome = grupo_atual["nome"]
    nova_descricao = grupo_atual["descricao"]
    novo_ativo = grupo_atual["ativo"]

    if nome is not None:
        novo_nome = nome.strip()

        if not novo_nome:
            raise ValueError("O nome do grupo não pode ficar vazio.")

    if descricao is not None:
        nova_descricao = descricao.strip() or None

    if ativo is not None:
        novo_ativo = 1 if ativo else 0

    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute("""
            UPDATE grupos
            SET
                nome = ?,
                descricao = ?,
                ativo = ?
            WHERE id = ?
        """, (
            novo_nome,
            nova_descricao,
            novo_ativo,
            grupo_id
        ))

        conexao.commit()

        cursor.execute("""
            SELECT *
            FROM grupos
            WHERE id = ?
        """, (
            grupo_id,
        ))

        return dict(cursor.fetchone())

    except sqlite3.IntegrityError as erro:
        conexao.rollback()

        raise ValueError(
            f"Já existe um grupo com o nome '{novo_nome}'."
        ) from erro

    finally:
        conexao.close()


def consultar_permissoes_grupo(grupo_id):
    """
    Retorna todas as permissões associadas a um grupo.

    A consulta utiliza JOIN para trazer o código e a descrição
    da permissão, e não apenas seu ID interno.
    """

    criar_tabelas_seguranca()
    cadastrar_permissoes_sistema()

    if buscar_grupo(grupo_id) is None:
        raise ValueError("Grupo não encontrado.")

    conexao = conectar_banco()
    cursor = conexao.cursor()

    cursor.execute("""
        SELECT
            p.id,
            p.codigo,
            p.descricao
        FROM permissoes AS p
        INNER JOIN grupo_permissao AS gp
            ON gp.permissao_id = p.id
        WHERE gp.grupo_id = ?
        ORDER BY p.codigo ASC
    """, (
        grupo_id,
    ))

    registros = cursor.fetchall()
    conexao.close()

    return [
        dict(registro)
        for registro in registros
    ]


def definir_permissoes_grupo(
    grupo_id,
    codigos_permissoes
):
    """
    Define o conjunto COMPLETO de permissões de um grupo.

    Exemplo:

        definir_permissoes_grupo(
            grupo_id=2,
            codigos_permissoes=[
                "dashboard.visualizar",
                "viagens.visualizar"
            ]
        )

    Atenção:
        esta função substitui as permissões atuais do grupo
        pelo conjunto recebido.

        Uma lista vazia é válida e deixa o grupo sem permissões.

    A operação acontece dentro de uma única transação:
        ou todas as relações são atualizadas,
        ou nenhuma alteração é gravada.
    """

    criar_tabelas_seguranca()
    cadastrar_permissoes_sistema()

    if buscar_grupo(grupo_id) is None:
        raise ValueError("Grupo não encontrado.")

    if codigos_permissoes is None:
        raise ValueError(
            "Informe a lista de permissões do grupo."
        )

    # Remove repetições sem depender da ordem recebida.
    codigos = list(dict.fromkeys(codigos_permissoes))

    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        ids_permissoes = []

        # Primeiro validamos TODOS os códigos.
        # Assim não alteramos o grupo parcialmente caso exista
        # alguma permissão inválida na lista.
        for codigo in codigos:
            cursor.execute("""
                SELECT id
                FROM permissoes
                WHERE codigo = ?
                LIMIT 1
            """, (
                codigo,
            ))

            permissao = cursor.fetchone()

            if permissao is None:
                raise ValueError(
                    f"Permissão desconhecida: {codigo}"
                )

            ids_permissoes.append(permissao["id"])

        # Somente depois da validação removemos as relações antigas.
        cursor.execute("""
            DELETE FROM grupo_permissao
            WHERE grupo_id = ?
        """, (
            grupo_id,
        ))

        for permissao_id in ids_permissoes:
            cursor.execute("""
                INSERT INTO grupo_permissao (
                    grupo_id,
                    permissao_id
                )
                VALUES (?, ?)
            """, (
                grupo_id,
                permissao_id
            ))

        conexao.commit()

    except Exception:
        conexao.rollback()
        raise

    finally:
        conexao.close()

    return consultar_permissoes_grupo(grupo_id)


def adicionar_permissao_grupo(
    grupo_id,
    codigo_permissao
):
    """
    Adiciona uma única permissão a um grupo.

    Se a relação já existir, INSERT OR IGNORE evita duplicidade.
    """

    criar_tabelas_seguranca()
    cadastrar_permissoes_sistema()

    if buscar_grupo(grupo_id) is None:
        raise ValueError("Grupo não encontrado.")

    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute("""
            SELECT id
            FROM permissoes
            WHERE codigo = ?
            LIMIT 1
        """, (
            codigo_permissao,
        ))

        permissao = cursor.fetchone()

        if permissao is None:
            raise ValueError(
                f"Permissão desconhecida: {codigo_permissao}"
            )

        cursor.execute("""
            INSERT OR IGNORE INTO grupo_permissao (
                grupo_id,
                permissao_id
            )
            VALUES (?, ?)
        """, (
            grupo_id,
            permissao["id"]
        ))

        conexao.commit()

    except Exception:
        conexao.rollback()
        raise

    finally:
        conexao.close()

    return consultar_permissoes_grupo(grupo_id)


def remover_permissao_grupo(
    grupo_id,
    codigo_permissao
):
    """
    Remove uma única permissão de um grupo.

    A permissão continua existindo no catálogo do sistema;
    removemos apenas a relação dela com o grupo.
    """

    criar_tabelas_seguranca()

    if buscar_grupo(grupo_id) is None:
        raise ValueError("Grupo não encontrado.")

    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute("""
            SELECT id
            FROM permissoes
            WHERE codigo = ?
            LIMIT 1
        """, (
            codigo_permissao,
        ))

        permissao = cursor.fetchone()

        if permissao is None:
            raise ValueError(
                f"Permissão desconhecida: {codigo_permissao}"
            )

        cursor.execute("""
            DELETE FROM grupo_permissao
            WHERE grupo_id = ?
            AND permissao_id = ?
        """, (
            grupo_id,
            permissao["id"]
        ))

        conexao.commit()

    except Exception:
        conexao.rollback()
        raise

    finally:
        conexao.close()

    return consultar_permissoes_grupo(grupo_id)



# ============================================================
# SOLICITAÇÕES DE ACESSO
# ============================================================
#
# Esta seção concentra as operações relacionadas aos pedidos
# de acesso ao DashPy.
#
# Regra importante:
#
#     solicitar acesso != criar usuário
#
# A pessoa apenas envia seus dados para análise.
# Nenhuma conta, grupo ou permissão é criada nesta etapa.
# ============================================================


def criar_solicitacao_acesso(
    nome,
    email,
    empresa,
    cargo,
    setor,
    justificativa
):
    """
    Registra uma nova solicitação de acesso ao DashPy.

    A função:

    1. valida os campos obrigatórios;
    2. normaliza o e-mail;
    3. verifica se já existe solicitação PENDENTE;
    4. grava o pedido com status PENDENTE;
    5. registra automaticamente a data/hora;
    6. retorna a solicitação criada.

    IMPORTANTE:

    Esta função NÃO cria usuário.
    Esta função NÃO define senha.
    Esta função NÃO associa grupos ou permissões.
    """

    # Garante que a estrutura de segurança e o índice contra
    # duplicidade existam antes de realizar a operação.
    criar_tabelas_seguranca()

    # --------------------------------------------------------
    # NORMALIZAR E VALIDAR NOME
    # --------------------------------------------------------

    nome = str(nome or "").strip()

    if not nome:
        raise ValueError(
            "Informe o nome completo."
        )

    # --------------------------------------------------------
    # NORMALIZAR E VALIDAR E-MAIL
    # --------------------------------------------------------
    #
    # lower() evita que o mesmo endereço seja tratado como
    # diferente apenas por letras maiúsculas/minúsculas.
    #
    # strip() remove espaços acidentais no início/fim.
    # --------------------------------------------------------

    email = str(email or "").strip().lower()

    if not email:
        raise ValueError(
            "Informe o e-mail."
        )

    # Esta validação é propositalmente simples.
    # O objetivo aqui é bloquear erros óbvios de digitação,
    # sem tentar reproduzir toda a especificação de e-mails.
    if (
        "@" not in email
        or email.startswith("@")
        or email.endswith("@")
    ):
        raise ValueError(
            "Informe um e-mail válido."
        )

    dominio = email.split("@", 1)[1]

    if "." not in dominio:
        raise ValueError(
            "Informe um e-mail válido."
        )

    # --------------------------------------------------------
    # NORMALIZAR CAMPOS OPCIONAIS
    # --------------------------------------------------------
    #
    # Se vierem vazios, salvamos None no SQLite em vez de
    # uma string vazia.
    # --------------------------------------------------------

    empresa = str(empresa or "").strip() or None
    cargo = str(cargo or "").strip() or None
    setor = str(setor or "").strip() or None

    # --------------------------------------------------------
    # VALIDAR JUSTIFICATIVA
    # --------------------------------------------------------

    justificativa = str(
        justificativa or ""
    ).strip()

    if not justificativa:
        raise ValueError(
            "Informe o motivo da solicitação de acesso."
        )

    # --------------------------------------------------------
    # ABRIR TRANSAÇÃO
    # --------------------------------------------------------

    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:

        # ----------------------------------------------------
        # VERIFICAR SE JÁ EXISTE SOLICITAÇÃO PENDENTE
        # ----------------------------------------------------
        #
        # Fazemos a verificação aqui para entregar uma mensagem
        # amigável ao usuário.
        #
        # O índice UNIQUE do banco continua sendo a proteção
        # definitiva contra duplicidade.
        # ----------------------------------------------------

        cursor.execute("""
            SELECT id
            FROM solicitacoes_acesso
            WHERE LOWER(TRIM(email)) = ?
              AND status = 'PENDENTE'
            LIMIT 1
        """, (
            email,
        ))

        if cursor.fetchone() is not None:
            raise ValueError(
                "Já existe uma solicitação de acesso pendente "
                "para este e-mail."
            )

        # ----------------------------------------------------
        # REGISTRAR DATA DA SOLICITAÇÃO
        # ----------------------------------------------------

        agora = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        # ----------------------------------------------------
        # INSERIR SOLICITAÇÃO
        # ----------------------------------------------------
        #
        # Não precisamos informar status porque a própria
        # tabela possui DEFAULT 'PENDENTE'.
        #
        # data_analise, analisado_por e motivo_rejeicao também
        # permanecem vazios enquanto o pedido não for analisado.
        # ----------------------------------------------------

        cursor.execute("""
            INSERT INTO solicitacoes_acesso (
                nome,
                email,
                empresa,
                cargo,
                setor,
                justificativa,
                data_solicitacao
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            nome,
            email,
            empresa,
            cargo,
            setor,
            justificativa,
            agora
        ))

        solicitacao_id = cursor.lastrowid

        conexao.commit()

        # ----------------------------------------------------
        # RETORNAR O REGISTRO CRIADO
        # ----------------------------------------------------

        cursor.execute("""
            SELECT *
            FROM solicitacoes_acesso
            WHERE id = ?
            LIMIT 1
        """, (
            solicitacao_id,
        ))

        resultado = cursor.fetchone()

        return dict(resultado)

    except sqlite3.IntegrityError as erro:

        conexao.rollback()

        # Mesmo que duas requisições ocorram praticamente ao
        # mesmo tempo, o índice UNIQUE impede duas pendências.
        if (
            "idx_solicitacao_acesso_email_pendente"
            in str(erro)
            or "UNIQUE constraint failed"
            in str(erro)
        ):
            raise ValueError(
                "Já existe uma solicitação de acesso pendente "
                "para este e-mail."
            ) from erro

        raise

    except Exception:

        conexao.rollback()
        raise

    finally:

        conexao.close()


def consultar_solicitacoes_acesso(
    status=None
):
    """
    Retorna as solicitações de acesso cadastradas.

    Se status não for informado:
        retorna todas.

    Se status for informado:
        retorna somente aquele status.

    Exemplos futuros:

        consultar_solicitacoes_acesso()

        consultar_solicitacoes_acesso(
            "PENDENTE"
        )

    Esta função será utilizada posteriormente pela tela
    administrativa de análise de acessos.
    """

    criar_tabelas_seguranca()

    conexao = conectar_banco()
    cursor = conexao.cursor()

    # --------------------------------------------------------
    # CONSULTAR TODAS AS SOLICITAÇÕES
    # --------------------------------------------------------

    if status is None:

        cursor.execute("""
            SELECT *
            FROM solicitacoes_acesso
            ORDER BY data_solicitacao DESC, id DESC
        """)

    # --------------------------------------------------------
    # CONSULTAR POR STATUS
    # --------------------------------------------------------

    else:

        status = str(status).strip().upper()

        cursor.execute("""
            SELECT *
            FROM solicitacoes_acesso
            WHERE status = ?
            ORDER BY data_solicitacao DESC, id DESC
        """, (
            status,
        ))

    registros = cursor.fetchall()

    conexao.close()

    return [
        dict(registro)
        for registro in registros
    ]



# ============================================================
# AUTENTICAÇÃO - SENHAS
# ============================================================
#
# O DashPy nunca deve armazenar a senha original do usuário.
#
# O que fica no banco é somente um HASH produzido pelo Argon2.
#
# Exemplo conceitual:
#
#     senha digitada:
#         MinhaSenhaSegura
#
#     valor salvo no banco:
#         $argon2id$v=19$...
#
# Não é necessário "descriptografar" a senha.
# No login, verificamos se a senha digitada corresponde ao hash.
# ============================================================


# O PasswordHasher usa Argon2id por padrão.
# Mantemos uma única instância para centralizar a configuração.
_password_hasher = PasswordHasher()


def gerar_hash_senha(senha):
    """
    Recebe uma senha em texto e devolve somente o hash seguro.

    A senha original NÃO é armazenada.

    Neste primeiro momento exigimos pelo menos 10 caracteres.
    Regras mais sofisticadas poderão ser adicionadas depois
    sem alterar a estrutura da tabela usuarios.
    """

    senha = str(senha or "")

    if len(senha) < 10:
        raise ValueError(
            "A senha deve possuir pelo menos 10 caracteres."
        )

    return _password_hasher.hash(senha)


def verificar_senha(senha, senha_hash):
    """
    Confere se uma senha corresponde ao hash armazenado.

    Retorna:

        True  -> senha correta
        False -> senha incorreta ou hash inválido

    A função não revela qual era a senha original.
    """

    senha = str(senha or "")
    senha_hash = str(senha_hash or "")

    if not senha or not senha_hash:
        return False

    try:
        return _password_hasher.verify(
            senha_hash,
            senha
        )

    except (VerifyMismatchError, VerificationError):
        return False

    except Exception:
        # Em autenticação, um hash inesperadamente inválido
        # deve resultar em falha de login, não em liberação.
        return False


# ============================================================
# BOOTSTRAP - PRIMEIRO USUÁRIO ADMINISTRATIVO
# ============================================================
#
# Existe um problema de "ovo e galinha":
#
# para aprovar usuários precisamos de alguém autorizado,
# mas em uma instalação nova ainda não existe nenhum usuário.
#
# Esta função resolve SOMENTE esse primeiro cadastro.
#
# REGRA DE SEGURANÇA:
#
# ela funciona apenas quando a tabela usuarios está vazia.
#
# Assim que o primeiro usuário existir, esta rotina deixa de
# poder criar novos usuários.
#
# Não existe usuário padrão.
# Não existe senha padrão.
# Não existe admin/admin123 gravado no código.
# ============================================================


def criar_primeiro_usuario_administrativo(
    nome,
    email,
    senha,
    empresa=None,
    cargo=None,
    setor=None,
    grupo_nome="Administrador"
):
    """
    Cria o primeiro usuário do DashPy e o associa ao grupo
    administrativo informado.

    Esta função só pode ser usada se ainda NÃO existir nenhum
    registro na tabela usuarios.

    O grupo precisa existir previamente no banco.

    Retorna os dados públicos do usuário criado.
    O hash da senha não é retornado.
    """

    # Garante que as tabelas de segurança existam.
    criar_tabelas_seguranca()

    # --------------------------------------------------------
    # NORMALIZAR DADOS
    # --------------------------------------------------------

    nome = str(nome or "").strip()
    email = str(email or "").strip().lower()

    empresa = str(empresa or "").strip() or None
    cargo = str(cargo or "").strip() or None
    setor = str(setor or "").strip() or None

    grupo_nome = str(grupo_nome or "").strip()

    # --------------------------------------------------------
    # VALIDAR CAMPOS PRINCIPAIS
    # --------------------------------------------------------

    if not nome:
        raise ValueError(
            "Informe o nome do primeiro usuário."
        )

    if (
        not email
        or "@" not in email
        or email.startswith("@")
        or email.endswith("@")
    ):
        raise ValueError(
            "Informe um e-mail válido."
        )

    dominio = email.split("@", 1)[1]

    if "." not in dominio:
        raise ValueError(
            "Informe um e-mail válido."
        )

    if not grupo_nome:
        raise ValueError(
            "Informe o grupo que receberá o primeiro usuário."
        )

    # Gera o hash ANTES de abrir a transação.
    # A senha em texto não será enviada ao SQLite.
    senha_hash = gerar_hash_senha(senha)

    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:

        # ----------------------------------------------------
        # GARANTIR QUE AINDA NÃO EXISTE USUÁRIO
        # ----------------------------------------------------

        cursor.execute("""
            SELECT COUNT(*) AS quantidade
            FROM usuarios
        """)

        quantidade = cursor.fetchone()["quantidade"]

        if quantidade > 0:
            raise ValueError(
                "O primeiro usuário já foi criado. "
                "O bootstrap administrativo está bloqueado."
            )

        # ----------------------------------------------------
        # LOCALIZAR O GRUPO ADMINISTRATIVO
        # --------------------------------------------------------
        #
        # O nome é parâmetro da função e não uma regra de
        # autorização espalhada pelo sistema.
        #
        # Depois do bootstrap, o sistema continuará tomando
        # decisões por PERMISSÕES, e não pelo nome do grupo.
        # ----------------------------------------------------

        cursor.execute("""
            SELECT id, nome, ativo
            FROM grupos
            WHERE LOWER(TRIM(nome)) = LOWER(TRIM(?))
            LIMIT 1
        """, (
            grupo_nome,
        ))

        grupo = cursor.fetchone()

        if grupo is None:
            raise ValueError(
                f"O grupo '{grupo_nome}' não existe."
            )

        if not grupo["ativo"]:
            raise ValueError(
                f"O grupo '{grupo_nome}' está inativo."
            )

        # ----------------------------------------------------
        # CRIAR USUÁRIO
        # ----------------------------------------------------

        agora = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        cursor.execute("""
            INSERT INTO usuarios (
                nome,
                email,
                empresa,
                cargo,
                setor,
                senha_hash,
                ativo,
                data_cadastro
            )
            VALUES (?, ?, ?, ?, ?, ?, 1, ?)
        """, (
            nome,
            email,
            empresa,
            cargo,
            setor,
            senha_hash,
            agora
        ))

        usuario_id = cursor.lastrowid

        # ----------------------------------------------------
        # ASSOCIAR AO GRUPO
        # ----------------------------------------------------

        cursor.execute("""
            INSERT INTO usuario_grupo (
                usuario_id,
                grupo_id
            )
            VALUES (?, ?)
        """, (
            usuario_id,
            grupo["id"]
        ))

        # Usuário + associação ao grupo fazem parte da mesma
        # transação. Ou os dois são gravados, ou nenhum deles.
        conexao.commit()

        # ----------------------------------------------------
        # RETORNAR SOMENTE DADOS PÚBLICOS
        # --------------------------------------------------------
        #
        # senha_hash fica propositalmente fora do SELECT.
        # ----------------------------------------------------

        cursor.execute("""
            SELECT
                id,
                nome,
                email,
                empresa,
                cargo,
                setor,
                ativo,
                data_cadastro
            FROM usuarios
            WHERE id = ?
        """, (
            usuario_id,
        ))

        usuario = dict(cursor.fetchone())

        usuario["grupo_inicial"] = grupo["nome"]

        return usuario

    except sqlite3.IntegrityError as erro:

        conexao.rollback()

        if "usuarios.email" in str(erro):
            raise ValueError(
                "Já existe um usuário cadastrado com este e-mail."
            ) from erro

        raise

    except Exception:

        conexao.rollback()
        raise

    finally:

        conexao.close()


# ============================================================
# USUÁRIOS <-> GRUPOS
# ============================================================


def adicionar_usuario_grupo(usuario_id, grupo_id):
    """
    Associa um usuário a um grupo.

    A associação usa INSERT OR IGNORE porque a chave primária
    composta (usuario_id, grupo_id) já impede duplicidade.

    Retorna True quando a operação termina corretamente.
    """

    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        # Confirma que o usuário existe.
        cursor.execute("""
            SELECT id
            FROM usuarios
            WHERE id = ?
            LIMIT 1
        """, (usuario_id,))

        if cursor.fetchone() is None:
            raise ValueError("Usuário não encontrado.")

        # Confirma que o grupo existe e está ativo.
        cursor.execute("""
            SELECT id, ativo
            FROM grupos
            WHERE id = ?
            LIMIT 1
        """, (grupo_id,))

        grupo = cursor.fetchone()

        if grupo is None:
            raise ValueError("Grupo não encontrado.")

        if not grupo["ativo"]:
            raise ValueError(
                "Não é possível associar um usuário a um grupo inativo."
            )

        cursor.execute("""
            INSERT OR IGNORE INTO usuario_grupo (
                usuario_id,
                grupo_id
            )
            VALUES (?, ?)
        """, (
            usuario_id,
            grupo_id
        ))

        conexao.commit()
        return True

    except Exception:
        conexao.rollback()
        raise

    finally:
        conexao.close()


def remover_usuario_grupo(usuario_id, grupo_id):
    """
    Remove a associação entre um usuário e um grupo.

    A função remove somente o vínculo.
    O usuário e o grupo continuam existindo.
    """

    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute("""
            DELETE FROM usuario_grupo
            WHERE usuario_id = ?
              AND grupo_id = ?
        """, (
            usuario_id,
            grupo_id
        ))

        removidos = cursor.rowcount

        conexao.commit()

        return removidos > 0

    except Exception:
        conexao.rollback()
        raise

    finally:
        conexao.close()


def consultar_grupos_usuario(usuario_id, somente_ativos=True):
    """
    Retorna os grupos associados a um usuário.

    Por padrão, retorna apenas grupos ativos.

    Isso é importante porque um grupo desativado não deve
    continuar concedendo acesso ao sistema.
    """

    conexao = conectar_banco()
    cursor = conexao.cursor()

    if somente_ativos:
        cursor.execute("""
            SELECT
                g.id,
                g.nome,
                g.descricao,
                g.ativo,
                g.data_cadastro
            FROM grupos g
            INNER JOIN usuario_grupo ug
                ON ug.grupo_id = g.id
            WHERE ug.usuario_id = ?
              AND g.ativo = 1
            ORDER BY g.nome
        """, (usuario_id,))

    else:
        cursor.execute("""
            SELECT
                g.id,
                g.nome,
                g.descricao,
                g.ativo,
                g.data_cadastro
            FROM grupos g
            INNER JOIN usuario_grupo ug
                ON ug.grupo_id = g.id
            WHERE ug.usuario_id = ?
            ORDER BY g.nome
        """, (usuario_id,))

    registros = cursor.fetchall()
    conexao.close()

    return [
        dict(registro)
        for registro in registros
    ]


# ============================================================
# PERMISSÕES EFETIVAS DO USUÁRIO
# ============================================================


def consultar_permissoes_usuario(usuario_id):
    """
    Retorna as permissões efetivas de um usuário.

    As permissões são a UNIÃO das permissões recebidas por
    todos os grupos ATIVOS aos quais o usuário pertence.

    DISTINCT evita repetir uma permissão quando dois grupos
    diferentes concedem a mesma ação.

    Usuário inativo não recebe permissões.
    """

    conexao = conectar_banco()
    cursor = conexao.cursor()

    cursor.execute("""
        SELECT
            u.id,
            u.ativo
        FROM usuarios u
        WHERE u.id = ?
        LIMIT 1
    """, (usuario_id,))

    usuario = cursor.fetchone()

    if usuario is None:
        conexao.close()
        return []

    if not usuario["ativo"]:
        conexao.close()
        return []

    cursor.execute("""
        SELECT DISTINCT
            p.id,
            p.codigo,
            p.descricao
        FROM permissoes p

        INNER JOIN grupo_permissao gp
            ON gp.permissao_id = p.id

        INNER JOIN grupos g
            ON g.id = gp.grupo_id

        INNER JOIN usuario_grupo ug
            ON ug.grupo_id = g.id

        WHERE ug.usuario_id = ?
          AND g.ativo = 1

        ORDER BY p.codigo
    """, (usuario_id,))

    registros = cursor.fetchall()
    conexao.close()

    return [
        dict(registro)
        for registro in registros
    ]


def tem_permissao(usuario_id, codigo_permissao):
    """
    Verifica se um usuário possui uma permissão específica.

    Exemplo:

        tem_permissao(
            usuario_id,
            "viagens.corrigir"
        )

    Retorna True ou False.

    IMPORTANTE:
    nenhuma decisão é tomada pelo nome do grupo.
    """

    codigo_permissao = str(
        codigo_permissao or ""
    ).strip()

    if not codigo_permissao:
        return False

    conexao = conectar_banco()
    cursor = conexao.cursor()

    cursor.execute("""
        SELECT 1
        FROM usuarios u

        INNER JOIN usuario_grupo ug
            ON ug.usuario_id = u.id

        INNER JOIN grupos g
            ON g.id = ug.grupo_id

        INNER JOIN grupo_permissao gp
            ON gp.grupo_id = g.id

        INNER JOIN permissoes p
            ON p.id = gp.permissao_id

        WHERE u.id = ?
          AND u.ativo = 1
          AND g.ativo = 1
          AND p.codigo = ?

        LIMIT 1
    """, (
        usuario_id,
        codigo_permissao
    ))

    possui = cursor.fetchone() is not None

    conexao.close()

    return possui


# ============================================================
# AUTENTICAÇÃO DE USUÁRIO
# ============================================================


def autenticar_usuario(email, senha):
    """
    Autentica um usuário por e-mail e senha.

    Para o login ser aceito:

    1. o e-mail precisa existir;
    2. o usuário precisa estar ativo;
    3. a senha precisa corresponder ao hash Argon2 armazenado.

    Por segurança, falhas de e-mail e senha retornam None.
    A interface poderá exibir uma mensagem genérica como:

        "E-mail ou senha inválidos."

    Isso evita revelar se determinado e-mail está cadastrado.

    Quando o login é válido, retorna somente dados públicos
    do usuário. O senha_hash nunca é devolvido.
    """

    email = str(email or "").strip().lower()
    senha = str(senha or "")

    if not email or not senha:
        return None

    conexao = conectar_banco()
    cursor = conexao.cursor()

    cursor.execute("""
        SELECT
            id,
            nome,
            email,
            empresa,
            cargo,
            setor,
            senha_hash,
            ativo,
            data_cadastro
        FROM usuarios
        WHERE LOWER(TRIM(email)) = ?
        LIMIT 1
    """, (
        email,
    ))

    registro = cursor.fetchone()
    conexao.close()

    # Não diferencia publicamente "usuário inexistente",
    # "usuário inativo" ou "senha incorreta".
    if registro is None:
        return None

    if not registro["ativo"]:
        return None

    if not verificar_senha(
        senha,
        registro["senha_hash"]
    ):
        return None

    # O hash é necessário somente para a verificação.
    # Ele não deve sair da camada de banco/autenticação.
    usuario = {
        "id": registro["id"],
        "nome": registro["nome"],
        "email": registro["email"],
        "empresa": registro["empresa"],
        "cargo": registro["cargo"],
        "setor": registro["setor"],
        "ativo": registro["ativo"],
        "data_cadastro": registro["data_cadastro"]
    }

    return usuario


# ============================================================
# GOVERNANÇA - INCONSISTÊNCIAS E SOLICITAÇÕES DE CORREÇÃO
# ============================================================


def criar_tabelas_governanca():
    """
    Cria as estruturas persistentes usadas para tratar divergências
    operacionais e propostas de correção.

    IMPORTANTE:
    - uma inconsistência não altera a viagem;
    - uma solicitação PENDENTE não altera a viagem;
    - confirmação humana encerra somente aquela ocorrência;
    - aprovação/rejeição será tratada em etapa própria;
    - não apagamos o histórico para "corrigir" uma decisão.
    """

    criar_tabelas_seguranca()
    criar_tabela_viagens()

    conexao = conectar_banco()
    cursor = conexao.cursor()

    # --------------------------------------------------------
    # INCONSISTÊNCIAS
    # --------------------------------------------------------
    #
    # regra_codigo guarda a regra técnica que detectou o problema.
    # mensagem guarda a explicação amigável apresentada ao usuário.
    #
    # chave_ocorrencia permite impedir que o mesmo problema seja
    # recriado repetidamente a cada atualização do dashboard.
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inconsistencias (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            viagem_id INTEGER,
            codigo_viagem TEXT,
            placa TEXT,
            balsa TEXT,

            regra_codigo TEXT NOT NULL,
            mensagem TEXT NOT NULL,
            chave_ocorrencia TEXT NOT NULL UNIQUE,

            status TEXT NOT NULL DEFAULT 'ABERTA',

            data_deteccao TEXT NOT NULL,

            data_resolucao TEXT,
            resolvida_por INTEGER,
            observacao_resolucao TEXT,

            FOREIGN KEY (viagem_id)
                REFERENCES viagens(id),

            FOREIGN KEY (resolvida_por)
                REFERENCES usuarios(id)
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS
            idx_inconsistencias_status
        ON inconsistencias (status)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS
            idx_inconsistencias_viagem
        ON inconsistencias (viagem_id)
    """)

    # --------------------------------------------------------
    # SOLICITAÇÕES DE CORREÇÃO
    # --------------------------------------------------------
    #
    # Nesta primeira estrutura, a correção proposta é de datas de
    # saída/chegada porque já possuímos corrigir_datas_viagem().
    #
    # Os valores oficiais permanecem em viagens até uma aprovação
    # futura aplicar a solicitação.
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS solicitacoes_correcao (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            inconsistencia_id INTEGER,
            viagem_id INTEGER NOT NULL,
            codigo_viagem TEXT NOT NULL,
            placa TEXT NOT NULL,

            data_inicio_atual TEXT,
            data_fim_atual TEXT,

            nova_data_inicio TEXT,
            nova_data_fim TEXT,

            motivo TEXT NOT NULL,

            status TEXT NOT NULL DEFAULT 'PENDENTE',

            solicitado_por INTEGER NOT NULL,
            data_solicitacao TEXT NOT NULL,

            analisado_por INTEGER,
            data_analise TEXT,
            motivo_decisao TEXT,

            FOREIGN KEY (inconsistencia_id)
                REFERENCES inconsistencias(id),

            FOREIGN KEY (viagem_id)
                REFERENCES viagens(id),

            FOREIGN KEY (solicitado_por)
                REFERENCES usuarios(id),

            FOREIGN KEY (analisado_por)
                REFERENCES usuarios(id)
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS
            idx_solicitacoes_correcao_status
        ON solicitacoes_correcao (status)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS
            idx_solicitacoes_correcao_viagem
        ON solicitacoes_correcao (viagem_id)
    """)

    # Uma mesma viagem pode receber novas solicitações no futuro,
    # mas não deve acumular duas propostas PENDENTES simultâneas.
    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS
            idx_correcao_pendente_viagem
        ON solicitacoes_correcao (viagem_id)
        WHERE status = 'PENDENTE'
    """)

    conexao.commit()
    conexao.close()


def registrar_inconsistencia(
    viagem_id,
    regra_codigo,
    mensagem,
    chave_ocorrencia
):
    """
    Registra uma inconsistência sem alterar a viagem.

    Se a mesma chave_ocorrencia já existir, retorna o registro
    existente. Assim o refresh do dashboard não cria duplicatas.
    """

    criar_tabelas_governanca()

    regra_codigo = str(regra_codigo or "").strip().upper()
    mensagem = str(mensagem or "").strip()
    chave_ocorrencia = str(chave_ocorrencia or "").strip()

    if not regra_codigo:
        raise ValueError("Informe o código da regra da inconsistência.")

    if not mensagem:
        raise ValueError("Informe a mensagem da inconsistência.")

    if not chave_ocorrencia:
        raise ValueError("Informe a chave da ocorrência.")

    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute("""
            SELECT *
            FROM viagens
            WHERE id = ?
            LIMIT 1
        """, (viagem_id,))

        viagem = cursor.fetchone()

        if viagem is None:
            raise ValueError("Viagem não encontrada.")

        viagem = dict(viagem)

        cursor.execute("""
            INSERT OR IGNORE INTO inconsistencias (
                viagem_id,
                codigo_viagem,
                placa,
                balsa,
                regra_codigo,
                mensagem,
                chave_ocorrencia,
                status,
                data_deteccao
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 'ABERTA', ?)
        """, (
            viagem["id"],
            viagem["codigo_viagem"],
            viagem["placa"],
            viagem["balsa"],
            regra_codigo,
            mensagem,
            chave_ocorrencia,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))

        conexao.commit()

        cursor.execute("""
            SELECT *
            FROM inconsistencias
            WHERE chave_ocorrencia = ?
            LIMIT 1
        """, (chave_ocorrencia,))

        resultado = cursor.fetchone()
        return dict(resultado)

    except Exception:
        conexao.rollback()
        raise

    finally:
        conexao.close()


def consultar_inconsistencias(status=None, viagem_id=None):
    """
    Consulta inconsistências.

    status:
        None -> todas
        'ABERTA', 'CONFIRMADA', 'CORRIGIDA' etc.

    viagem_id:
        opcionalmente restringe a uma viagem.
    """

    criar_tabelas_governanca()

    conexao = conectar_banco()
    cursor = conexao.cursor()

    condicoes = []
    parametros = []

    if status is not None:
        condicoes.append("status = ?")
        parametros.append(str(status).strip().upper())

    if viagem_id is not None:
        condicoes.append("viagem_id = ?")
        parametros.append(viagem_id)

    where = ""

    if condicoes:
        where = " WHERE " + " AND ".join(condicoes)

    cursor.execute(f"""
        SELECT *
        FROM inconsistencias
        {where}
        ORDER BY
            CASE WHEN status = 'ABERTA' THEN 0 ELSE 1 END,
            data_deteccao DESC,
            id DESC
    """, parametros)

    registros = cursor.fetchall()
    conexao.close()

    return [dict(registro) for registro in registros]


def confirmar_inconsistencia(
    inconsistencia_id,
    usuario_id,
    observacao
):
    """
    Confirma que os dados atuais daquela ocorrência foram conferidos.

    Esta função NÃO altera a viagem.

    Exige a permissão inconsistencias.confirmar e registra quem
    realizou a confirmação.
    """

    if not tem_permissao(
        usuario_id,
        "inconsistencias.confirmar"
    ):
        raise PermissionError(
            "Usuário sem permissão para confirmar inconsistências."
        )

    observacao = str(observacao or "").strip()

    if not observacao:
        raise ValueError(
            "Informe uma observação para a confirmação."
        )

    criar_tabelas_governanca()

    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute("""
            SELECT *
            FROM inconsistencias
            WHERE id = ?
            LIMIT 1
        """, (inconsistencia_id,))

        inconsistencia = cursor.fetchone()

        if inconsistencia is None:
            raise ValueError("Inconsistência não encontrada.")

        if inconsistencia["status"] != "ABERTA":
            raise ValueError(
                "Esta inconsistência já foi tratada."
            )

        agora = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        cursor.execute("""
            UPDATE inconsistencias
            SET
                status = 'CONFIRMADA',
                data_resolucao = ?,
                resolvida_por = ?,
                observacao_resolucao = ?
            WHERE id = ?
              AND status = 'ABERTA'
        """, (
            agora,
            usuario_id,
            observacao,
            inconsistencia_id
        ))

        if cursor.rowcount != 1:
            raise ValueError(
                "A inconsistência foi alterada por outro usuário."
            )

        conexao.commit()

        cursor.execute("""
            SELECT *
            FROM inconsistencias
            WHERE id = ?
        """, (inconsistencia_id,))

        return dict(cursor.fetchone())

    except Exception:
        conexao.rollback()
        raise

    finally:
        conexao.close()


def criar_solicitacao_correcao(
    viagem_id,
    usuario_id,
    nova_data_inicio,
    nova_data_fim,
    motivo,
    inconsistencia_id=None
):
    """
    Cria uma proposta de correção sem modificar a viagem oficial.

    Exige correcoes.solicitar.

    A solicitação guarda uma fotografia das datas atuais para que,
    na etapa de aprovação, possamos detectar se a viagem mudou
    enquanto o pedido aguardava análise.
    """

    if not tem_permissao(
        usuario_id,
        "correcoes.solicitar"
    ):
        raise PermissionError(
            "Usuário sem permissão para solicitar correções."
        )

    motivo = str(motivo or "").strip()

    if not motivo:
        raise ValueError(
            "Informe o motivo da solicitação de correção."
        )

    nova_data_inicio = formatar_data_banco(
        nova_data_inicio
    )

    nova_data_fim = formatar_data_banco(
        nova_data_fim
    )

    if (
        nova_data_inicio is None
        and nova_data_fim is not None
    ):
        raise ValueError(
            "Uma viagem não pode ter chegada sem saída."
        )

    if nova_data_inicio and nova_data_fim:
        inicio = datetime.strptime(
            nova_data_inicio,
            "%Y-%m-%d %H:%M:%S"
        )
        fim = datetime.strptime(
            nova_data_fim,
            "%Y-%m-%d %H:%M:%S"
        )

        if fim < inicio:
            raise ValueError(
                "A chegada não pode ser anterior à saída."
            )

    criar_tabelas_governanca()

    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute("""
            SELECT *
            FROM viagens
            WHERE id = ?
            LIMIT 1
        """, (viagem_id,))

        viagem = cursor.fetchone()

        if viagem is None:
            raise ValueError("Viagem não encontrada.")

        viagem = dict(viagem)

        if (
            nova_data_inicio == viagem["data_inicio"]
            and nova_data_fim == viagem["data_fim"]
        ):
            raise ValueError(
                "A solicitação não contém nenhuma alteração."
            )

        if inconsistencia_id is not None:
            cursor.execute("""
                SELECT *
                FROM inconsistencias
                WHERE id = ?
                LIMIT 1
            """, (inconsistencia_id,))

            inconsistencia = cursor.fetchone()

            if inconsistencia is None:
                raise ValueError(
                    "Inconsistência não encontrada."
                )

            if inconsistencia["viagem_id"] != viagem_id:
                raise ValueError(
                    "A inconsistência não pertence a esta viagem."
                )

        agora = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        try:
            cursor.execute("""
                INSERT INTO solicitacoes_correcao (
                    inconsistencia_id,
                    viagem_id,
                    codigo_viagem,
                    placa,
                    data_inicio_atual,
                    data_fim_atual,
                    nova_data_inicio,
                    nova_data_fim,
                    motivo,
                    status,
                    solicitado_por,
                    data_solicitacao
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDENTE', ?, ?)
            """, (
                inconsistencia_id,
                viagem["id"],
                viagem["codigo_viagem"],
                viagem["placa"],
                viagem["data_inicio"],
                viagem["data_fim"],
                nova_data_inicio,
                nova_data_fim,
                motivo,
                usuario_id,
                agora
            ))

        except sqlite3.IntegrityError as erro:
            if "idx_correcao_pendente_viagem" in str(erro):
                raise ValueError(
                    "Já existe uma solicitação de correção "
                    "pendente para esta viagem."
                ) from erro

            # SQLite normalmente informa a coluna e não o nome
            # do índice para esta violação.
            cursor.execute("""
                SELECT id
                FROM solicitacoes_correcao
                WHERE viagem_id = ?
                  AND status = 'PENDENTE'
                LIMIT 1
            """, (viagem_id,))

            if cursor.fetchone() is not None:
                raise ValueError(
                    "Já existe uma solicitação de correção "
                    "pendente para esta viagem."
                ) from erro

            raise

        solicitacao_id = cursor.lastrowid
        conexao.commit()

        cursor.execute("""
            SELECT *
            FROM solicitacoes_correcao
            WHERE id = ?
        """, (solicitacao_id,))

        return dict(cursor.fetchone())

    except Exception:
        conexao.rollback()
        raise

    finally:
        conexao.close()


def consultar_solicitacoes_correcao(
    status=None,
    viagem_id=None
):
    """
    Consulta propostas de correção sem alterar dados operacionais.
    """

    criar_tabelas_governanca()

    conexao = conectar_banco()
    cursor = conexao.cursor()

    condicoes = []
    parametros = []

    if status is not None:
        condicoes.append("sc.status = ?")
        parametros.append(str(status).strip().upper())

    if viagem_id is not None:
        condicoes.append("sc.viagem_id = ?")
        parametros.append(viagem_id)

    where = ""

    if condicoes:
        where = " WHERE " + " AND ".join(condicoes)

    cursor.execute(f"""
        SELECT
            sc.*,
            u.nome AS solicitado_por_nome
        FROM solicitacoes_correcao sc
        INNER JOIN usuarios u
            ON u.id = sc.solicitado_por
        {where}
        ORDER BY
            CASE WHEN sc.status = 'PENDENTE' THEN 0 ELSE 1 END,
            sc.data_solicitacao DESC,
            sc.id DESC
    """, parametros)

    registros = cursor.fetchall()
    conexao.close()

    return [dict(registro) for registro in registros]


# ============================================================
# DELETE DE EVENTOS (modo edição do Administrador)
# ============================================================
#
# Deletar um evento da tabela area_restrita é uma operação
# sensível: o evento sai do banco, mas uma cópia integral
# é preservada em ajustes_viagem para auditoria.
#
# Exige a permissão viagens.corrigir (Administrador).
# ============================================================


def deletar_evento(
    evento_id,
    usuario_id,
    motivo
):
    """
    Remove um evento da tabela area_restrita e registra
    uma cópia na auditoria (ajustes_viagem).

    Parâmetros:
        evento_id  -> id do evento em area_restrita
        usuario_id -> id do usuário que está deletando
        motivo     -> justificativa obrigatória

    Retorna os dados do evento deletado (antes da remoção).
    """

    # --------------------------------------------------------
    # VERIFICAR PERMISSÃO
    # --------------------------------------------------------

    if not tem_permissao(usuario_id, "viagens.corrigir"):
        raise PermissionError(
            "Usuário sem permissão para deletar eventos."
        )

    # --------------------------------------------------------
    # VALIDAR MOTIVO
    # --------------------------------------------------------

    motivo = str(motivo or "").strip()

    if not motivo:
        raise ValueError(
            "Informe o motivo da remoção do evento."
        )

    criar_tabela_area_restrita()
    criar_tabela_ajustes()

    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        # ----------------------------------------------------
        # BUSCAR EVENTO
        # ----------------------------------------------------

        cursor.execute("""
            SELECT *
            FROM area_restrita
            WHERE id = ?
            LIMIT 1
        """, (evento_id,))

        evento = cursor.fetchone()

        if evento is None:
            raise ValueError("Evento não encontrado.")

        evento = dict(evento)

        # ----------------------------------------------------
        # REGISTRAR NA AUDITORIA
        # ----------------------------------------------------

        # Descrição curta para caber no campo tipo_ajuste
        descricao = (
            f"Delete de evento: "
            f"{evento.get('evento')} @ {evento.get('area')} "
            f"em {evento.get('dataGPS')}"
        )

        cursor.execute("""
            INSERT INTO ajustes_viagem (
                placa,
                codigo_viagem,
                tipo_ajuste,
                valor_anterior,
                valor_novo,
                motivo,
                data_ajuste
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            evento.get("placa"),
            None,                      # evento não tem código de viagem
            descricao,
            (
                f"evento={evento.get('evento')} | "
                f"area={evento.get('area')} | "
                f"dataGPS={evento.get('dataGPS')}"
            ),
            None,                      # sem valor novo (é exclusão)
            motivo,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))

        # ----------------------------------------------------
        # DELETAR EVENTO
        # ----------------------------------------------------

        cursor.execute("""
            DELETE FROM area_restrita
            WHERE id = ?
        """, (evento_id,))

        conexao.commit()

        return evento

    except Exception:
        conexao.rollback()
        raise

    finally:
        conexao.close()





# ============================================================
# APROVAÇÃO / REJEIÇÃO DE SOLICITAÇÕES DE ACESSO
# ============================================================

def aprovar_solicitacao_acesso(
    solicitacao_id,
    usuario_id,
    grupo_id,
    senha_provisoria,
    empresa=None,
    cargo=None,
    setor=None
):
    """
    Aprova uma solicitação pendente:
    - cria o usuário em usuarios com o hash da senha provisória;
    - associa ao grupo escolhido;
    - marca a solicitação como APROVADA.

    Exige a permissão 'acessos.aprovar'.
    """

    if not tem_permissao(usuario_id, "acessos.aprovar"):
        raise PermissionError(
            "Usuário sem permissão para aprovar solicitações."
        )

    senha_provisoria = str(senha_provisoria or "")
    if len(senha_provisoria) < 10:
        raise ValueError(
            "A senha provisória deve ter pelo menos 10 caracteres."
        )

    criar_tabelas_seguranca()
    cadastrar_permissoes_sistema()

    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        # ----------------------------------------------------
        # 1. Buscar solicitação
        # ----------------------------------------------------

        cursor.execute("""
            SELECT * FROM solicitacoes_acesso
            WHERE id = ? LIMIT 1
        """, (solicitacao_id,))

        s = cursor.fetchone()

        if s is None:
            raise ValueError("Solicitação não encontrada.")

        if s["status"] != "PENDENTE":
            raise ValueError(
                f"Solicitação já está com status {s['status']}."
            )

        # ----------------------------------------------------
        # 2. Verificar se já existe usuário com esse e-mail
        # ----------------------------------------------------

        cursor.execute("""
            SELECT id FROM usuarios
            WHERE LOWER(TRIM(email)) = LOWER(TRIM(?))
            LIMIT 1
        """, (s["email"],))

        if cursor.fetchone() is not None:
            raise ValueError(
                "Já existe um usuário cadastrado com este e-mail."
            )

        # ----------------------------------------------------
        # 3. Verificar grupo
        # ----------------------------------------------------

        cursor.execute("""
            SELECT id, ativo FROM grupos WHERE id = ? LIMIT 1
        """, (grupo_id,))

        grupo = cursor.fetchone()

        if grupo is None:
            raise ValueError("Grupo não encontrado.")

        if not grupo["ativo"]:
            raise ValueError("O grupo escolhido está inativo.")

        # ----------------------------------------------------
        # 4. Criar usuário
        # ----------------------------------------------------

        agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        senha_hash = gerar_hash_senha(senha_provisoria)

        cursor.execute("""
            INSERT INTO usuarios (
                nome, email, empresa, cargo, setor,
                senha_hash, ativo, data_cadastro
            )
            VALUES (?, ?, ?, ?, ?, ?, 1, ?)
        """, (
            s["nome"],
            s["email"],
            empresa or s["empresa"],
            cargo or s["cargo"],
            setor or s["setor"],
            senha_hash,
            agora
        ))

        novo_usuario_id = cursor.lastrowid

        # ----------------------------------------------------
        # 5. Associar ao grupo
        # ----------------------------------------------------

        cursor.execute("""
            INSERT INTO usuario_grupo (usuario_id, grupo_id)
            VALUES (?, ?)
        """, (novo_usuario_id, grupo_id))

        # ----------------------------------------------------
        # 6. Marcar solicitação como aprovada
        # ----------------------------------------------------

        cursor.execute("""
            UPDATE solicitacoes_acesso
            SET status = 'APROVADA',
                data_analise = ?,
                analisado_por = ?
            WHERE id = ?
        """, (agora, usuario_id, solicitacao_id))

        conexao.commit()

        return {
            "solicitacao_id": solicitacao_id,
            "usuario_id": novo_usuario_id,
            "status": "APROVADA"
        }

    except Exception:
        conexao.rollback()
        raise
    finally:
        conexao.close()


def rejeitar_solicitacao_acesso(
    solicitacao_id,
    usuario_id,
    motivo_rejeicao
):
    """
    Rejeita uma solicitação pendente.

    Exige a permissão 'acessos.rejeitar'.
    Não cria usuário.
    """

    if not tem_permissao(usuario_id, "acessos.rejeitar"):
        raise PermissionError(
            "Usuário sem permissão para rejeitar solicitações."
        )

    motivo_rejeicao = str(motivo_rejeicao or "").strip()

    if not motivo_rejeicao:
        raise ValueError("Informe o motivo da rejeição.")

    criar_tabelas_seguranca()

    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute("""
            SELECT * FROM solicitacoes_acesso
            WHERE id = ? LIMIT 1
        """, (solicitacao_id,))

        s = cursor.fetchone()

        if s is None:
            raise ValueError("Solicitação não encontrada.")

        if s["status"] != "PENDENTE":
            raise ValueError(
                f"Solicitação já está com status {s['status']}."
            )

        agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("""
            UPDATE solicitacoes_acesso
            SET status = 'REJEITADA',
                data_analise = ?,
                analisado_por = ?,
                motivo_rejeicao = ?
            WHERE id = ?
        """, (
            agora,
            usuario_id,
            motivo_rejeicao,
            solicitacao_id
        ))

        conexao.commit()

        return {
            "solicitacao_id": solicitacao_id,
            "status": "REJEITADA"
        }

    except Exception:
        conexao.rollback()
        raise
    finally:
        conexao.close()