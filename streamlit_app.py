import streamlit as st
from bq_analyst.agent import root_agent

st.set_page_config(page_title="ADK Agent — Streamlit", layout="centered")
st.title("ADK Agent — Pełna Wersja (Streamlit)")
st.write("Agent Gemini 3 Flash działający bezpośrednio w chmurze (EPIR Art Jewellery).")

prompt = st.text_area("W czym mogę Ci pomóc analitycznie?", height=180, placeholder="Np. Pokaż 5 najlepiej sprzedających się produktów...")

if st.button("Wyślij zapytanie do agenta"):
    if not prompt.strip():
        st.error("Proszę wpisać treść zapytania.")
    else:
        try:
            with st.spinner("Agent analizuje dane BigQuery..."):
                # Wywołanie agenta bezpośrednio (bez HTTP API)
                result = root_agent.run(prompt)
                
                # Przetwarzanie wyniku AgentResult
                answer = getattr(result, "output", None) or getattr(result, "response", None) or str(result)
                
            st.success("Odpowiedź agenta:")
            st.markdown(answer)
            
            # Opcjonalny wgląd w proces myślowy
            with st.expander("Proces myślowy (Thought Trace)"):
                st.write(result)
                
        except Exception as e:
            st.error(f"Wystąpił błąd podczas pracy agenta: {e}")
            st.info("Upewnij się, że usługa ma uprawnienia do BigQuery oraz Vertex AI API jest włączone.")
