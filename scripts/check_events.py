from google.cloud import bigquery


def main() -> None:
    # Wymuszamy region us-central1 zgodnie z lokalizacją datasetu
    client = bigquery.Client(project="epir-adk-agent-v2-48a86e6f", location="us-central1")
    query = """
SELECT
    COUNT(*) as total_events,
    MAX(created_at) as latest_event,
    COUNTIF(created_at > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)) as events_last_hour
FROM
    `epir-adk-agent-v2-48a86e6f.analytics_435783047.events_raw`
"""
    job = client.query(query)
    rows = list(job.result())
    for row in rows:
        print(dict(row))


if __name__ == "__main__":
    main()