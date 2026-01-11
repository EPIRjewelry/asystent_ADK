import streamlit as st
from bq_analyst.agent import run_agent

st.set_page_config(page_title="ADK Agent — Streamlit", layout="centered")
st.title("EPIR Art Jewellery — Analityk BigQuery")
st.write("Agent Gemini 2.5 Flash działający bezpośrednio w chmurze (Vertex AI).")

prompt = st.text_area("W czym mogę Ci pomóc analitycznie?", height=180, placeholder="Np. Pokaż 5 najlepiej sprzedających się produktów...")

if st.button("Wyślij zapytanie do agenta"):
    if not prompt.strip():
        st.error("Proszę wpisać treść zapytania.")
    else:
        try:
            with st.spinner("Agent analizuje dane BigQuery..."):
                # Wywołanie agenta przez funkcję run_agent
                answer = run_agent(prompt)
                
            st.success("Odpowiedź agenta:")
            st.markdown(answer)
                
        except Exception as e:
            st.error(f"Wystąpił błąd podczas pracy agenta: {e}")
            st.info("Upewnij się, że usługa ma uprawnienia do BigQuery oraz Vertex AI API jest włączone.")
