import streamlit as st
import pandas as pd
import random
import io
from datetime import datetime
import os

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
    if "Pergunta" not in df.columns or "Resposta" not in df.columns:
        st.error("A planilha deve conter as colunas: Pergunta e Resposta.")
        st.stop()

    alt_cols = [c for c in df.columns if c not in ["Pergunta", "Resposta"]]
    df = df.dropna(how="all")
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

def save_result(name, score, total, xp, mode):
    path = "ranking.csv"
    now = datetime.now().strftime("%d/%m/%Y %H:%M")

    new_row = {
        "Nome": name,
        "Modo": mode,
        "Pontuação": score,
        "Total": total,
        "Porcentagem": round((score / total) * 100, 2),
        "XP": xp,
        "Data": now
    }

    if os.path.exists(path):
        old = pd.read_csv(path)
        df = pd.concat([old, pd.DataFrame([new_row])], ignore_index=True)
    else:
        df = pd.DataFrame([new_row])

    df.to_csv(path, index=False)


def load_ranking():
    if os.path.exists("ranking.csv"):
        return pd.read_csv("ranking.csv")
    return pd.DataFrame(columns=["Nome", "Modo", "Pontuação", "Total", "Porcentagem", "XP", "Data"])


def get_level(xp):
    level = xp // 200
    return level


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
#                MODO 1 — QUIZ NORMAL
# ============================================================
if menu == "🏁 Jogar Quiz":

    st.header("📘 Iniciar Quiz")

    name = st.text_input("Seu nome:")
    dificuldade = st.selectbox("Dificuldade", ["Fácil", "Médio", "Difícil"])
    qtd = st.slider("Quantidade de questões", 5, min(30, len(df)), 10)

    iniciar = st.button("COMEÇAR 🔥")

    if iniciar:
        if not name:
            st.error("Digite seu nome para iniciar.")
            st.stop()

        perguntas = df.sample(qtd).reset_index(drop=True)

        score = 0

        for i in range(qtd):
            st.subheader(f"❓ Questão {i+1}/{qtd}")
            row = perguntas.iloc[i]
            opts, correct = shuffle_options(row, alt_cols)

            choice = st.radio(row["Pergunta"], opts)
            if choice == correct:
                score += 1

        st.success(f"Você acertou {score}/{qtd} ({score/qtd*100:.1f}%)")

        # XP por dificuldade
        xp_gain = {
            "Fácil": 10,
            "Médio": 20,
            "Difícil": 40
        }[dificuldade] * score

        st.info(f"XP ganho: **{xp_gain} XP**")

        save_result(name, score, qtd, xp_gain, mode="Quiz Normal")

        st.balloons()



# ============================================================
#              MODO 2 — BATALHA 1x1
# ============================================================
if menu == "⚔️ Batalha 1x1":

    st.header("⚔️ Batalha de Conhecimento 1 vs 1")

    p1 = st.text_input("Jogador 1")
    p2 = st.text_input("Jogador 2")
    qtd = st.slider("Quantidade de questões", 5, 30, 10)

    iniciar = st.button("INICIAR BATALHA ⚔️")

    if iniciar:
        if not p1 or not p2:
            st.error("Informe os nomes dos jogadores.")
            st.stop()

        perguntas = df.sample(qtd).reset_index(drop=True)
        score1 = score2 = 0

        for i in range(qtd):
            row = perguntas.iloc[i]
            opts, correct = shuffle_options(row, alt_cols)

            st.subheader(f"❓ Questão {i+1}/{qtd}")

            col1, col2 = st.columns(2)

            with col1:
                resp1 = st.radio(f"{p1}", opts, key=f"{i}_1")
            with col2:
                resp2 = st.radio(f"{p2}", opts, key=f"{i}_2")

            if resp1 == correct:
                score1 += 1
            if resp2 == correct:
                score2 += 1

        st.success(f"🎉 Resultado: {p1} {score1} x {score2} {p2}")

        xp1 = score1 * 25
        xp2 = score2 * 25

        save_result(p1, score1, qtd, xp1, "Batalha")
        save_result(p2, score2, qtd, xp2, "Batalha")

        if score1 > score2:
            st.success(f"🏆 **{p1} VENCEU A BATALHA!**")
        elif score2 > score1:
            st.success(f"🏆 **{p2} VENCEU A BATALHA!**")
        else:
            st.info("🤝 EMPATE")


# ============================================================
#                 RANKING GERAL
# ============================================================
if menu == "🏅 Ranking Geral":
    st.header("🏅 Ranking Geral de Jogadores")

    ranking = load_ranking()

    if ranking.empty:
        st.info("Ainda não há resultados registrados.")
        st.stop()

    # Ordenar por XP total
    ranking["XP Total"] = ranking.groupby("Nome")["XP"].transform("sum")
    ranking_unique = ranking[["Nome", "XP Total"]].drop_duplicates()
    ranking_unique = ranking_unique.sort_values("XP Total", ascending=False).reset_index(drop=True)

    # Adicionar níveis
    ranking_unique["Nível"] = ranking_unique["XP Total"].apply(get_level)

    st.dataframe(ranking_unique)

    # Medalhas
    for i, row in ranking_unique.head(3).iterrows():
        medal = ["🥇", "🥈", "🥉"][i]
        st.markdown(f"### {medal} {row['Nome']} — {row['XP Total']} XP (Nível {row['Nível']})")

