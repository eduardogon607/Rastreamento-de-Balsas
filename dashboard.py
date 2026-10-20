# Dashboard do DashPy — Combitrans
# Consultas pelo banco.py, cálculos pelo admin.py.
# A tela se atualiza a cada 60s relendo o SQLite.
# O botão "Atualizar dados da API" executa o main.py.

# ============================================================
# IMPORTS
# ============================================================

from datetime import datetime, date, time, timedelta
from pathlib import Path
import base64
import sqlite3
import subprocess
import sys

import pandas as pd
import streamlit as st

import banco
from admin import consultar_situacao_balsa
from rotas import obter_rota


# ============================================================
# CAMINHOS DO PROJETO
# ============================================================

PASTA = Path(__file__).resolve().parent
BANCO = PASTA / "dados_totaltrack.db"
MAIN = PASTA / "main.py"
LOGO = PASTA / "logo_combitrans.jpeg"

banco.NOME_BANCO = str(BANCO)


# ============================================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================================

st.set_page_config(
    page_title="DashPy | Combitrans",
    page_icon=str(LOGO) if LOGO.is_file() else "🚢",
    layout="wide"
)


# ============================================================
# MAPEAMENTO DE PERFIS DE ACESSO
# ============================================================

PERFIS = {
    "Visualizador": {
        "grupo_id": 4,
        "descricao": "Somente visualização. Não altera nada.",
        "permissoes": [
            "dashboard.visualizar",
            "mapa.visualizar",
            "viagens.visualizar",
        ],
    },
    "Operador": {
        "grupo_id": 3,
        "descricao": (
            "Visualiza e propõe correções; "
            "as alterações precisam de aprovação do Administrador."
        ),
        "permissoes": [
            "dashboard.visualizar",
            "mapa.visualizar",
            "viagens.visualizar",
            "viagens.editar",
            "correcoes.solicitar",
            "inconsistencias.visualizar",
            "inconsistencias.confirmar",
        ],
    },
    "Administrador": {
        "grupo_id": 2,
        "descricao": "Acesso total. Aprova acessos e correções.",
        "permissoes": list(banco.PERMISSOES_SISTEMA.keys()),
    },
}

PERFIL_POR_GRUPO_ID = {
    4: "Visualizador",
    3: "Operador",
    2: "Administrador",
}

# Limite de antiguidade: 1 ano
LIMITE_ANTIGO_DIAS = 365


# ============================================================
# FUNÇÕES AUXILIARES DE DATA
# ============================================================

def data(valor):
    if not valor:
        return None
    if isinstance(valor, datetime):
        return valor
    return datetime.fromisoformat(valor)


def formatar_data(valor):
    return (
        data(valor).strftime("%d/%m/%y %H:%M")
        if valor
        else "—"
    )


def validar_datas_viagem(inicio, fim, contexto="viagem"):
    """
    Valida um par (início, fim) de datas.

    Retorna (ok: bool, mensagem: str|None).
    """
    agora = datetime.now()

    # -------- Início --------
    if inicio is not None:
        if inicio > agora:
            return False, (
                "A **saída** não pode estar no futuro. "
                f"Data informada: {inicio:%d/%m/%Y %H:%M}"
            )

        dias_atras = (agora - inicio).days
        if dias_atras > LIMITE_ANTIGO_DIAS:
            return False, (
                f"A **saída** está há {dias_atras} dias no "
                f"passado. O limite é {LIMITE_ANTIGO_DIAS} "
                f"dias (1 ano)."
            )

    # -------- Fim --------
    if fim is not None:
        if inicio is not None and fim < inicio:
            return False, (
                "A **chegada** não pode ser anterior à "
                "**saída**.\n"
                f"Saída: {inicio:%d/%m/%Y %H:%M} · "
                f"Chegada: {fim:%d/%m/%Y %H:%M}"
            )

        if fim > agora:
            margem = (fim - agora).total_seconds()
            if margem > 300:  # 5 minutos de tolerância
                return False, (
                    "A **chegada** não pode estar no futuro. "
                    f"Data informada: {fim:%d/%m/%Y %H:%M}"
                )

    return True, None


def campos_data_hora(
    prefixo,
    valor_inicial=None,
    rotulo="Data",
    permitir_vazio=True,
    key_suffix=""
):
    """
    Renderiza um par (date_input + time_input).

    Retorna datetime ou None.

    O Streamlit garante que o usuário não consegue
    digitar uma data inexistente (ex.: mês 29). O
    date_input usa calendário.
    """
    base = valor_inicial or datetime.now()

    sem_data = False
    if permitir_vazio:
        sem_data = st.checkbox(
            f"{rotulo}: sem data definida",
            value=(valor_inicial is None),
            key=f"sem_{prefixo}_{key_suffix}"
        )
        if sem_data:
            return None

    col_d, col_h = st.columns(2)

    with col_d:
        d = st.date_input(
            "Data",
            value=base.date(),
            key=f"data_{prefixo}_{key_suffix}"
        )

    with col_h:
        t = st.time_input(
            "Hora",
            value=base.time().replace(microsecond=0),
            key=f"hora_{prefixo}_{key_suffix}",
            step=60
        )

    return datetime.combine(d, t)


# ============================================================
# LOGO E CABEÇALHOS
# ============================================================

def _logo_data_url():
    if not LOGO.is_file():
        return None

    sufixo = LOGO.suffix.lower().lstrip(".")
    mimetype = {
        "png":  "image/png",
        "jpg":  "image/jpeg",
        "jpeg": "image/jpeg",
        "svg":  "image/svg+xml",
        "webp": "image/webp",
    }.get(sufixo, "image/png")

    b64 = base64.b64encode(LOGO.read_bytes()).decode()
    return f"data:{mimetype};base64,{b64}"


def cabecalho_login():
    data_url = _logo_data_url()

    if data_url:
        conteudo = (
            f'<img src="{data_url}" alt="Combitrans" '
            f'style="height:52px;display:block;">'
        )
    else:
        conteudo = (
            '<div style="color:#FFFFFF;font-size:22px;'
            'font-weight:700;line-height:1;">Combitrans</div>'
        )

    st.markdown(
        f"""
        <div style="
            display:flex;
            align-items:center;
            gap:16px;
            background:linear-gradient(90deg,#0D2E63 0%,#08224D 100%);
            padding:16px 28px;
            border-radius:0 0 14px 14px;
            margin:-1rem -1rem 2rem -1rem;
            box-shadow:0 4px 14px rgba(13,46,99,0.18);
        ">
            {conteudo}
            <div style="
                color:#B8C9E3;
                font-size:13px;
                margin-left:auto;
                letter-spacing:0.5px;
            ">
                Sistema de Monitoramento · DashPy
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def cabecalho_dashboard(usuario, modo_edicao=False):
    data_url = _logo_data_url()

    if data_url:
        logo_tag = (
            f'<img src="{data_url}" alt="Combitrans" '
            f'style="height:44px;display:block;">'
        )
    else:
        logo_tag = (
            '<div style="color:#FFFFFF;font-size:20px;'
            'font-weight:700;line-height:1;">Combitrans</div>'
        )

    if modo_edicao:
        faixa = (
            '<div style="background:#B45309;color:#FFFFFF;'
            'padding:4px 10px;border-radius:6px;'
            'font-size:11px;font-weight:700;'
            'margin-left:12px;letter-spacing:0.5px;">'
            '✏️ MODO EDIÇÃO ATIVO</div>'
        )
    else:
        faixa = ""

    col_esq, col_dir = st.columns([3, 1])

    with col_esq:
        st.markdown(
            f"""
            <div style="
                display:flex;
                align-items:center;
                gap:16px;
                background:linear-gradient(90deg,#0D2E63 0%,#08224D 100%);
                padding:14px 22px;
                border-radius:0 0 12px 12px;
                margin:-1rem -1rem 1.25rem -1rem;
                box-shadow:0 4px 14px rgba(13,46,99,0.18);
            ">
                {logo_tag}
                <div>
                    <div style="color:#FFFFFF;font-size:17px;
                                font-weight:700;line-height:1.2;">
                        Monitoramento de balsas
                    </div>
                    <div style="color:#B8C9E3;font-size:12px;
                                margin-top:2px;">
                        COMBITRANS · Projeto DashPy
                    </div>
                </div>
                {faixa}
            </div>
            """,
            unsafe_allow_html=True
        )

    with col_dir:
        st.caption(f"Conectado como **{usuario['nome']}**")
        if st.button("Sair", use_container_width=True):
            st.session_state.pop("usuario", None)
            st.session_state.pop("modo_edicao", None)
            st.rerun()


# ============================================================
# OUTRAS AUXILIARES
# ============================================================

def pendencia_viagem(viagem, eventos):
    if not viagem or not viagem.get("data_inicio"):
        return ""

    inicio = data(viagem["data_inicio"])

    if inicio > datetime.now():
        return "Início da viagem no futuro"

    rota = obter_rota(viagem["origem"], viagem["destino"])
    if not rota:
        return "Rota não identificada"

    pontos = [p["ponto"] for p in rota]
    indice_anterior = 0

    for evento in eventos:
        if (
            evento["placa"] != viagem["placa"]
            or evento["evento"] != "Entrada"
        ):
            continue

        if (
            evento["area"] not in pontos
            or data(evento["dataGPS"]) < inicio
        ):
            continue

        indice = pontos.index(evento["area"])

        if indice == 0 and data(evento["dataGPS"]) == inicio:
            continue

        if indice == 0:
            return (
                "Entrada na origem após a saída; "
                "conferir viagem/geofence"
            )

        if indice < indice_anterior:
            return (
                "Pontos fora da sequência; "
                "conferir associação da viagem"
            )

        indice_anterior = indice

        if indice == len(pontos) - 1:
            return (
                "Chegada ao destino registrada, "
                "mas viagem ainda aberta"
            )

    return ""


def atualizar_dados_api():
    if not MAIN.is_file():
        raise FileNotFoundError(
            "main.py não foi encontrado na pasta do projeto."
        )

    processo = subprocess.run(
        [sys.executable, str(MAIN)],
        cwd=str(PASTA),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )

    if processo.returncode != 0:
        mensagem = (
            processo.stderr.strip()
            or processo.stdout.strip()
            or "O main.py terminou com erro."
        )
        raise RuntimeError(mensagem)

    return processo.stdout.strip()


# ============================================================
# HELPERS DE PERFIL / PERMISSÃO
# ============================================================

def perfil_do_usuario(usuario_id):
    grupos = banco.consultar_grupos_usuario(usuario_id, somente_ativos=True)

    for g in grupos:
        rotulo = PERFIL_POR_GRUPO_ID.get(g["id"])
        if rotulo:
            return rotulo

    return None


def garantir_permissoes_do_perfil(perfil_nome):
    perfil = PERFIS.get(perfil_nome)
    if not perfil:
        raise ValueError(f"Perfil desconhecido: {perfil_nome}")

    banco.definir_permissoes_grupo(
        grupo_id=perfil["grupo_id"],
        codigos_permissoes=perfil["permissoes"]
    )


# ============================================================
# SOLICITAÇÕES DE ACESSO
# ============================================================

def _tem_funcao(nome):
    return hasattr(banco, nome) and callable(getattr(banco, nome))


def contar_solicitacoes_pendentes():
    try:
        return len(banco.consultar_solicitacoes_acesso("PENDENTE"))
    except Exception:
        return 0


def contar_correcoes_pendentes():
    try:
        return len(banco.consultar_solicitacoes_correcao("PENDENTE"))
    except Exception:
        return 0


def tela_autorizacoes(usuario):
    st.subheader("🔐 Autorização de acessos")
    st.caption(
        "Solicitações enviadas pela tela de login ficam aqui "
        "até serem aprovadas ou rejeitadas."
    )

    try:
        pendentes = banco.consultar_solicitacoes_acesso("PENDENTE")
    except Exception as erro:
        st.error(f"Não foi possível consultar solicitações: {erro}")
        return

    if not pendentes:
        st.success("Nenhuma solicitação pendente. Tudo em ordem. ✅")
    else:
        st.markdown(f"**{len(pendentes)} solicitação(ões) pendente(s)**")

        nomes_perfis = list(PERFIS.keys())

        for s in pendentes:
            with st.container(border=True):
                col_info, col_acoes = st.columns([3, 2])

                with col_info:
                    st.markdown(f"### {s['nome']}")
                    st.write(f"**E-mail:** {s['email']}")
                    if s.get("empresa"):
                        st.write(f"**Empresa:** {s['empresa']}")
                    if s.get("cargo"):
                        st.write(f"**Cargo:** {s['cargo']}")
                    if s.get("setor"):
                        st.write(f"**Setor:** {s['setor']}")
                    st.write(
                        f"**Justificativa:** "
                        f"{s.get('justificativa', '—')}"
                    )
                    st.caption(
                        f"Enviada em "
                        f"{formatar_data(s.get('data_solicitacao'))}"
                    )

                with col_acoes:
                    tem_aprovar = (
                        _tem_funcao("aprovar_solicitacao_acesso")
                        and banco.tem_permissao(
                            usuario["id"], "acessos.aprovar"
                        )
                    )
                    tem_rejeitar = (
                        _tem_funcao("rejeitar_solicitacao_acesso")
                        and banco.tem_permissao(
                            usuario["id"], "acessos.rejeitar"
                        )
                    )

                    if not tem_aprovar:
                        st.caption(
                            "⚠️ Aprovação indisponível: falta "
                            "`banco.aprovar_solicitacao_acesso` "
                            "ou a permissão `acessos.aprovar`."
                        )
                    if not tem_rejeitar:
                        st.caption(
                            "⚠️ Rejeição indisponível: falta "
                            "`banco.rejeitar_solicitacao_acesso` "
                            "ou a permissão `acessos.rejeitar`."
                        )

                    with st.expander("✅ Aprovar"):
                        perfil_escolhido = st.selectbox(
                            "Tipo de acesso",
                            nomes_perfis,
                            key=f"perfil_{s['id']}",
                            format_func=lambda x: (
                                f"{x} — {PERFIS[x]['descricao']}"
                            )
                        )

                        senha_temp = st.text_input(
                            "Senha provisória (mín. 10 caracteres)",
                            type="password",
                            key=f"senha_{s['id']}"
                        )

                        if st.button(
                            "Confirmar aprovação",
                            key=f"aprovar_{s['id']}",
                            disabled=not tem_aprovar,
                            type="primary"
                        ):
                            try:
                                garantir_permissoes_do_perfil(
                                    perfil_escolhido
                                )

                                grupo_id = PERFIS[
                                    perfil_escolhido
                                ]["grupo_id"]

                                banco.aprovar_solicitacao_acesso(
                                    solicitacao_id=s["id"],
                                    usuario_id=usuario["id"],
                                    grupo_id=grupo_id,
                                    senha_provisoria=senha_temp
                                )

                                st.success(
                                    f"Usuário {s['email']} aprovado "
                                    f"como **{perfil_escolhido}**."
                                )
                                st.rerun()

                            except Exception as erro:
                                st.error(f"Erro: {erro}")

                    with st.expander("❌ Rejeitar"):
                        motivo = st.text_area(
                            "Motivo da rejeição",
                            key=f"motivo_{s['id']}"
                        )

                        if st.button(
                            "Confirmar rejeição",
                            key=f"rejeitar_{s['id']}",
                            disabled=not tem_rejeitar
                        ):
                            try:
                                banco.rejeitar_solicitacao_acesso(
                                    solicitacao_id=s["id"],
                                    usuario_id=usuario["id"],
                                    motivo_rejeicao=motivo
                                )
                                st.success("Solicitação rejeitada.")
                                st.rerun()
                            except Exception as erro:
                                st.error(f"Erro: {erro}")

    with st.expander("Histórico de solicitações"):
        try:
            todas = banco.consultar_solicitacoes_acesso()
        except Exception:
            todas = []

        if todas:
            historico = pd.DataFrame([
                {
                    "ID": x["id"],
                    "Nome": x["nome"],
                    "E-mail": x["email"],
                    "Status": x["status"],
                    "Solicitada em": formatar_data(
                        x.get("data_solicitacao")
                    ),
                    "Analisada em": formatar_data(
                        x.get("data_analise")
                    ),
                }
                for x in todas
            ])
            st.dataframe(
                historico, hide_index=True, width="stretch"
            )
        else:
            st.info("Nenhuma solicitação registrada.")


# ============================================================
# CORREÇÕES PENDENTES
# ============================================================

def tela_correcoes(usuario):
    st.subheader("✏️ Correções pendentes")
    st.caption(
        "Operadores propõem correções. O Administrador aprova ou "
        "rejeita. A viagem só é alterada após a aprovação."
    )

    try:
        pendentes = banco.consultar_solicitacoes_correcao("PENDENTE")
    except Exception as erro:
        st.error(f"Não foi possível consultar correções: {erro}")
        return

    if not pendentes:
        st.success("Nenhuma correção pendente. Tudo em ordem. ✅")
        return

    st.markdown(f"**{len(pendentes)} correção(ões) pendente(s)**")

    for c in pendentes:
        with st.container(border=True):
            col_info, col_acoes = st.columns([3, 2])

            with col_info:
                st.markdown(
                    f"### Viagem {c['codigo_viagem']}"
                )
                st.write(f"**Placa:** {c['placa']}")
                st.write(
                    f"**Saída atual:** "
                    f"{formatar_data(c.get('data_inicio_atual'))}"
                )
                st.write(
                    f"**Chegada atual:** "
                    f"{formatar_data(c.get('data_fim_atual'))}"
                )
                st.write(
                    f"**Nova saída:** "
                    f"{formatar_data(c.get('nova_data_inicio'))}"
                )
                st.write(
                    f"**Nova chegada:** "
                    f"{formatar_data(c.get('nova_data_fim'))}"
                )
                st.write(f"**Motivo:** {c.get('motivo', '—')}")
                st.caption(
                    f"Solicitada por "
                    f"{c.get('solicitado_por_nome', '—')} em "
                    f"{formatar_data(c.get('data_solicitacao'))}"
                )

            with col_acoes:
                st.write("**Decisão**")

                pode_aprovar = banco.tem_permissao(
                    usuario["id"], "correcoes.aprovar"
                )
                pode_rejeitar = banco.tem_permissao(
                    usuario["id"], "correcoes.rejeitar"
                )

                if st.button(
                    "✅ Aplicar correção",
                    key=f"aplicar_{c['id']}",
                    disabled=not pode_aprovar,
                    type="primary"
                ):
                    try:
                        banco.corrigir_datas_viagem(
                            id_viagem=c["viagem_id"],
                            nova_data_inicio=c.get("nova_data_inicio"),
                            nova_data_fim=c.get("nova_data_fim"),
                            motivo=c.get("motivo", "Correção aprovada")
                        )

                        conexao = banco.conectar_banco()
                        cursor = conexao.cursor()
                        cursor.execute("""
                            UPDATE solicitacoes_correcao
                            SET status = 'APROVADA',
                                data_analise = ?,
                                analisado_por = ?,
                                motivo_decisao = ?
                            WHERE id = ?
                        """, (
                            datetime.now().strftime(
                                "%Y-%m-%d %H:%M:%S"
                            ),
                            usuario["id"],
                            "Aprovada via dashboard",
                            c["id"]
                        ))
                        conexao.commit()
                        conexao.close()

                        st.success("Correção aplicada.")
                        st.rerun()
                    except Exception as erro:
                        st.error(f"Erro: {erro}")

                with st.expander("❌ Rejeitar"):
                    motivo_rej = st.text_area(
                        "Motivo da rejeição",
                        key=f"motivo_corr_{c['id']}"
                    )
                    if st.button(
                        "Confirmar rejeição",
                        key=f"rejeitar_corr_{c['id']}",
                        disabled=not pode_rejeitar
                    ):
                        try:
                            conexao = banco.conectar_banco()
                            cursor = conexao.cursor()
                            cursor.execute("""
                                UPDATE solicitacoes_correcao
                                SET status = 'REJEITADA',
                                    data_analise = ?,
                                    analisado_por = ?,
                                    motivo_decisao = ?
                                WHERE id = ?
                            """, (
                                datetime.now().strftime(
                                    "%Y-%m-%d %H:%M:%S"
                                ),
                                usuario["id"],
                                motivo_rej,
                                c["id"]
                            ))
                            conexao.commit()
                            conexao.close()
                            st.success("Correção rejeitada.")
                            st.rerun()
                        except Exception as erro:
                            st.error(f"Erro: {erro}")


# ============================================================
# CARREGAR DADOS DO PAINEL
# ============================================================

def carregar_painel():
    eventos = banco.consultar_eventos_cronologicos()
    viagens = banco.consultar_viagens()
    balsas = banco.buscar_balsas_ativas()

    ultimos = {}
    for evento in eventos:
        ultimos[evento["placa"]] = evento

    abertas = {}
    for viagem in viagens:
        if viagem["data_fim"] is None:
            abertas.setdefault(viagem["placa"], []).append(viagem)

    linhas = []
    detalhes = {}
    agora = datetime.now()

    for placa, cadastro in sorted(
        balsas.items(),
        key=lambda item: item[1]["nome"]
    ):
        lista = abertas.get(placa, [])
        viagem = lista[0] if len(lista) == 1 else None

        aviso = (
            "Mais de uma viagem aberta"
            if len(lista) > 1
            else "Sem viagem aberta"
            if not lista
            else pendencia_viagem(viagem, eventos)
        )

        situacao = consultar_situacao_balsa(placa) if viagem else {}
        situacao = situacao or {}

        evento = ultimos.get(placa, {})
        ultimo = data(evento.get("dataGPS"))

        idade = (
            (agora - ultimo).total_seconds() / 3600
            if ultimo
            else None
        )

        evento_estado = (
            "Sem evento registrado"
            if idade is None
            else "Data de evento no futuro"
            if idade < 0
            else "Evento há mais de 24h"
            if idade > 24
            else "Evento recente"
        )

        eta = None if aviso else situacao.get("eta_destino")
        eta_texto = "Conferir viagem" if aviso else formatar_data(eta)

        if eta and data(eta) < agora:
            eta_texto += " · previsão vencida"

        linha = {
            "Balsa": cadastro["nome"],
            "Viagem": viagem["codigo_viagem"] if viagem else "—",
            "Status": situacao.get("status") or (
                viagem["status"] if viagem else "Sem viagem"
            ),
            "Rota": situacao.get("trajeto") or "—",
            "Prazo": "Conferir viagem" if aviso else (
                situacao.get("situacao_prazo") or "—"
            ),
            "Tempo em viagem": situacao.get("tempo_em_viagem") or "—",
            "Previsão de chegada": eta_texto,
            "Último evento": formatar_data(evento.get("dataGPS")),
            "Local do evento": evento.get("area", "—"),
            "Dados do evento": evento_estado,
            "Conferência": aviso or "Sem alerta de sequência",
        }

        linhas.append(linha)

        detalhes[cadastro["nome"]] = {
            "situacao": situacao,
            "viagem": viagem,
            "evento": evento,
            "aviso": aviso,
        }

    return pd.DataFrame(linhas), detalhes, viagens, eventos


# ============================================================
# ESTILO GLOBAL — Azul Combitrans
# ============================================================

st.markdown(
    """
    <style>
    .stApp { background:#F5F7FB; }

    h1, h2, h3 { color:#0D2E63; }

    .stButton > button,
    .stFormSubmitButton > button,
    button[kind="primary"],
    button[kind="primaryFormSubmit"],
    button[kind="secondaryFormSubmit"] {
        background-color:#0D2E63 !important;
        color:#FFFFFF !important;
        border:1px solid #0D2E63 !important;
        border-radius:8px !important;
        font-weight:600 !important;
    }
    .stButton > button:hover,
    .stFormSubmitButton > button:hover,
    button[kind="primary"]:hover,
    button[kind="primaryFormSubmit"]:hover,
    button[kind="secondaryFormSubmit"]:hover {
        background-color:#08224D !important;
        border-color:#08224D !important;
        color:#FFFFFF !important;
    }

    input:focus, textarea:focus,
    .stTextInput input:focus,
    .stTextArea textarea:focus {
        border-color:#0D2E63 !important;
        box-shadow:0 0 0 2px rgba(13,46,99,0.15) !important;
    }

    [data-testid="stMetric"] {
        background:#FFFFFF;
        border:1px solid #E3E8F0;
        border-left:4px solid #0D2E63;
        border-radius:12px;
        padding:16px;
        box-shadow:0 1px 3px rgba(13,46,99,0.06);
    }

    .login-card {
        background:#FFFFFF;
        padding:24px 28px;
        border-radius:14px;
        border-top:5px solid #0D2E63;
        box-shadow:0 6px 20px rgba(13,46,99,0.10);
        margin-bottom:16px;
    }
    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# TELA DE ACESSO (login + solicitação)
# ============================================================

def tela_acesso():
    cabecalho_login()

    col_esq, col_centro, col_dir = st.columns([1, 1.4, 1])

    with col_centro:
        st.markdown('<div class="login-card">', unsafe_allow_html=True)

        with st.form("form_login", clear_on_submit=False):
            st.subheader("Entrar")

            email = st.text_input(
                "E-mail",
                placeholder="seu.email@empresa.com.br"
            )
            senha = st.text_input("Senha", type="password")

            entrar = st.form_submit_button(
                "Entrar",
                use_container_width=True,
                type="primary"
            )

        if entrar:
            usuario = banco.autenticar_usuario(email, senha)
            if usuario is None:
                st.error("E-mail ou senha inválidos.")
            else:
                st.session_state["usuario"] = usuario
                st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

        with st.expander("Não tem acesso? Solicite aqui"):
            st.caption(
                "O envio deste formulário não libera acesso "
                "automaticamente. A solicitação ficará pendente "
                "para análise."
            )

            with st.form("form_solicitar_acesso", clear_on_submit=True):
                nome = st.text_input("Nome completo")
                email_solicitacao = st.text_input(
                    "E-mail corporativo/profissional"
                )
                empresa = st.text_input("Empresa")
                cargo = st.text_input("Cargo/Função")
                setor = st.text_input("Setor")
                justificativa = st.text_area(
                    "Justificativa/Motivo do acesso",
                    placeholder=(
                        "Informe por que você precisa acessar "
                        "o DashPy."
                    )
                )

                solicitar = st.form_submit_button(
                    "Enviar solicitação",
                    use_container_width=True,
                    type="primary"
                )

            if solicitar:
                try:
                    banco.criar_solicitacao_acesso(
                        nome=nome,
                        email=email_solicitacao,
                        empresa=empresa,
                        cargo=cargo,
                        setor=setor,
                        justificativa=justificativa
                    )
                    st.success(
                        "Solicitação enviada com sucesso. "
                        "Ela ficará pendente até ser analisada."
                    )
                except ValueError as erro:
                    st.warning(str(erro))
                except Exception:
                    st.error(
                        "Não foi possível enviar a solicitação "
                        "neste momento."
                    )


# ============================================================
# BOTÕES DE EDIÇÃO (MODO EDIÇÃO DO ADMIN)
# ============================================================

def bloco_edicao_balsa(nome_balsa, dados_detalhe, usuario):
    viagem = dados_detalhe.get("viagem")
    evento = dados_detalhe.get("evento")
    cadastro = banco.buscar_balsa(
        viagem["placa"] if viagem else None
    ) or {}

    st.markdown("---")
    st.markdown("### ✏️ Modo edição — " + nome_balsa)

    abas = st.tabs([
        "📅 Datas da viagem",
        "🚦 Finalizar/Iniciar",
        "🚢 Dados da balsa",
        "🗑️ Deletar evento",
    ])

    # --------------------------------------------------------
    # ABA 1 — EDITAR DATAS
    # --------------------------------------------------------

    with abas[0]:
        if not viagem:
            st.info("Nenhuma viagem aberta para esta balsa.")
        else:
            st.caption(
                f"Viagem **{viagem['codigo_viagem']}** — "
                f"edite as datas de saída e chegada."
            )

            st.markdown("**Saída registrada**")
            saida_atual = None
            if viagem.get("data_inicio"):
                try:
                    saida_atual = datetime.strptime(
                        viagem["data_inicio"],
                        "%Y-%m-%d %H:%M:%S"
                    )
                except ValueError:
                    saida_atual = None

            nova_saida = campos_data_hora(
                prefixo="saida",
                valor_inicial=saida_atual,
                rotulo="Saída",
                permitir_vazio=True,
                key_suffix=f"ed_{viagem['id']}"
            )

            st.markdown("**Chegada registrada**")
            chegada_atual = None
            if viagem.get("data_fim"):
                try:
                    chegada_atual = datetime.strptime(
                        viagem["data_fim"],
                        "%Y-%m-%d %H:%M:%S"
                    )
                except ValueError:
                    chegada_atual = None

            nova_chegada = campos_data_hora(
                prefixo="chegada",
                valor_inicial=chegada_atual,
                rotulo="Chegada",
                permitir_vazio=True,
                key_suffix=f"ed_{viagem['id']}"
            )

            motivo_data = st.text_area(
                "Motivo da correção",
                placeholder="Ex.: API mandou evento com horário errado",
                key=f"motivo_data_{viagem['id']}"
            )

            if st.button(
                "💾 Salvar datas",
                key=f"salvar_datas_{viagem['id']}",
                type="primary"
            ):
                ok, erro = validar_datas_viagem(
                    nova_saida,
                    nova_chegada,
                    contexto="viagem"
                )
                if not ok:
                    st.error(erro)
                elif not motivo_data.strip():
                    st.error("Informe o motivo da correção.")
                else:
                    try:
                        banco.corrigir_datas_viagem(
                            id_viagem=viagem["id"],
                            nova_data_inicio=(
                                nova_saida.strftime(
                                    "%Y-%m-%d %H:%M:%S"
                                )
                                if nova_saida else None
                            ),
                            nova_data_fim=(
                                nova_chegada.strftime(
                                    "%Y-%m-%d %H:%M:%S"
                                )
                                if nova_chegada else None
                            ),
                            motivo=motivo_data
                        )
                        st.success("Datas corrigidas com sucesso.")
                        st.rerun()
                    except Exception as erro:
                        st.error(f"Erro ao salvar: {erro}")

    # --------------------------------------------------------
    # ABA 2 — INICIAR / FINALIZAR
    # --------------------------------------------------------

    with abas[1]:
        if not viagem:
            st.info("Nenhuma viagem aberta para esta balsa.")
        else:
            col_a, col_b = st.columns(2)

            # ---------------- INICIAR ----------------
            with col_a:
                st.markdown("**Iniciar viagem**")

                saida_ini = None
                if viagem.get("data_inicio"):
                    try:
                        saida_ini = datetime.strptime(
                            viagem["data_inicio"],
                            "%Y-%m-%d %H:%M:%S"
                        )
                    except ValueError:
                        saida_ini = None

                data_ini = campos_data_hora(
                    prefixo="iniciar",
                    valor_inicial=saida_ini,
                    rotulo="Início",
                    permitir_vazio=False,
                    key_suffix=f"ini_{viagem['id']}"
                )

                if st.button(
                    "▶️ Iniciar viagem",
                    key=f"btn_iniciar_{viagem['id']}",
                    type="primary"
                ):
                    ok, erro = validar_datas_viagem(
                        data_ini, None, contexto="início"
                    )
                    if not ok:
                        st.error(erro)
                    else:
                        try:
                            banco.iniciar_viagem_banco(
                                id_viagem=viagem["id"],
                                data_inicio=data_ini.strftime(
                                    "%Y-%m-%d %H:%M:%S"
                                )
                            )
                            st.success("Viagem iniciada.")
                            st.rerun()
                        except Exception as erro:
                            st.error(f"Erro: {erro}")

            # ---------------- FINALIZAR ----------------
            with col_b:
                st.markdown("**Finalizar viagem**")

                chegada_fim = None
                if viagem.get("data_fim"):
                    try:
                        chegada_fim = datetime.strptime(
                            viagem["data_fim"],
                            "%Y-%m-%d %H:%M:%S"
                        )
                    except ValueError:
                        chegada_fim = None

                data_fim = campos_data_hora(
                    prefixo="finalizar",
                    valor_inicial=chegada_fim or datetime.now(),
                    rotulo="Fim",
                    permitir_vazio=False,
                    key_suffix=f"fim_{viagem['id']}"
                )

                if st.button(
                    "⏹️ Finalizar viagem",
                    key=f"btn_finalizar_{viagem['id']}",
                    type="primary"
                ):
                    inicio_banco = None
                    if viagem.get("data_inicio"):
                        try:
                            inicio_banco = datetime.strptime(
                                viagem["data_inicio"],
                                "%Y-%m-%d %H:%M:%S"
                            )
                        except ValueError:
                            inicio_banco = None

                    ok, erro = validar_datas_viagem(
                        inicio_banco, data_fim,
                        contexto="finalização"
                    )
                    if not ok:
                        st.error(erro)
                    else:
                        try:
                            if inicio_banco and data_fim:
                                duracao = (
                                    data_fim - inicio_banco
                                ).total_seconds() / 3600
                            else:
                                duracao = None

                            prazo = viagem.get("prazo_horas")
                            if duracao is not None and prazo:
                                diferenca = duracao - prazo
                                status_prazo = (
                                    "No prazo" if diferenca <= 0
                                    else "Atrasada"
                                )
                            else:
                                diferenca = None
                                status_prazo = None

                            banco.finalizar_viagem_banco(
                                id_viagem=viagem["id"],
                                data_fim=data_fim.strftime(
                                    "%Y-%m-%d %H:%M:%S"
                                ),
                                duracao_horas=duracao,
                                diferenca_horas=diferenca,
                                status_prazo=status_prazo
                            )
                            st.success("Viagem finalizada.")
                            st.rerun()
                        except Exception as erro:
                            st.error(f"Erro: {erro}")

    # --------------------------------------------------------
    # ABA 3 — DADOS DA BALSA
    # --------------------------------------------------------

    with abas[2]:
        if not cadastro:
            st.info("Balsa não encontrada.")
        else:
            with st.form(f"form_balsa_{cadastro['id']}"):
                novo_nome = st.text_input(
                    "Nome", value=cadastro.get("nome", "")
                )
                novo_prefixo = st.text_input(
                    "Prefixo", value=cadastro.get("prefixo", "")
                )
                novo_status = st.checkbox(
                    "Ativa",
                    value=bool(cadastro.get("ativa"))
                )

                if st.form_submit_button("Salvar dados da balsa"):
                    try:
                        banco.salvar_balsa(
                            placa=cadastro["placa"],
                            nome=novo_nome,
                            prefixo=novo_prefixo,
                            ativa=novo_status
                        )
                        st.success("Balsa atualizada.")
                        st.rerun()
                    except Exception as erro:
                        st.error(f"Erro: {erro}")

    # --------------------------------------------------------
    # ABA 4 — DELETAR EVENTO
    # --------------------------------------------------------

    with abas[3]:
        st.caption(
            "Deletar um evento remove ele do banco. "
            "Uma cópia integral é guardada em auditoria."
        )

        eventos_balsa = [
            e for e in banco.consultar_eventos_cronologicos()
            if e["placa"] == (viagem["placa"] if viagem else None)
        ]

        if not eventos_balsa:
            st.info("Nenhum evento para esta balsa.")
        else:
            eventos_balsa_ord = list(reversed(eventos_balsa))[:30]

            opcoes = {
                f"{e['id']} — {e['evento']} @ {e['area']} "
                f"({e['dataGPS']})": e
                for e in eventos_balsa_ord
            }

            escolha = st.selectbox(
                "Escolha o evento a deletar",
                list(opcoes.keys()),
                key=f"del_evt_{cadastro.get('id', 'x')}"
            )

            motivo_del = st.text_area(
                "Motivo da remoção",
                key=f"del_motivo_{cadastro.get('id', 'x')}"
            )

            if st.button(
                "🗑️ Deletar evento",
                key=f"del_btn_{cadastro.get('id', 'x')}"
            ):
                try:
                    evt = opcoes[escolha]
                    banco.deletar_evento(
                        evento_id=evt["id"],
                        usuario_id=usuario["id"],
                        motivo=motivo_del
                    )
                    st.success("Evento deletado.")
                    st.rerun()
                except Exception as erro:
                    st.error(f"Erro: {erro}")


def bloco_propor_correcao(nome_balsa, dados_detalhe, usuario):
    viagem = dados_detalhe.get("viagem")

    if not viagem:
        return

    with st.expander("✏️ Propor correção para esta viagem"):
        st.caption(
            "Sua proposta fica pendente até o Administrador "
            "aprovar. A viagem só é alterada depois disso."
        )

        saida_atual = None
        if viagem.get("data_inicio"):
            try:
                saida_atual = datetime.strptime(
                    viagem["data_inicio"],
                    "%Y-%m-%d %H:%M:%S"
                )
            except ValueError:
                saida_atual = None

        st.markdown("**Nova saída**")
        nova_saida = campos_data_hora(
            prefixo="prop_saida",
            valor_inicial=saida_atual,
            rotulo="Saída",
            permitir_vazio=False,
            key_suffix=f"p_{viagem['id']}"
        )

        chegada_atual = None
        if viagem.get("data_fim"):
            try:
                chegada_atual = datetime.strptime(
                    viagem["data_fim"],
                    "%Y-%m-%d %H:%M:%S"
                )
            except ValueError:
                chegada_atual = None

        st.markdown("**Nova chegada**")
        nova_chegada = campos_data_hora(
            prefixo="prop_chegada",
            valor_inicial=chegada_atual,
            rotulo="Chegada",
            permitir_vazio=True,
            key_suffix=f"p_{viagem['id']}"
        )

        motivo = st.text_area(
            "Motivo",
            key=f"prop_motivo_{viagem['id']}"
        )

        if st.button(
            "📤 Enviar proposta",
            key=f"prop_btn_{viagem['id']}",
            type="primary"
        ):
            ok, erro = validar_datas_viagem(
                nova_saida, nova_chegada,
                contexto="proposta"
            )
            if not ok:
                st.error(erro)
            elif not motivo.strip():
                st.error("Informe o motivo.")
            else:
                try:
                    banco.criar_solicitacao_correcao(
                        viagem_id=viagem["id"],
                        usuario_id=usuario["id"],
                        nova_data_inicio=nova_saida.strftime(
                            "%Y-%m-%d %H:%M:%S"
                        ) if nova_saida else None,
                        nova_data_fim=nova_chegada.strftime(
                            "%Y-%m-%d %H:%M:%S"
                        ) if nova_chegada else None,
                        motivo=motivo
                    )
                    st.success(
                        "Proposta enviada. Aguarde a aprovação."
                    )
                    st.rerun()
                except Exception as erro:
                    st.error(f"Erro: {erro}")


# ============================================================
# FLUXO DE AUTENTICAÇÃO
# ============================================================

if not BANCO.is_file():
    st.error(
        "O sistema de acesso está temporariamente indisponível."
    )
    st.stop()

usuario_logado = st.session_state.get("usuario")

if usuario_logado is None:
    tela_acesso()
    st.stop()

if not banco.tem_permissao(
    usuario_logado["id"],
    "dashboard.visualizar"
):
    st.session_state.pop("usuario", None)
    st.error(
        "Seu usuário não possui permissão para acessar "
        "o dashboard."
    )
    if st.button("Voltar para o login"):
        st.rerun()
    st.stop()


# ============================================================
# MODO EDIÇÃO (por sessão)
# ============================================================

modo_edicao = st.session_state.get("modo_edicao", False)

perfil = perfil_do_usuario(usuario_logado["id"])
pode_editar_direto = (
    perfil == "Administrador"
    or banco.tem_permissao(
        usuario_logado["id"], "viagens.corrigir"
    )
)


# ============================================================
# CABEÇALHO AUTENTICADO
# ============================================================

cabecalho_dashboard(usuario_logado, modo_edicao=modo_edicao)


# ============================================================
# BARRA DE MODO EDIÇÃO (só para Admin)
# ============================================================

if pode_editar_direto:
    col_modo, col_info = st.columns([1, 4])

    with col_modo:
        if modo_edicao:
            if st.button(
                "🔒 Desativar modo edição",
                use_container_width=True
            ):
                st.session_state["modo_edicao"] = False
                st.rerun()
        else:
            if st.button(
                "✏️ Ativar modo edição",
                use_container_width=True,
                type="primary"
            ):
                st.session_state["modo_edicao"] = True
                st.rerun()

    with col_info:
        if modo_edicao:
            st.warning(
                "**Modo edição ativo.** Todas as balsas exibem "
                "controles para editar datas, iniciar/finalizar "
                "viagens, alterar cadastro e deletar eventos. "
                "O modo é apenas desta sessão."
            )
        else:
            st.caption(
                "Modo leitura. Clique em **Ativar modo edição** "
                "para liberar edição inline."
            )


# ============================================================
# AVISOS DE PENDÊNCIAS
# ============================================================

if banco.tem_permissao(
    usuario_logado["id"], "acessos.visualizar"
):
    n = contar_solicitacoes_pendentes()
    if n > 0:
        st.info(
            f"🔔 Você tem **{n}** solicitação(ões) de acesso "
            f"aguardando análise na aba 🔐 Autorizações."
        )

if banco.tem_permissao(
    usuario_logado["id"], "correcoes.aprovar"
):
    n = contar_correcoes_pendentes()
    if n > 0:
        st.info(
            f"✏️ Você tem **{n}** correção(ões) aguardando "
            f"análise na aba ✏️ Correções pendentes."
        )


# ============================================================
# ABAS PRINCIPAIS
# ============================================================

abas = ["📊 Painel"]

if banco.tem_permissao(
    usuario_logado["id"], "acessos.visualizar"
):
    abas.append("🔐 Autorizações")

if banco.tem_permissao(
    usuario_logado["id"], "correcoes.aprovar"
):
    abas.append("✏️ Correções pendentes")

tabs = st.tabs(abas)


# ============================================================
# ABA — PAINEL
# ============================================================

with tabs[0]:

    @st.fragment(run_every="60s")
    def painel():
        coluna_botao, coluna_status = st.columns([1, 4])

        with coluna_botao:
            atualizar_api = st.button(
                "🔄 Atualizar dados da API",
                type="primary",
                use_container_width=True
            )

        if atualizar_api:
            with st.spinner(
                "Consultando a TotalTrack e atualizando o banco..."
            ):
                try:
                    log_main = atualizar_dados_api()
                    st.session_state[
                        "ultima_atualizacao_api"
                    ] = datetime.now()
                    st.session_state["ultimo_log_main"] = log_main
                    st.success("Dados atualizados com sucesso.")
                except Exception as erro:
                    st.error(
                        "Não foi possível atualizar os dados: "
                        f"{erro}"
                    )

        with coluna_status:
            ultima_api = st.session_state.get(
                "ultima_atualizacao_api"
            )
            if ultima_api:
                st.caption(
                    "Última consulta manual à API neste painel: "
                    f"{ultima_api:%d/%m/%y %H:%M:%S}"
                )
            else:
                st.caption(
                    "A tela relê o banco a cada 60 segundos. "
                    "Use o botão ao lado para consultar novos "
                    "eventos na API TotalTrack."
                )

        if st.session_state.get("ultimo_log_main"):
            with st.expander(
                "Ver resultado da última atualização da API"
            ):
                st.code(
                    st.session_state["ultimo_log_main"],
                    language="text"
                )

        try:
            df, detalhes, viagens, eventos = carregar_painel()
        except (
            sqlite3.Error, ValueError, KeyError, TypeError
        ) as erro:
            st.error(f"Não foi possível carregar o painel: {erro}")
            st.stop()

        if df.empty:
            st.info("Nenhuma balsa ativa cadastrada.")
            return

        ultima = max(
            (e["dataGPS"] for e in eventos),
            default=None
        )

        st.caption(
            f"Painel consultado em "
            f"{datetime.now():%d/%m/%y %H:%M:%S}"
            f" · Último evento no banco: {formatar_data(ultima)}"
        )

        # ---------- Métricas ----------
        metricas = st.columns(4)
        metricas[0].metric("Balsas ativas", len(df))
        metricas[1].metric(
            "Em viagem",
            int((df["Status"] == "Em viagem").sum())
        )
        metricas[2].metric(
            "Aguardando carregamento",
            int((df["Status"] == "Aguardando carregamento").sum())
        )
        metricas[3].metric(
            "Viagens para conferir",
            sum(bool(d["aviso"]) for d in detalhes.values())
        )

        # ---------- Filtros ----------
        c1, c2, c3 = st.columns([2, 1, 1])
        busca = c1.text_input(
            "Buscar balsa ou viagem",
            placeholder="Nome ou código da viagem"
        )
        status = c2.selectbox(
            "Status",
            ["Todos"] + sorted(df["Status"].unique().tolist())
        )
        somente_alertas = c3.checkbox("Somente pendências")

        filtrado = df.copy()

        if busca:
            filtrado = filtrado[
                filtrado["Balsa"].str.contains(
                    busca, case=False, regex=False
                )
                | filtrado["Viagem"].str.contains(
                    busca, case=False, regex=False
                )
            ]

        if status != "Todos":
            filtrado = filtrado[filtrado["Status"] == status]

        if somente_alertas:
            filtrado = filtrado[
                filtrado["Conferência"]
                != "Sem alerta de sequência"
            ]

        st.dataframe(filtrado, hide_index=True, width="stretch")

        # ---------- Detalhes ----------
        st.subheader("Detalhes da balsa")
        nome = st.selectbox("Selecione a balsa", sorted(detalhes))
        d = detalhes[nome]

        situacao = d["situacao"]
        viagem = d["viagem"]
        evento = d["evento"]

        if d["aviso"]:
            st.warning(
                d["aviso"]
                + ". ETA suspenso neste painel até a conferência."
            )

        a, b, c = st.columns(3)

        a.write(
            "**Viagem:** "
            + (viagem["codigo_viagem"] if viagem else "—")
        )
        a.write(
            "**Saída registrada:** "
            + formatar_data(
                viagem.get("data_inicio") if viagem else None
            )
        )
        a.write(
            "**Carga:** "
            + str(viagem.get("carga", "—") if viagem else "—")
        )

        b.write(
            "**Prazo previsto:** "
            + (
                str(viagem["prazo_horas"]) + " h"
                if viagem
                else "—"
            )
        )
        b.write(
            "**Previsão de chegada:** "
            + (
                "Conferir viagem"
                if d["aviso"]
                else formatar_data(situacao.get("eta_destino"))
            )
        )
        b.write(
            "**Tempo restante:** "
            + str(situacao.get("tempo_restante") or "—")
        )
        b.write(
            "**Tempo excedido:** "
            + str(situacao.get("tempo_excedido") or "—")
        )

        c.write(
            "**Último evento:** " + str(evento.get("evento", "—"))
        )
        c.write("**Local:** " + str(evento.get("area", "—")))
        c.write(
            "**Data do evento:** "
            + formatar_data(evento.get("dataGPS"))
        )

        if not d["aviso"]:
            st.write(
                "**Próximo ponto previsto:** "
                + str(situacao.get("proximo_ponto") or "—")
            )
            st.write(
                "**ETA do próximo ponto:** "
                + formatar_data(situacao.get("eta_proximo_ponto"))
            )
            st.write(
                "**Fonte do ETA:** "
                + str(situacao.get("fonte_eta") or "—")
            )
        else:
            st.caption(
                "Tempos e prazo acima foram calculados "
                "com a saída registrada, que precisa "
                "de conferência."
            )

        # ---------- Ações por perfil ----------

        if (
            banco.tem_permissao(
                usuario_logado["id"], "correcoes.solicitar"
            )
            and not pode_editar_direto
        ):
            bloco_propor_correcao(nome, d, usuario_logado)

        if pode_editar_direto and modo_edicao:
            bloco_edicao_balsa(nome, d, usuario_logado)

        # ---------- Histórico ----------
        with st.expander("Histórico de viagens finalizadas"):
            historico = [
                v for v in viagens if v["data_fim"] is not None
            ]

            if historico:
                h = pd.DataFrame([
                    {
                        "Balsa": v["balsa"],
                        "Viagem": v["codigo_viagem"],
                        "Rota": v["trajeto"],
                        "Saída": formatar_data(v["data_inicio"]),
                        "Chegada": formatar_data(v["data_fim"]),
                        "Duração (h)": (
                            round(v["duracao_horas"], 2)
                            if v["duracao_horas"] is not None
                            else None
                        ),
                        "Prazo": v["status_prazo"],
                    }
                    for v in historico
                ])
                st.dataframe(h, hide_index=True, width="stretch")
            else:
                st.info("Nenhuma viagem finalizada registrada.")

    painel()


# ============================================================
# ABA — AUTORIZAÇÕES
# ============================================================

if "🔐 Autorizações" in abas:
    with tabs[abas.index("🔐 Autorizações")]:
        tela_autorizacoes(usuario_logado)


# ============================================================
# ABA — CORREÇÕES PENDENTES
# ============================================================

if "✏️ Correções pendentes" in abas:
    with tabs[abas.index("✏️ Correções pendentes")]:
        tela_correcoes(usuario_logado)




        