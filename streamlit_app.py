import os
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

DEFAULT_ENDPOINT = os.getenv("ADK_REMOTE_ENDPOINT", "")

st.set_page_config(page_title="ADK Agent — Streamlit", layout="centered")
st.title("ADK Agent — prosty frontend (Streamlit)")
st.write("Użyj tego prostego interfejsu, by wysyłać zapytania do Twojego agenta na Cloud Run.")

endpoint = st.text_input("Endpoint (np. https://asystent-adk-...)", value=DEFAULT_ENDPOINT)
prompt = st.text_area("Treść zapytania", height=180)
show_raw = st.checkbox("Pokaż surową odpowiedź JSON")

if st.button("Wyślij"):
    if not endpoint:
        st.error("Podaj adres endpointa (ADK_REMOTE_ENDPOINT lub ręcznie).")
    elif not prompt.strip():
        st.error("Wpisz treść zapytania.")
    else:
        try:
            with st.spinner("Wysyłam zapytanie..."):
                url = endpoint.rstrip("/") + "/chat"
                resp = requests.post(url, json={"text": prompt}, timeout=30)
                resp.raise_for_status()
                data = resp.json()
            st.success("Odpowiedź otrzymana")
            if show_raw:
                st.json(data)
            else:
                if isinstance(data, dict) and "response" in data:
                    st.markdown("**Agent:**\n\n" + str(data.get("response")))
                else:
                    st.write(data)
        except requests.exceptions.RequestException as e:
            st.error(f"Błąd połączenia: {e}")
        except ValueError:
            st.error("Nie udało się sparsować odpowiedzi jako JSON.")
