import streamlit as st
from bq_analyst.agent import run_agent

st.set_page_config(page_title="ADK Agent — Streamlit", layout="centered")
st.title("EPIR Art Jewellery — Analityk BigQuery")
st.write("Agent Gemini 3 Flash działający bezpośrednio w chmurze (Vertex AI).")

prompt = st.text_area("W czym mogę Ci pomóc analitycznie?", height=180, placeholder="Np. Pokaż 5 najlepiej sprzedających się produktów...")

if "history" not in st.session_state:
    st.session_state.history = []

if st.button("Wyślij zapytanie do agenta"):
    if not prompt.strip():
        st.error("Proszę wpisać treść zapytania.")
    else:
        try:
            with st.spinner("Agent analizuje dane BigQuery..."):
                # Wywołanie agenta przez funkcję run_agent
                answer, response_obj = run_agent(prompt)
                thought_trace = ""
                if response_obj:
                    candidates = getattr(response_obj, "candidates", None)
                    if candidates:
                        parts = []
                        for candidate in candidates:
                            content = getattr(candidate, "content", None)
                            if content:
                                parts.append(str(content))
                        thought_trace = "\n---\n".join(parts) if parts else str(response_obj)
                    else:
                        thought_trace = str(response_obj)
                else:
                    thought_trace = "Brak danych o procesie myślowym."
                st.session_state.history.append({
                    "prompt": prompt,
                    "answer": answer,
                    "thoughts": thought_trace,
                })
                
            st.success("Odpowiedź agenta:")
            st.markdown(answer)
                
        except Exception as e:
            st.error(f"Wystąpił błąd podczas pracy agenta: {e}")
            st.info("Upewnij się, że usługa ma uprawnienia do BigQuery oraz Vertex AI API jest włączone.")
    
    if st.session_state.history:
        st.markdown("### Historia rozmów")
        for entry in st.session_state.history:
            st.markdown(f"**Ty:** {entry['prompt']}")
            st.markdown(f"**Agent:** {entry['answer']}")
            with st.expander("Proces myślowy (Thought Trace)"):
                st.code(entry["thoughts"])
