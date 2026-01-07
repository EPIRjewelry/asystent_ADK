# asystent_ADK

Projekt asystent_ADK to agent analityczny oparty na Google ADK oraz BigQuery. Pozwala budować zapytania SQL do danych analitycznych, wykorzystując agenta opartego o model Gemini.

## Struktura projektu

```
requirements.txt
bq_analyst/
    __init__.py
    agent.py
scripts/
    check_events.py
    check_dataset.py
query.sql
```

## Instalacja

1. Sklonuj repozytorium:
    ```bash
    git clone https://github.com/EPIRjewelry/asystent_ADK.git
    ```
2. Zainstaluj wymagane pakiety:
    ```bash
    pip install -r requirements.txt
    ```

## Użycie

Kod agenta znajduje się w pliku `bq_analyst/agent.py`. Uruchomienie (Windows, w wirtualnym środowisku):
```bash
.venv\Scripts\python bq_analyst/agent.py
```

### Skrypty pomocnicze
- `scripts/check_events.py` – sprawdza liczbę zdarzeń i znacznik czasu ostatniego zdarzenia.
- `scripts/check_dataset.py` – sprawdza metadane datasetu (lokalizację).
- `query.sql` – przykładowe zapytanie do liczenia zdarzeń i ostatniego timestampu.

## Wymagania

- Python 3.10+
- Zależności z `requirements.txt` (uwzględniono google-adk, google-cloud-bigquery itd.).

## Bezpieczeństwo
- Plik klucza serwisowego `adk-key.json` jest wykluczony w `.gitignore`. Nie commituj kluczy ani sekretów.
