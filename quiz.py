import streamlit as st
import pandas as pd
import random
import os
from datetime import datetime

# ============================================================
#                 CONFIG DA PÁGINA
# ============================================================
st.set_page_config(
    page_title="QUIZ - Sistema Gamificado",
    page_icon="🔥",
    layout="centered"
)

# ============================================================
#                FUNÇÕES AUXILIARES
# ============================================================

def load_quiz(path="QUIZ.xlsx"):
    if not os.path.exists(path):
        st.error("Arquivo QUIZ.xlsx não encontrado!")
        st.stop()

    df = pd.read_excel(path)
    df = df.dropna(how="all")

    if "Pergunta" not in df.columns or "Resposta" not in df.columns:
        st.error("A planilha deve conter as colunas: Pergunta e Resposta.")
        st.stop()

    alternativas = [c for c in df.columns if c not in ["Pergunta", "Resposta"]]
    return df, alternativas


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


def save_result(name, score, total, xp, mode):
    path = "ranking.csv"
    now = datetime.now().strftime("%d/%m/%Y %H:%M")

    new_row = pd.DataFrame([{
        "Nome": name,
        "Modo": mode,
        "Pontuação": score,
        "Total": total,
        "Porcentagem": round((score / total) * 100, 2),
        "XP": xp,
        "Data": now
    }])

    if os.path.exists(path):
        old = pd.read_csv(path)
        df = pd.concat([old, new_row], ignore_index=True)
    else:
        df = new_row

    df.to_csv(path, index=False)


def load_ranking():
    if os.path.exists("ranking.csv"):
        return pd.read_csv("ranking.csv")
    return pd.DataFrame(columns=["Nome", "Modo", "Pontuação", "Total", "Porcentagem", "XP", "Data"])


def get_level(xp):
    return xp // 200


# ============================================================
#               MENU PRINCIPAL
# ============================================================
st.title("🔥 Quiz Gamificado - GeekHub Edition")

menu = st.sidebar.radio(
    "Navegação",
    ["🏁 Jogar Quiz", "⚔️ Batalha 1x1", "🏅 Ranking Geral"]
)

df, alt_cols = load_quiz("QUIZ.xlsx")

# ============================================================
#            SISTEMA DE ESTADO — SEM RESET
# ============================================================

if "quiz_data" not in st.session_state:
    st.session_state.quiz_data = None
if "cur_q" not in st.session_state:
    st.session_state.cur_q = 0
if "answers" not in st.session_state:
    st.session_state.answers = []
if "mode" not in st.session_state:
    st.session_state.mode = None


# ============================================================
#                    MODO QUIZ NORMAL
# ============================================================
if menu == "🏁 Jogar Quiz":

    if st.session_state.mode != "quiz":
        st.session_state.quiz_data = None
        st.session_state.cur_q = 0
        st.session_state.answers = []
        st.session_state.mode = "quiz"

    st.header("📘 Iniciar Quiz")

    name = st.text_input("Seu nome:")
    dificuldade = st.selectbox("Dificuldade", ["Fácil", "Médio", "Difícil"])
    qtd = st.slider("Quantidade de questões", 5, min(30, len(df)), 10)

    if st.button("COMEÇAR 🔥") and name:
        st.session_state.quiz_data = df.sample(qtd).reset_index(drop=True)
        st.session_state.cur_q = 0
        st.session_state.answers = []

    # ----- Se o quiz já começou -----
    if st.session_state.quiz_data is not None:

        cur = st.session_state.cur_q
        perguntas = st.session_state.quiz_data

        if cur < len(perguntas):

            row = perguntas.iloc[cur]
            opts, correct = shuffle_options(row, alt_cols)

            st.subheader(f"❓ Questão {cur+1}/{len(perguntas)}")

            choice = st.radio(row["Pergunta"], opts, key=f"quiz_{cur}")

            if st.button("Confirmar resposta"):
                st.session_state.answers.append(choice)
                st.session_state.cur_q += 1
                st.rerun()

        else:
            # ---- FINAL ----
            score = sum(
                1 for i, row in enumerate(perguntas.itertuples())
                if st.session_state.answers[i] == str(row.Resposta).strip()
            )

            xp_gain = {
                "Fácil": 10,
                "Médio": 20,
                "Difícil": 40
            }[dificuldade] * score

            st.success(f"Você fez {score}/{len(perguntas)} acertos!")
            st.info(f"Ganhou **{xp_gain} XP**")

            save_result(name, score, len(perguntas), xp_gain, "Quiz Normal")

            if st.button("Refazer Quiz"):
                for key in ["quiz_data", "answers", "cur_q", "mode"]:
                    st.session_state[key] = None
                st.rerun()


# ============================================================
#              MODO 2 — BATALHA 1x1 (SEM BUGS)
# ============================================================
if menu == "⚔️ Batalha 1x1":

    if st.session_state.mode != "battle":
        st.session_state.quiz_data = None
        st.session_state.cur_q = 0
        st.session_state.answers = []
        st.session_state.mode = "battle"

    st.header("⚔️ Batalha 1x1")

    p1 = st.text_input("Jogador 1")
    p2 = st.text_input("Jogador 2")
    qtd = st.slider("Quantidade de questões", 5, 30, 10)

    if st.button("INICIAR BATALHA ⚔️") and p1 and p2:
        st.session_state.quiz_data = df.sample(qtd).reset_index(drop=True)
        st.session_state.cur_q = 0
        st.session_state.answers = []

    if st.session_state.quiz_data is not None:

        cur = st.session_state.cur_q
        perguntas = st.session_state.quiz_data

        if cur < len(perguntas):

            row = perguntas.iloc[cur]
            opts, correct = shuffle_options(row, alt_cols)

            st.subheader(f"❓ Questão {cur+1}/{len(perguntas)}")

            col1, col2 = st.columns(2)

            with col1:
                r1 = st.radio(p1, opts, key=f"b1_{cur}")
            with col2:
                r2 = st.radio(p2, opts, key=f"b2_{cur}")

            if st.button("Confirmar respostas"):
                st.session_state.answers.append((r1, r2))
                st.session_state.cur_q += 1
                st.rerun()

        else:
            # ---- FINAL ----
            score1 = 0
            score2 = 0

            for i, row in enumerate(perguntas.itertuples()):
                correct = str(row.Resposta).strip()
                r1, r2 = st.session_state.answers[i]
                if r1 == correct:
                    score1 += 1
                if r2 == correct:
                    score2 += 1

            st.success(f"🎉 Resultado: {p1} {score1} x {score2} {p2}")

            xp1 = score1 * 25
            xp2 = score2 * 25

            save_result(p1, score1, len(perguntas), xp1, "Batalha")
            save_result(p2, score2, len(perguntas), xp2, "Batalha")

            if score1 > score2:
                st.success(f"🏆 {p1} venceu!")
            elif score2 > score1:
                st.success(f"🏆 {p2} venceu!")
            else:
                st.info("🤝 Empate!")

            if st.button("Nova Batalha"):
                for key in ["quiz_data", "answers", "cur_q", "mode"]:
                    st.session_state[key] = None
                st.rerun()


# ============================================================
#                 RANKING GERAL
# ============================================================
if menu == "🏅 Ranking Geral":
    st.header("🏅 Ranking Geral")

    ranking = load_ranking()

    if ranking.empty:
        st.info("Nenhum jogo registrado ainda.")
        st.stop()

    ranking["XP Total"] = ranking.groupby("Nome")["XP"].transform("sum")

    unique = ranking[["Nome", "XP Total"]].drop_duplicates()
    unique["Nível"] = unique["XP Total"] // 200
    unique = unique.sort_values("XP Total", ascending=False)

    st.dataframe(unique)

    for i, row in unique.head(3).iterrows():
        medal = ["🥇", "🥈", "🥉"][i]
        st.markdown(f"### {medal} {row['Nome']} — {row['XP Total']} XP (Nível {row['Nível']})")
