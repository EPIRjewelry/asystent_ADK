# Frontend React dla EPIR Analyst ADK

Nowoczesny interfejs webowy do komunikacji z agentem analitycznym BigQuery.

## 🚀 Uruchomienie lokalne

```bash
cd frontend
npm install
npm run dev
```

Aplikacja uruchomi się na `http://localhost:3000`.

## 🔧 Konfiguracja

Przed uruchomieniem ustaw URL backendu:

### Opcja 1: Zmienna środowiskowa
```bash
export VITE_API_URL=https://twoj-backend.a.run.app
npm run dev
```

### Opcja 2: Edytuj src/App.jsx
Zmień wartość `API_URL` na początku pliku na swój adres Cloud Run.

## 📦 Build produkcyjny

```bash
npm run build
```

Zbudowane pliki znajdziesz w `frontend/dist/`.

## 🌐 Deployment

### Firebase Hosting (zalecane)
```bash
npm install -g firebase-tools
firebase login
firebase init hosting
npm run build
firebase deploy
```

### Cloud Storage jako statyczna strona
```bash
npm run build
gsutil -m rsync -r dist/ gs://twoj-bucket
gsutil web set -m index.html -e index.html gs://twoj-bucket
```

## 🎨 Funkcje

- ✅ Chat interface z dymkami
- ✅ Obsługa sesji (thread_id)
- ✅ Wyświetlanie metadanych (kroki, narzędzia)
- ✅ Responsywny design
- ✅ Przykładowe pytania (quick actions)
- ✅ Przycisk "Nowa rozmowa"
