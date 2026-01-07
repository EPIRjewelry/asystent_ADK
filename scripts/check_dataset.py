from google.cloud import bigquery


def main() -> None:
    # Wymuszamy region us-central1 zgodnie z lokalizacją datasetu
    client = bigquery.Client(project="epir-adk-agent-v2-48a86e6f", location="us-central1")
    dataset_id = "analytics_435783047"
    dataset_ref = client.dataset(dataset_id)
    try:
        dataset = client.get_dataset(dataset_ref)
        print("Dataset location:", dataset.location)
    except Exception as exc:
        print("Failed to fetch dataset metadata:", exc)


if __name__ == "__main__":
    main()