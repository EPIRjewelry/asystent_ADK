from google.cloud import bigquery
import os

# Upewnij się, że klucz jest ustawiony lokalnie
os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", "adk-key.json")

client = bigquery.Client(project="epir-adk-agent-v2-48a86e6f", location="us-central1")

print(f"Sprawdzam projekt: {client.project}")
print("Lista datasetów i ich lokalizacje:")

for ds in client.list_datasets():
    full_ds = client.get_dataset(ds.reference)
    print(f"- Dataset: {full_ds.dataset_id}")
    print(f"  Lokalizacja: {full_ds.location}")
