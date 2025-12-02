import streamlit as st
import pandas as pd
import random
import io
from datetime import datetime
import os

# Configuração da página
st.set_page_config(page_title="Quiz Interativo", page_icon="📘", layout="centered")

# ---------- Funções Auxiliares (Helpers) ----------
def load_quiz(path="QUIZ.xlsx"):
    # Verifica se o arquivo existe antes de tentar abrir
    if not os.path.exists(path):
        st.error(f"O arquivo '{path}' não foi encontrado. Verifique se ele está no repositório.")
        st.stop()
        
    try:
        df = pd.read_excel(path)
    except Exception as e:
        st.error(f"Erro ao ler o arquivo Excel: {e}")
        st.stop()

    # Garante colunas esperadas
    cols = list(df.columns)
    if "Pergunta" not in cols or "Resposta" not in cols:
        st.error("A planilha deve conter as colunas obrigatórias: 'Pergunta' e 'Resposta'.")
        st.stop()
        
    # Coleta colunas de alternativas (todas exceto Pergunta e Resposta)
    alt_cols = [c for c in cols if c not in ("Pergunta", "Resposta")]
    
    # Remove linhas vazias para evitar erros
    df = df.dropna(how='all')
    
    return df, alt_cols

def make_question_item(row, alt_cols):
    opts = []
    # Preferência por colunas canônicas A..E se existirem
    canonical = ["A","B","C","D","E"]
    if set(canonical).issubset(set(alt_cols)):
        for col in canonical:
            if pd.notna(row.get(col)): opts.append(str(row[col]).strip())
    else:
        for col in alt_cols:
            if pd.notna(row.get(col)): opts.append(str(row[col]).strip())
            
    # Garante que a resposta correta esteja inclusa
    correct = str(row["Resposta"]).strip()
    if correct not in opts:
        opts.append(correct)
        
    # Remove duplicatas mantendo a ordem e embaralha
    opts = list(dict.fromkeys(opts))
    random.shuffle(opts)
    return opts, correct

def to_csv_bytes(results_df):
    buffer = io.StringIO()
    results_df.to_csv(buffer, index=False)
    return buffer.getvalue().encode('utf-8')

# ---------- Carregamento de Dados ----------
with st.spinner("Carregando perguntas..."):
    df, alt_cols = load_quiz("QUIZ.xlsx")

if df.empty:
    st.warning("A planilha foi carregada mas não contém perguntas.")
    st.stop()

# ---------- Barra Lateral / Configurações ----------
st.sidebar.title("Configurações")
qtd_default = min(10, len(df))
qtd = st.sidebar.number_input("Quantas questões?", min_value=1, max_value=len(df), value=qtd_default, step=1)
mode = st.sidebar.selectbox("Modo", ["Treino (feedback imediato)", "Prova (mostrar nota só no final)"])
shuffle_questions = st.sidebar.checkbox("Embaralhar perguntas", value=True)
show_progress = st.sidebar.checkbox("Mostrar barra de progresso", value=True)

if st.sidebar.button("Reiniciar Quiz"):
    for key in st.session_state.keys():
        del st.session_state[key]
    st.rerun()

st.title("📘 Quiz Interativo")
st.markdown("Escolha a quantidade de questões na barra lateral e clique em **Iniciar**.")

# ---------- Estado da Sessão (Session State) ----------
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

# ---------- Iniciar Quiz ----------
if not st.session_state.started:
    if st.button("Iniciar Quiz", type="primary"):
        # Lógica de seleção
        if shuffle_questions:
            pool = df.sample(n=len(df)).reset_index(drop=True)
        else:
            pool = df.copy().reset_index(drop=True)
            
        st.session_state.order = pool.iloc[:qtd].reset_index(drop=True)
        st.session_state.index = 0
        st.session_state.picks = [None] * qtd
        st.session_state.correct_count = 0
        st.session_state.shuffled_options = [None] * qtd
        st.session_state.started = True
        st.rerun()
    else:
        st.info("Configure as opções ao lado e clique em **Iniciar Quiz**.")
        st.stop()

# ---------- Fluxo do Quiz ----------
cur_i = st.session_state.index
total_q = len(st.session_state.order)

# Tela de Finalização
if cur_i >= total_q:
    # CORREÇÃO 1: Evitar divisão por zero
    if total_q > 0:
        percent = (st.session_state.correct_count / total_q) * 100
    else:
        percent = 0.0
        
    st.success(f"Quiz finalizado — você acertou {st.session_state.correct_count} de {total_q} ({percent:.1f}%)")
    st.write("---")
    st.subheader("Detalhes e Gabarito")
    
    # Construir dataframe de resultados
    rows = []
    for i in range(total_q):
        row_data = st.session_state.order.iloc[i]
        # Recupera opções salvas ou vazio
        pick = st.session_state.picks[i]
        correct = str(row_data["Resposta"]).strip()
        
        rows.append({
            "N°": i+1,
            "Pergunta": row_data["Pergunta"],
            "Sua Escolha": pick if pick is not None else "Não respondido",
            "Correta": correct,
            "Acertou": (pick == correct)
        })
        
    results_df = pd.DataFrame(rows)
    
    # CORREÇÃO 2: Substituir applymap (depreciado) por map e corrigir KeyError
    def highlight_correct(val):
        return 'background-color: #d4edda' if val is True else ''

    st.dataframe(
        results_df.style.map(highlight_correct, subset=["Acertou"]),
        use_container_width=True
    )
    
    # Botão de exportação
    csv_bytes = to_csv_bytes(results_df)
    st.download_button("📥 Exportar resultados (CSV)", data=csv_bytes, file_name="quiz_result.csv", mime="text/csv")
    
    if st.button("Refazer Quiz"):
        st.session_state.started = False
        st.session_state.index = 0
        st.session_state.picks = []
        st.session_state.correct_count = 0
        st.session_state.shuffled_options = []
        st.rerun()
    st.stop()

# Mostrar questão atual
row = st.session_state.order.iloc[cur_i]
st.header(f"Questão {cur_i+1} / {total_q}")
st.write(row["Pergunta"])

# Preparar opções e armazenar na sessão
if st.session_state.shuffled_options[cur_i] is None:
    opts, correct = make_question_item(row, alt_cols)
    st.session_state.shuffled_options[cur_i] = opts
else:
    opts = st.session_state.shuffled_options[cur_i]
    correct = str(row["Resposta"]).strip()

# Exibir opções com letras (A, B, C...)
letters = [chr(65 + i) for i in range(len(opts))]
labelled_opts = [f"{letters[i]}) {opts[i]}" for i in range(len(opts))]

# Recuperar escolha prévia para manter o radio button correto
initial_choice_text = st.session_state.picks[cur_i] # Ex: "Resposta X"
initial_index = 0

# Lógica para encontrar o índice correto baseado no texto salvo
if initial_choice_text is not None:
    # Procura qual opção termina com o texto salvo
    for idx, opt_label in enumerate(labelled_opts):
        if opt_label.endswith(f") {initial_choice_text}"):
            initial_index = idx
            break

choice = st.radio(
    "Escolha uma alternativa:", 
    options=labelled_opts, 
    index=initial_index, 
    key=f"q_radio_{cur_i}"
)

# Salvar seleção na sessão (apenas o texto, sem "A) ")
if ") " in choice:
    selected_text = choice.split(") ", 1)[1]
else:
    selected_text = choice

st.session_state.picks[cur_i] = selected_text

# Barra de progresso
if show_progress:
    progress = (cur_i) / total_q if total_q > 0 else 0
    st.progress(progress)

# Navegação e Lógica de Modos
if mode.startswith("Treino"):
    if st.button("Confirmar resposta e próxima"):
        if selected_text == correct:
            st.success("✔️ Correto!")
            st.session_state.correct_count += 1
        else:
            st.error("❌ Incorreto")
            st.markdown(f"Resposta correta: **{correct}**")
            
        st.session_state.index += 1
        st.rerun()
else:
    # Modo Prova
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("Anterior") and cur_i > 0:
            st.session_state.index -= 1
            st.rerun()
    with col3:
        if st.button("Próxima"):
            st.session_state.index += 1
            st.rerun()
            
    st.write("---")
    if st.button("Finalizar prova e ver resultado", type="primary"):
        # Calcular pontuação final
        correct_count = 0
        for i in range(total_q):
            r_row = st.session_state.order.iloc[i]
            # Garante comparação segura de strings
            r_correct = str(r_row["Resposta"]).strip()
            r_pick = st.session_state.picks[i]
            
            if r_pick == r_correct:
                correct_count += 1
                
        st.session_state.correct_count = correct_count
        st.session_state.index = total_q # Força ir para tela final
        st.rerun()


