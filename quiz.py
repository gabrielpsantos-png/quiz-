import streamlit as st
import pandas as pd
import random
import os
from datetime import datetime

# ============================================================
#                  CONFIG DA PÁGINA
# ============================================================
st.set_page_config(
    page_title="QUIZ - Sistema Gamificado",
    page_icon="🔥",
    layout="centered"
)

# ============================================================
#                 FUNÇÕES AUXILIARES
# ============================================================

def load_quiz(path="QUIZ.xlsx"):
    if not os.path.exists(path):
        # Cria um arquivo de exemplo se não existir para evitar erro ao testar
        data = {
            'Pergunta': ['Quanto é 2+2?', 'Capital da França?', 'Cor do céu?'],
            'Resposta': ['4', 'Paris', 'Azul'],
            'Opcao1': ['3', 'Londres', 'Verde'],
            'Opcao2': ['5', 'Berlim', 'Roxo'],
            'Opcao3': ['6', 'Madri', 'Amarelo']
        }
        df_exemplo = pd.DataFrame(data)
        df_exemplo.to_excel(path, index=False)
        st.warning(f"Arquivo {path} não existia e foi criado um exemplo. Recarregue a página.")
    
    df = pd.read_excel(path)
    df = df.dropna(how="all")

    if "Pergunta" not in df.columns or "Resposta" not in df.columns:
        st.error("A planilha deve conter as colunas: Pergunta e Resposta.")
        st.stop()

    alternativas = [c for c in df.columns if c not in ["Pergunta", "Resposta"]]
    return df, alternativas


def shuffle_options(row, alt_cols):
    """Gera as opções embaralhadas e retorna (lista_opcoes, resposta_correta)"""
    opts = []
    
    for col in alt_cols:
        if pd.notna(row[col]):
            opts.append(str(row[col]).strip())

    correct = str(row["Resposta"]).strip()
    
    # Se a resposta correta não estiver nas opções (ex: planilha mal formatada), adiciona ela
    if correct not in opts:
        opts.append(correct)

    # Remove duplicatas mantendo a ordem (só por segurança)
    opts = list(dict.fromkeys(opts))
    
    # O PULO DO GATO: O embaralhamento acontece aqui, mas só chamaremos esta função UMA VEZ por jogo
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

# ============================================================
#                MENU PRINCIPAL
# ============================================================
st.title("🔥 Quiz Gamificado - GeekHub Edition")

menu = st.sidebar.radio(
    "Navegação",
    ["🏁 Jogar Quiz", "⚔️ Batalha 1x1", "🏅 Ranking Geral"]
)

df, alt_cols = load_quiz("QUIZ.xlsx")

# ============================================================
#            SISTEMA DE ESTADO
# ============================================================

if "quiz_data" not in st.session_state:
    st.session_state.quiz_data = None  # Agora guardará uma LISTA de dicionários já processados
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

    # Reseta se mudar de modo
    if st.session_state.mode != "quiz":
        st.session_state.quiz_data = None
        st.session_state.cur_q = 0
        st.session_state.answers = []
        st.session_state.mode = "quiz"

    st.header("📘 Iniciar Quiz")

    if st.session_state.quiz_data is None:
        # TELA DE CONFIGURAÇÃO (Só aparece se o jogo não começou)
        name = st.text_input("Seu nome:")
        dificuldade = st.selectbox("Dificuldade", ["Fácil", "Médio", "Difícil"])
        max_q = min(30, len(df))
        qtd = st.slider("Quantidade de questões", 1, max_q, min(5, max_q))

        if st.button("COMEÇAR 🔥"):
            if not name:
                st.warning("Digite seu nome para começar!")
            else:
                # ---------------------------------------------------------
                # CORREÇÃO AQUI: PREPARAMOS OS DADOS ANTES DE SALVAR NO STATE
                # ---------------------------------------------------------
                raw_questions = df.sample(qtd).reset_index(drop=True)
                prepared_quiz = []

                for idx, row in raw_questions.iterrows():
                    opts, correct = shuffle_options(row, alt_cols)
                    prepared_quiz.append({
                        "pergunta": row["Pergunta"],
                        "opcoes": opts,       # Ordem fixa para este jogo
                        "resposta": correct
                    })
                
                st.session_state.quiz_data = prepared_quiz
                st.session_state.cur_q = 0
                st.session_state.answers = []
                st.session_state.user_name = name # Guardar nome no state
                st.session_state.difficulty = dificuldade # Guardar diff no state
                st.rerun()

    else:
        # JOGO EM ANDAMENTO
        cur = st.session_state.cur_q
        perguntas = st.session_state.quiz_data # Esta é a lista preparada

        if cur < len(perguntas):
            # Pegamos a pergunta JÁ processada do state
            q_data = perguntas[cur]
            
            st.progress((cur) / len(perguntas))
            st.subheader(f"❓ Questão {cur+1}/{len(perguntas)}")
            st.write(f"**{q_data['pergunta']}**")

            # O st.radio usa a lista 'opcoes' que já foi embaralhada lá no começo e não muda mais
            choice = st.radio("Escolha uma alternativa:", q_data['opcoes'], key=f"quiz_{cur}")

            if st.button("Confirmar resposta"):
                st.session_state.answers.append(choice)
                st.session_state.cur_q += 1
                st.rerun()

        else:
            # TELA FINAL
            score = 0
            for i, p_data in enumerate(perguntas):
                user_ans = st.session_state.answers[i]
                correct_ans = p_data['resposta']
                if user_ans == correct_ans:
                    score += 1
            
            diff = st.session_state.get("difficulty", "Fácil")
            xp_gain = {
                "Fácil": 10,
                "Médio": 20,
                "Difícil": 40
            }[diff] * score

            st.balloons()
            st.success(f"Você fez {score}/{len(perguntas)} acertos!")
            st.info(f"Ganhou **{xp_gain} XP**")

            save_result(st.session_state.user_name, score, len(perguntas), xp_gain, "Quiz Normal")

            if st.button("Jogar Novamente"):
                st.session_state.quiz_data = None
                st.session_state.cur_q = 0
                st.session_state.answers = []
                st.rerun()


# ============================================================
#               MODO 2 — BATALHA 1x1
# ============================================================
if menu == "⚔️ Batalha 1x1":

    if st.session_state.mode != "battle":
        st.session_state.quiz_data = None
        st.session_state.cur_q = 0
        st.session_state.answers = []
        st.session_state.mode = "battle"

    st.header("⚔️ Batalha 1x1")

    if st.session_state.quiz_data is None:
        p1 = st.text_input("Nome Jogador 1")
        p2 = st.text_input("Nome Jogador 2")
        max_q = min(30, len(df))
        qtd = st.slider("Quantidade de questões", 1, max_q, min(5, max_q))

        if st.button("INICIAR BATALHA ⚔️"):
            if p1 and p2:
                # MESMA CORREÇÃO: PREPARAR DADOS ANTES
                raw_questions = df.sample(qtd).reset_index(drop=True)
                prepared_quiz = []

                for idx, row in raw_questions.iterrows():
                    opts, correct = shuffle_options(row, alt_cols)
                    prepared_quiz.append({
                        "pergunta": row["Pergunta"],
                        "opcoes": opts,
                        "resposta": correct
                    })

                st.session_state.quiz_data = prepared_quiz
                st.session_state.cur_q = 0
                st.session_state.answers = []
                st.session_state.p1_name = p1
                st.session_state.p2_name = p2
                st.rerun()
            else:
                st.warning("Preencha os nomes dos dois jogadores.")

    else:
        # BATALHA EM ANDAMENTO
        cur = st.session_state.cur_q
        perguntas = st.session_state.quiz_data

        if cur < len(perguntas):
            q_data = perguntas[cur]

            st.progress((cur) / len(perguntas))
            st.subheader(f"❓ Questão {cur+1}/{len(perguntas)}")
            st.write(f"**{q_data['pergunta']}**")

            col1, col2 = st.columns(2)

            with col1:
                st.markdown(f"**{st.session_state.p1_name}**")
                # Opções fixas vindas do state
                r1 = st.radio("Sua resposta:", q_data['opcoes'], key=f"b1_{cur}")
            
            with col2:
                st.markdown(f"**{st.session_state.p2_name}**")
                # Opções fixas vindas do state
                r2 = st.radio("Sua resposta:", q_data['opcoes'], key=f"b2_{cur}")

            if st.button("Confirmar respostas"):
                st.session_state.answers.append((r1, r2))
                st.session_state.cur_q += 1
                st.rerun()

        else:
            # RESULTADO BATALHA
            score1 = 0
            score2 = 0

            for i, p_data in enumerate(perguntas):
                correct = p_data['resposta']
                r1, r2 = st.session_state.answers[i]
                
                if r1 == correct: score1 += 1
                if r2 == correct: score2 += 1

            p1 = st.session_state.p1_name
            p2 = st.session_state.p2_name

            st.success(f"🎉 Placar Final: {p1} ({score1}) x ({score2}) {p2}")

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
                st.session_state.quiz_data = None
                st.session_state.cur_q = 0
                st.session_state.answers = []
                st.rerun()

# ============================================================
#                  RANKING GERAL
# ============================================================
if menu == "🏅 Ranking Geral":
    st.header("🏅 Ranking Geral")
    ranking = load_ranking()

    if ranking.empty:
        st.info("Nenhum jogo registrado ainda.")
    else:
        # Agrupamento para somar XP
        ranking["XP Total"] = ranking.groupby("Nome")["XP"].transform("sum")
        
        # Remove duplicatas de nome para mostrar o ranking consolidado
        unique = ranking[["Nome", "XP Total"]].drop_duplicates()
        unique["Nível"] = unique["XP Total"] // 200
        unique = unique.sort_values("XP Total", ascending=False).reset_index(drop=True)

        st.dataframe(unique, use_container_width=True)

        st.markdown("---")
        st.subheader("Top 3 Jogadores")
        for i, row in unique.head(3).iterrows():
            medal = ["🥇", "🥈", "🥉"][i]
            st.markdown(f"### {medal} {row['Nome']} — {row['XP Total']} XP (Nível {row['Nível']})")
