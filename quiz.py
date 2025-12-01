# quiz.py
import streamlit as st
import pandas as pd
import random
import io
from datetime import datetime

st.set_page_config(page_title="Quiz Interativo", page_icon="📘", layout="centered")

# ---------- Helpers ----------
def load_quiz(path="QUIZ.xlsx"):
    df = pd.read_excel(path)
    # Ensure expected columns: Pergunta, Resposta (certa) and alternatives
    cols = list(df.columns)
    if "Pergunta" not in cols or "Resposta" not in cols:
        st.error("Planilha deve conter as colunas 'Pergunta' e 'Resposta'.")
        st.stop()
    # Collect alternative columns (all except Pergunta and Resposta)
    alt_cols = [c for c in cols if c not in ("Pergunta", "Resposta")]
    return df, alt_cols

def make_question_item(row, alt_cols):
    # Build list of options (keep non-empty)
    opts = []
    # prefer canonical A..E if present, else use all alt_cols
    if set(["A","B","C","D","E"]).issubset(set(alt_cols)):
        for col in ["A","B","C","D","E"]:
            if pd.notna(row.get(col)): opts.append(str(row[col]))
    else:
        for col in alt_cols:
            if pd.notna(row.get(col)): opts.append(str(row[col]))
    # ensure correct answer included
    correct = str(row["Resposta"])
    if correct not in opts:
        opts.append(correct)
    # remove duplicates and shuffle
    opts = list(dict.fromkeys(opts))
    random.shuffle(opts)
    return opts, correct

def to_csv_bytes(results_df):
    buffer = io.StringIO()
    results_df.to_csv(buffer, index=False)
    return buffer.getvalue().encode('utf-8')

# ---------- Load data ----------
with st.spinner("Carregando perguntas..."):
    try:
        df, alt_cols = load_quiz("QUIZ.xlsx")
    except Exception as e:
        st.stop()

# ---------- Sidebar / settings ----------
st.sidebar.title("Configurações")
qtd_default = min(10, len(df))
qtd = st.sidebar.number_input("Quantas questões?", min_value=1, max_value=len(df), value=qtd_default, step=1)
mode = st.sidebar.selectbox("Modo", ["Treino (feedback imediato)", "Prova (mostrar nota só no final)"])
shuffle_questions = st.sidebar.checkbox("Embaralhar perguntas", value=True)
show_progress = st.sidebar.checkbox("Mostrar barra de progresso", value=True)
add_timer = st.sidebar.checkbox("Tempo por questão (segundos) — experimental", value=False)

st.title("📘 Quiz Interativo")
st.markdown("Escolha a quantidade de questões, clique em **Iniciar** e responda. Ao final, veja resultado e exporte o gabarito.")

# ---------- Session state ----------
if "started" not in st.session_state:
    st.session_state.started = False
if "order" not in st.session_state:
    st.session_state.order = []
if "index" not in st.session_state:
    st.session_state.index = 0
if "picks" not in st.session_state:
    st.session_state.picks = []
if "correct_count" not in st.session_state:
    st.session_state.correct_count = 0
if "shuffled_options" not in st.session_state:
    st.session_state.shuffled_options = []
if "start_time" not in st.session_state:
    st.session_state.start_time = None

# ---------- Start quiz ----------
if not st.session_state.started:
    if st.button("Iniciar Quiz"):
        pool = df.sample(len(df)).reset_index(drop=True) if shuffle_questions else df.copy().reset_index(drop=True)
        st.session_state.order = pool.iloc[:qtd].reset_index(drop=True)
        st.session_state.index = 0
        st.session_state.picks = [None] * qtd
        st.session_state.correct_count = 0
        st.session_state.shuffled_options = [None] * qtd
        st.session_state.started = True
        st.session_state.start_time = datetime.now().isoformat()
        st.experimental_rerun()
    else:
        st.info("Clique em **Iniciar Quiz** na barra esquerda quando estiver pronto.")
        st.stop()

# ---------- Quiz flow ----------
cur_i = st.session_state.index
total_q = len(st.session_state.order)

if cur_i >= total_q:
    # Finished
    st.success(f"Quiz finalizado — você acertou {st.session_state.correct_count} de {total_q} ({(st.session_state.correct_count/total_q)*100:.1f}%)")
    st.write("---")
    st.subheader("Detalhes e Gabarito")
    # Build results dataframe
    rows = []
    for i in range(total_q):
        row = st.session_state.order.iloc[i]
        opts = st.session_state.shuffled_options[i] or []
        pick = st.session_state.picks[i]
        correct = str(row["Resposta"])
        rows.append({
            "N°": i+1,
            "Pergunta": row["Pergunta"],
            "Escolha": pick if pick is not None else "",
            "Correta": correct,
            "Acertou": (pick == correct)
        })
    results_df = pd.DataFrame(rows)
    # Visual summary
    st.dataframe(results_df.style.applymap(lambda v: 'background-color: #d4edda' if v is True else None, subset=["Acertou"]))
    # Export CSV button
    csv_bytes = to_csv_bytes(results_df)
    st.download_button("📥 Exportar resultados (CSV)", data=csv_bytes, file_name="quiz_result.csv", mime="text/csv")
    # Reset button
    if st.button("Refazer Quiz"):
        st.session_state.started = False
        st.session_state.index = 0
        st.session_state.picks = []
        st.session_state.correct_count = 0
        st.session_state.shuffled_options = []
        st.experimental_rerun()
    st.stop()

# Show current question
row = st.session_state.order.iloc[cur_i]
st.header(f"Questão {cur_i+1} / {total_q}")
st.write(row["Pergunta"])

# Prepare options & store them in session so UI remains stable across reruns
if st.session_state.shuffled_options[cur_i] is None:
    opts, correct = make_question_item(row, alt_cols)
    st.session_state.shuffled_options[cur_i] = opts
else:
    opts = st.session_state.shuffled_options[cur_i]
    correct = str(row["Resposta"])

# Option display (lettered)
letters = [chr(65 + i) for i in range(len(opts))]
labelled_opts = [f"{letters[i]}) {opts[i]}" for i in range(len(opts))]

# If user already picked, select that radio option
initial_choice = None
if st.session_state.picks[cur_i] is not None:
    initial_choice = st.session_state.picks[cur_i]

choice = st.radio("Escolha uma alternativa:", options=labelled_opts, index=labelled_opts.index(initial_choice) if initial_choice in labelled_opts else 0, key=f"q{cur_i}")

# Save selection into session-friendly plaintext (strip "X) " prefix)
selected_text = choice.split(") ", 1)[1] if ") " in choice else choice
st.session_state.picks[cur_i] = selected_text

# Show progress
if show_progress:
    progress = (cur_i) / total_q
    st.progress(progress)

# Immediate feedback in training mode
if mode.startswith("Treino"):
    if st.button("Confirmar resposta e próxima"):
        if selected_text == correct:
            st.success("✔️ Correto!")
            st.session_state.correct_count += 1
        else:
            st.error("❌ Incorreto")
            st.write(f"Resposta correta: **{correct}**")
        st.session_state.index += 1
        st.experimental_rerun()
else:
    # Prova mode: just navigate
    col1, col2, col3 = st.columns([1,2,1])
    with col1:
        if st.button("Anterior") and cur_i > 0:
            st.session_state.index -= 1
            st.experimental_rerun()
    with col3:
        if st.button("Próxima"):
            st.session_state.index += 1
            st.experimental_rerun()
    st.write("---")
    if st.button("Finalizar prova e ver resultado"):
        # compute score
        correct_count = 0
        for i in range(total_q):
            row_i = st.session_state.order.iloc[i]
            if st.session_state.picks[i] == str(row_i["Resposta"]):
                correct_count += 1
        st.session_state.correct_count = correct_count
        st.session_state.index = total_q
        st.experimental_rerun()
