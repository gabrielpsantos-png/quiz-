import streamlit as st
import pandas as pd
import random
import os
import hashlib
import json
import time # Importado para o Timer
from datetime import datetime

# ============================================================
#                  CONFIG DA PÁGINA
# ============================================================
st.set_page_config(
    page_title="QUIZ - Sistema Gamificado",
    page_icon="🔥",
    layout="centered"
)

USERS_FILE = "users.csv"
DESAFIOS_FILE = "desafios.csv"
RANKING_FILE = "ranking.csv"
QUIZ_FILE = "QUIZ.xlsx"

# ============================================================
#                  FUNÇÕES AUXILIARES
# ============================================================

def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def load_users():
    if not os.path.exists(USERS_FILE):
        df = pd.DataFrame(columns=["usuario", "senha_hash", "data"])
        df.to_csv(USERS_FILE, index=False)
        return df
    return pd.read_csv(USERS_FILE)

def save_user(usuario, senha):
    df = load_users()
    if usuario in df["usuario"].values:
        return False
    new_row = pd.DataFrame([{
        "usuario": usuario,
        "senha_hash": hash_password(senha),
        "data": datetime.now().strftime("%d/%m/%Y %H:%M")
    }])
    df = pd.concat([df, new_row], ignore_index=True)
    df.to_csv(USERS_FILE, index=False)
    return True

def login(usuario, senha):
    df = load_users()
    senha_hash = hash_password(senha)
    if usuario in df["usuario"].values:
        row = df[df["usuario"] == usuario].iloc[0]
        if row["senha_hash"] == senha_hash:
            return True
    return False

def load_quiz(path=QUIZ_FILE):
    if not os.path.exists(path):
        st.error("Arquivo QUIZ.xlsx não encontrado! Crie um arquivo Excel com colunas 'Pergunta' e 'Resposta'.")
        st.stop()

    df = pd.read_excel(path).dropna(how="all")

    if "Pergunta" not in df.columns or "Resposta" not in df.columns:
        st.error("A planilha deve conter as colunas: Pergunta e Resposta.")
        st.stop()

    alt_cols = [c for c in df.columns if c not in ["Pergunta", "Resposta"]]
    return df, alt_cols

def shuffle_options(row, alt_cols):
    opts = []
    for col in alt_cols:
        if pd.notna(row[col]):
            opts.append(str(row[col]).strip())

    correct = str(row["Resposta"]).strip()

    if correct not in opts:
        opts.append(correct)

    opts = list(dict.fromkeys(opts))
    random.shuffle(opts)

    return opts, correct

def save_result(usuario, score, total, xp, modo):
    now = datetime.now().strftime("%d/%m/%Y %H:%M")

    new_row = pd.DataFrame([{
        "usuario": usuario,
        "modo": modo,
        "score": score,
        "total": total,
        "porcentagem": round((score/total)*100, 2),
        "xp": xp,
        "data": now
    }])

    if os.path.exists(RANKING_FILE):
        df = pd.read_csv(RANKING_FILE)
        df = pd.concat([df, new_row], ignore_index=True)
    else:
        df = new_row

    df.to_csv(RANKING_FILE, index=False)

def load_ranking():
    if os.path.exists(RANKING_FILE):
        return pd.read_csv(RANKING_FILE)
    return pd.DataFrame(columns=["usuario","modo","score","total","porcentagem","xp","data"])


# ============================================================
#                   SISTEMA DE LOGIN
# ============================================================

if "user" not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None:
    st.title("🔥 Login no Quiz Gamificado")

    aba = st.radio("Escolha:", ["Entrar", "Criar Conta"])

    if aba == "Entrar":
        user = st.text_input("Usuário")
        pw = st.text_input("Senha", type="password")

        if st.button("Entrar"):
            if login(user, pw):
                st.session_state.user = user
                st.success("Login realizado!")
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")

    else:
        user = st.text_input("Novo usuário")
        pw = st.text_input("Senha", type="password")

        if st.button("Criar Conta"):
            if save_user(user, pw):
                st.success("Conta criada! Faça login.")
            else:
                st.error("Usuário já existe.")

    st.stop()

# ============================================================
#            USUÁRIO LOGADO
# ============================================================

st.sidebar.success(f"Logado como: {st.session_state.user}")
if st.sidebar.button("Sair"):
    st.session_state.user = None
    st.rerun()

menu = st.sidebar.radio(
    "Navegação",
    ["🏁 Jogar Quiz", "⚔️ Desafiar Jogador", "📥 Desafios Recebidos", "🏅 Ranking Geral"]
)

df, alt_cols = load_quiz()


# ============================================================
#                     JOGAR QUIZ NORMAL
# ============================================================

if "quiz_data" not in st.session_state:
    st.session_state.quiz_data = None
if "cur_q" not in st.session_state:
    st.session_state.cur_q = 0
if "answers" not in st.session_state:
    st.session_state.answers = []
if "start_time" not in st.session_state:
    st.session_state.start_time = None
if "time_limit" not in st.session_state:
    st.session_state.time_limit = 0

if menu == "🏁 Jogar Quiz":

    # --- CONFIGURAÇÃO INICIAL DO QUIZ ---
    if st.session_state.quiz_data is None:
        st.header("📘 Configuração do Quiz")

        col1, col2 = st.columns(2)
        with col1:
            dificuldade = st.selectbox("Dificuldade", ["Fácil", "Médio", "Difícil"])
        with col2:
            # ADAPTAÇÃO 2: Escolha de segundos por questão
            segundos = st.number_input("Segundos por questão (0 = Sem tempo)", min_value=0, max_value=300, value=0, step=5)

        max_q = min(30, len(df))
        qtd = st.slider("Quantidade de questões", 1, max_q, 5)

        if st.button("COMEÇAR 🔥"):
            raw = df.sample(qtd).reset_index(drop=True)
            prepared = []

            for idx, row in raw.iterrows():
                opts, correct = shuffle_options(row, alt_cols)
                prepared.append({
                    "pergunta": row["Pergunta"],
                    "opcoes": opts,
                    "resposta": correct
                })

            st.session_state.quiz_data = prepared
            st.session_state.cur_q = 0
            st.session_state.answers = []
            st.session_state.difficulty = dificuldade
            st.session_state.time_limit = segundos # Salva o tempo limite
            st.session_state.start_time = None # Reseta o timer
            st.rerun()

    # --- EXECUÇÃO DO QUIZ ---
    else:
        cur = st.session_state.cur_q
        perguntas = st.session_state.quiz_data
        limit = st.session_state.time_limit

        if cur < len(perguntas):
            q = perguntas[cur]

            # Inicia o timer se ainda não iniciou para essa questão
            if st.session_state.start_time is None:
                st.session_state.start_time = time.time()

            # Mostra progresso e timer
            st.progress(cur/len(perguntas))
            
            # Cabeçalho com Timer
            col_h1, col_h2 = st.columns([3, 1])
            with col_h1:
                st.subheader(f"❓ Questão {cur+1}/{len(perguntas)}")
            with col_h2:
                if limit > 0:
                    st.markdown(f"⏱️ **Limite: {limit}s**")

            st.write(f"**{q['pergunta']}**")

            choice = st.radio("Escolha:", q["opcoes"], key=f"quiz_{cur}")

            if st.button("Confirmar resposta"):
                # Verifica Tempo
                tempo_esgotado = False
                if limit > 0:
                    elapsed = time.time() - st.session_state.start_time
                    if elapsed > limit:
                        tempo_esgotado = True
                        st.toast("⚠️ Tempo esgotado! Resposta anulada.", icon="⏰")
                
                # Lógica de salvar resposta
                if tempo_esgotado:
                    st.session_state.answers.append("TEMPO_ESGOTADO")
                else:
                    st.session_state.answers.append(choice)

                # Prepara próxima questão
                st.session_state.cur_q += 1
                st.session_state.start_time = None # Reseta timer para próxima
                st.rerun()

        # --- TELA DE RESULTADOS ---
        else:
            score = 0
            # Calcula score ignorando timeouts e erros
            for i, p in enumerate(perguntas):
                if st.session_state.answers[i] == p["resposta"]:
                    score += 1

            xp_gain = {"Fácil": 10, "Médio": 20, "Difícil": 40}[st.session_state.difficulty]
            xp_gain *= score

            st.balloons()
            st.success(f"Fim de jogo! Você acertou {score} de {len(perguntas)}.")
            st.info(f"XP ganho: **{xp_gain} XP**")

            # Salva no Ranking
            save_result(st.session_state.user, score, len(perguntas), xp_gain, "Quiz Normal")

            # ADAPTAÇÃO 1: Mostrar Detalhes (Erros e Acertos)
            st.write("---")
            st.subheader("📝 Revisão da Partida")
            
            for i, p in enumerate(perguntas):
                user_ans = st.session_state.answers[i]
                correct_ans = p["resposta"]
                
                with st.expander(f"Questão {i+1}: {p['pergunta']}"):
                    if user_ans == correct_ans:
                        st.markdown(f"✅ **Você acertou!** Resposta: {user_ans}")
                    elif user_ans == "TEMPO_ESGOTADO":
                        st.markdown(f"⏰ **Tempo Esgotado!**")
                        st.markdown(f"A resposta correta era: **{correct_ans}**")
                    else:
                        st.markdown(f"❌ **Você errou.** Sua escolha: {user_ans}")
                        st.markdown(f"A resposta correta era: **{correct_ans}**")

            st.write("---")
            if st.button("Jogar Novamente"):
                st.session_state.quiz_data = None
                st.session_state.cur_q = 0
                st.session_state.answers = []
                st.session_state.start_time = None
                st.rerun()


# ============================================================
#                  DESAFIAR OUTRO JOGADOR
# ============================================================
# (Mantido igual, apenas para contexto)

def load_desafios():
    if not os.path.exists(DESAFIOS_FILE):
        return pd.DataFrame(columns=["id","desafiante","desafiado","status","perguntas","resp1","resp2"])
    return pd.read_csv(DESAFIOS_FILE)

def save_desafios(df):
    df.to_csv(DESAFIOS_FILE, index=False)

if menu == "⚔️ Desafiar Jogador":
    st.header("⚔️ Desafiar Jogador")
    ranking = load_ranking()
    usuarios = ranking["usuario"].drop_duplicates().tolist()
    usuarios = [u for u in usuarios if u != st.session_state.user]

    if not usuarios:
        st.info("Nenhum jogador disponível para desafiar.")
        st.stop()

    desafiado = st.selectbox("Escolha o jogador:", usuarios)
    qtd = st.slider("Quantidade de questões:", 3, 20, 5)

    if st.button("Enviar Desafio ⚔️"):
        raw = df.sample(qtd).reset_index(drop=True)
        perguntas = []
        for _, row in raw.iterrows():
            opts, correct = shuffle_options(row, alt_cols)
            perguntas.append({
                "pergunta": row["Pergunta"],
                "opcoes": opts,
                "correta": correct
            })

        desafios = load_desafios()
        novo = pd.DataFrame([{
            "id": len(desafios)+1,
            "desafiante": st.session_state.user,
            "desafiado": desafiado,
            "status": "pendente",
            "perguntas": json.dumps(perguntas),
            "resp1": "",
            "resp2": ""
        }])
        desafios = pd.concat([desafios, novo], ignore_index=True)
        save_desafios(desafios)
        st.success("Desafio enviado!")

# ============================================================
#                  DESAFIOS RECEBIDOS (RESUMO)
# ============================================================
if menu == "📥 Desafios Recebidos":
    st.header("📥 Desafios Recebidos")
    desafios = load_desafios()
    meus = desafios[(desafios["desafiado"] == st.session_state.user) & (desafios["status"] == "pendente")]

    if meus.empty:
        st.info("Nenhum desafio recebido.")
        st.stop()

    id_select = st.selectbox("Desafios pendentes (ID):", meus["id"].tolist())
    row = meus[meus["id"] == id_select].iloc[0]
    perguntas = json.loads(row["perguntas"])

    if "duelo_q" not in st.session_state:
        st.session_state.duelo_q = 0
        st.session_state.duelo_ans = []

    cur = st.session_state.duelo_q

    if cur < len(perguntas):
        q = perguntas[cur]
        st.subheader(f"Questão {cur+1}/{len(perguntas)}")
        st.write(f"**{q['pergunta']}**")
        choice = st.radio("Selecione:", q["opcoes"], key=f"dq{cur}")
        if st.button("Responder"):
            st.session_state.duelo_ans.append(choice)
            st.session_state.duelo_q += 1
            st.rerun()
    else:
        corretas = 0
        for i, q in enumerate(perguntas):
            if st.session_state.duelo_ans[i] == q["correta"]:
                corretas += 1
        
        # Atualiza CSV
        desafios.loc[desafios["id"] == id_select, "resp2"] = ";".join(st.session_state.duelo_ans)
        desafios.loc[desafios["id"] == id_select, "status"] = "respondido"
        save_desafios(desafios)
        
        # Salva Ranking
        xp = corretas * 30
        save_result(st.session_state.user, corretas, len(perguntas), xp, "Desafio Recebido")
        
        # MOSTRA RESULTADO DO DUELO
        st.success(f"Desafio concluído! Acertos: {corretas}/{len(perguntas)}")
        
        # RESET
        st.session_state.duelo_q = 0
        st.session_state.duelo_ans = []

# ============================================================
#                       RANKING GERAL
# ============================================================
if menu == "🏅 Ranking Geral":
    st.header("🏅 Ranking Geral")
    ranking = load_ranking()
    if ranking.empty:
        st.info("Nenhum jogo registrado ainda.")
    else:
        ranking["xp_total"] = ranking.groupby("usuario")["xp"].transform("sum")
        unique = ranking[["usuario","xp_total"]].drop_duplicates()
        unique["nivel"] = unique["xp_total"] // 200
        unique = unique.sort_values("xp_total", ascending=False).reset_index(drop=True)
        st.dataframe(unique, use_container_width=True)

