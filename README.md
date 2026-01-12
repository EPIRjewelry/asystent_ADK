# EPIR BigQuery Analyst Agent

Agent analityczny oparty na **Vertex AI + LangGraph + FastAPI**, zaprojektowany do inteligentnej analizy danych BigQuery dla EPIR Art Jewellery.

## 🏗️ Architektura

- **Vertex AI Agent Engine**: Pełna orkiestracja agenta z pętlą myślową (Reasoning Loop)
- **LangGraph**: Grafy stanów z pamięcią sesji i self-correction
- **FastAPI**: Produkcyjne REST API kompatybilne z Cloud Run
- **BigQuery Tools**: Bezpośredni dostęp do danych przez natywne narzędzia
- **MemorySaver**: Kontekst konwersacji w sesji wieloturowej

## 📁 Struktura projektu

```
asystent_ADK/
├── bq_analyst/
│   ├── __init__.py
│   ├── config.py         # Konfiguracja ENV (12-Factor App)
│   ├── agent.py          # LangGraph Agent + Tools
│   ├── main.py           # FastAPI Server
│   └── mcp_adapter.py    # MCP compatibility layer
├── scripts/              # Utility scripts
├── requirements.txt      # Dependencies
├── Dockerfile            # Production container
└── README.md
```

## 🚀 Deployment na Cloud Run

### 1. Lokalne przygotowanie (Cloud Shell)

```bash
git clone https://github.com/EPIRjewelry/asystent_ADK.git
cd asystent_ADK
```

### 2. Build i deploy

```bash
# Build kontenera
gcloud builds submit --tag gcr.io/epir-adk-agent-v2-48a86e6f/bq-analyst-agent

# Deploy na Cloud Run
gcloud run deploy bq-analyst-agent \
  --image gcr.io/epir-adk-agent-v2-48a86e6f/bq-analyst-agent \
  --platform managed \
  --region global \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_CLOUD_PROJECT=epir-adk-agent-v2-48a86e6f,GOOGLE_CLOUD_LOCATION=global,MODEL_NAME=publishers/google/models/gemini-3-flash-preview
```

### 3. Testowanie

```bash
# Health check
curl https://YOUR_CLOUD_RUN_URL/health

# Zapytanie do agenta
curl -X POST https://YOUR_CLOUD_RUN_URL/agent/query \
  -H "Content-Type: application/json" \
  -d '{"text": "Pokaż dostępne datasety w BigQuery"}'
```

## 📡 API Endpoints

| Endpoint | Metoda | Opis |
|----------|--------|------|
| `/` | GET | Health check |
| `/health` | GET | Status serwisu |
| `/agent/query` | POST | Główny endpoint zapytań |
| `/agent/history/{thread_id}` | GET | Historia konwersacji |
| `/chat` | POST | Legacy endpoint (kompatybilność) |

### Przykład zapytania

```json
POST /agent/query
{
  "text": "Ile mamy rekordów w tabeli sprzedaży?",
  "thread_id": "session-123"  // opcjonalne
}
```

### Odpowiedź

```json
{
  "response": "W tabeli sprzedaży znajduje się 15847 rekordów.",
  "thread_id": "session-123",
  "metadata": {
    "steps": 7,
    "tool_calls": 2,
    "tool_results": 2
  }
}
```

## 🔧 Konfiguracja

Wszystkie ustawienia ładowane są z **zmiennych środowiskowych Cloud Run**:

| Zmienna | Default | Opis |
|---------|---------|------|
| `GOOGLE_CLOUD_PROJECT` | `epir-adk-agent-v2-48a86e6f` | ID projektu GCP |
| `GOOGLE_CLOUD_LOCATION` | `global` | Region Vertex AI |
| `MODEL_NAME` | `publishers/google/models/gemini-3-flash-preview` | Model LLM |
| `AGENT_RECURSION_LIMIT` | `15` | Maksymalna głębokość pętli |
| `AGENT_TEMPERATURE` | `0.0` | Temperatura modelu (deterministyczność) |
| `LOG_LEVEL` | `INFO` | Poziom logowania |
| `PORT` | `8080` | Port HTTP |

## 🛠️ Lokalna instalacja (opcjonalnie)

```bash
# Zainstaluj zależności
pip install -r requirements.txt

# Ustaw zmienne środowiskowe
export GOOGLE_CLOUD_PROJECT=epir-adk-agent-v2-48a86e6f
export GOOGLE_CLOUD_LOCATION=global

# Uruchom lokalnie
python -m bq_analyst.main
```

## 🔒 Bezpieczeństwo

- **IAM Authentication**: Uwierzytelnianie przez Service Account w Cloud Run
- **Non-root Container**: Kontener uruchamiany jako user `appuser` (UID 1000)
- **SQL Injection Protection**: Blokada operacji modyfikujących dane (INSERT/UPDATE/DELETE/DROP)
- **CORS**: Domyślnie `allow_origins=["*"]` — ogranicz w produkcji do konkretnych domen

## 📊 Narzędzia agenta

Agent ma dostęp do następujących narzędzi BigQuery:

1. **`list_datasets()`** — Listuje dostępne datasety
2. **`list_tables(dataset_id)`** — Listuje tabele w datasecie
3. **`get_table_schema(dataset_id, table_id)`** — Pobiera schemat tabeli
4. **`execute_sql(query)`** — Wykonuje zapytania SQL (READ-ONLY)

## 🧠 Zalety architektury LangGraph

- **Self-Correction**: Agent automatycznie naprawia błędy SQL
- **Context Awareness**: Pamięć sesji między zapytaniami
- **Tool Orchestration**: Inteligentne wybieranie narzędzi
- **Observability**: Pełne logowanie kroków i wywołań narzędzi

## 📝 Licencja

Proprietary - EPIR Art Jewellery

## 🆘 Wsparcie

W razie problemów skontaktuj się z zespołem DevOps lub otwórz Issue w repozytorium GitHub.


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
