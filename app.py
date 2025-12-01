import streamlit as st
import pandas as pd

df = pd.read_excel("QUIZ.xlsx")

st.title("Quiz – App Web")

for index, row in df.iterrows():
    st.subheader(row["Pergunta"])

    opc = st.radio("Escolha:", [
        row["Opção1"],
        row["Opção2"],
        row["Opção3"],
        row["Opção4"]
    ], key=index)

    if opc == row["Resposta"]:
        st.success("✔️ Resposta correta!")
    else:
        st.error("❌ Resposta incorreta!")
