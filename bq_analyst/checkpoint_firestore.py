"""
Firestore REST checkpointer for LangGraph.
Minimal persistent storage without extra client dependencies.
"""
from __future__ import annotations

import base64
import logging
from typing import Any, Iterator, Sequence

from google.auth import default as google_auth_default
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from langchain_core.runnables import RunnableConfig

from langgraph.checkpoint.base import (
    WRITES_IDX_MAP,
    BaseCheckpointSaver,
    ChannelVersions,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
    get_checkpoint_id,
    get_checkpoint_metadata,
)

logger = logging.getLogger(__name__)


def _safe_id(value: str) -> str:
    return value.replace("/", "_")


def _to_value(value: Any) -> dict:
    if value is None:
        return {"nullValue": None}
    if isinstance(value, bool):
        return {"booleanValue": value}
    if isinstance(value, int):
        return {"integerValue": str(value)}
    if isinstance(value, float):
        return {"doubleValue": value}
    if isinstance(value, bytes):
        return {"bytesValue": base64.b64encode(value).decode("ascii")}
    return {"stringValue": str(value)}


def _from_value(value: dict) -> Any:
    if "nullValue" in value:
        return None
    if "booleanValue" in value:
        return value["booleanValue"]
    if "integerValue" in value:
        return int(value["integerValue"])
    if "doubleValue" in value:
        return float(value["doubleValue"])
    if "bytesValue" in value:
        return base64.b64decode(value["bytesValue"])
    if "stringValue" in value:
        return value["stringValue"]
    return None


def _encode_fields(payload: dict[str, Any]) -> dict:
    return {"fields": {k: _to_value(v) for k, v in payload.items()}}


def _decode_fields(payload: dict) -> dict[str, Any]:
    fields = payload.get("fields", {})
    return {k: _from_value(v) for k, v in fields.items()}


class FirestoreCheckpointSaver(BaseCheckpointSaver[str]):
    """Persistent checkpointer using Firestore REST API."""

    def __init__(
        self,
        *,
        project_id: str | None = None,
        database: str = "(default)",
        checkpoints_collection: str = "langgraph_checkpoints",
        blobs_collection: str = "langgraph_blobs",
        writes_collection: str = "langgraph_writes",
        serde=None,
    ) -> None:
        super().__init__(serde=serde)
        credentials, default_project = google_auth_default(
            scopes=["https://www.googleapis.com/auth/datastore"]
        )
        self.project_id = project_id or default_project
        self.database = database
        self.base_path = f"projects/{self.project_id}/databases/{self.database}/documents"
        self.documents = build(
            "firestore",
            "v1",
            credentials=credentials,
            cache_discovery=False,
        ).projects().databases().documents()

        self.checkpoints_collection = checkpoints_collection
        self.blobs_collection = blobs_collection
        self.writes_collection = writes_collection

    def _doc_path(self, collection: str, doc_id: str) -> str:
        return f"{self.base_path}/{collection}/{doc_id}"

    def _checkpoint_doc_id(self, thread_id: str, checkpoint_ns: str, checkpoint_id: str) -> str:
        return f"{_safe_id(thread_id)}__{_safe_id(checkpoint_ns)}__{checkpoint_id}"

    def _blob_doc_id(self, thread_id: str, checkpoint_ns: str, channel: str, version: str | int | float) -> str:
        return f"{_safe_id(thread_id)}__{_safe_id(checkpoint_ns)}__{_safe_id(channel)}__{version}"

    def _write_doc_id(self, thread_id: str, checkpoint_ns: str, checkpoint_id: str, task_id: str, idx: int) -> str:
        return f"{_safe_id(thread_id)}__{_safe_id(checkpoint_ns)}__{checkpoint_id}__{_safe_id(task_id)}__{idx}"

    def _run_query(
        self,
        collection: str,
        filters: list[tuple[str, Any]],
        *,
        order_by: str | None = None,
        direction: str = "DESCENDING",
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        structured_query = {
            "from": [{"collectionId": collection}],
            "where": {
                "compositeFilter": {
                    "op": "AND",
                    "filters": [
                        {
                            "fieldFilter": {
                                "field": {"fieldPath": field},
                                "op": "EQUAL",
                                "value": _to_value(value),
                            }
                        }
                        for field, value in filters
                    ],
                }
            },
        }
        if order_by:
            structured_query["orderBy"] = [
                {"field": {"fieldPath": order_by}, "direction": direction}
            ]
        if limit is not None:
            structured_query["limit"] = limit

        response = self.documents.runQuery(
            parent=self.base_path,
            body={"structuredQuery": structured_query},
        ).execute()
        results: list[dict[str, Any]] = []
        for item in response or []:
            if "document" in item:
                results.append(item["document"])
        return results

    def _load_blobs(self, thread_id: str, checkpoint_ns: str, versions: ChannelVersions) -> dict[str, Any]:
        channel_values: dict[str, Any] = {}
        for channel, version in versions.items():
            blob_id = self._blob_doc_id(thread_id, checkpoint_ns, channel, version)
            path = self._doc_path(self.blobs_collection, blob_id)
            try:
                doc = self.documents.get(name=path).execute()
            except HttpError:
                continue
            data = _decode_fields(doc)
            blob_type = data.get("blob_type")
            blob_data = data.get("blob_data")
            if blob_type and blob_type != "empty":
                channel_values[channel] = self.serde.loads_typed((blob_type, blob_data))
        return channel_values

    def get_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        thread_id: str = config["configurable"]["thread_id"]
        checkpoint_ns: str = config["configurable"].get("checkpoint_ns", "")

        if checkpoint_id := get_checkpoint_id(config):
            doc_id = self._checkpoint_doc_id(thread_id, checkpoint_ns, checkpoint_id)
            path = self._doc_path(self.checkpoints_collection, doc_id)
            try:
                doc = self.documents.get(name=path).execute()
            except HttpError:
                return None
        else:
            docs = self._run_query(
                self.checkpoints_collection,
                [("thread_id", thread_id), ("checkpoint_ns", checkpoint_ns)],
                order_by="checkpoint_id",
                limit=1,
            )
            if not docs:
                return None
            doc = docs[0]
            checkpoint_id = _decode_fields(doc).get("checkpoint_id")

        data = _decode_fields(doc)
        checkpoint = self.serde.loads_typed((data["checkpoint_type"], data["checkpoint_data"]))
        metadata = self.serde.loads_typed((data["metadata_type"], data["metadata_data"]))
        parent_checkpoint_id = data.get("parent_checkpoint_id")

        channel_values = self._load_blobs(thread_id, checkpoint_ns, checkpoint["channel_versions"])

        writes_docs = self._run_query(
            self.writes_collection,
            [
                ("thread_id", thread_id),
                ("checkpoint_ns", checkpoint_ns),
                ("checkpoint_id", checkpoint_id),
            ],
        )
        pending_writes = []
        for write_doc in writes_docs:
            w = _decode_fields(write_doc)
            pending_writes.append(
                (
                    w.get("task_id"),
                    w.get("channel"),
                    self.serde.loads_typed((w.get("value_type"), w.get("value_data"))),
                )
            )

        result_config = (
            config
            if get_checkpoint_id(config)
            else {
                "configurable": {
                    "thread_id": thread_id,
                    "checkpoint_ns": checkpoint_ns,
                    "checkpoint_id": checkpoint_id,
                }
            }
        )

        return CheckpointTuple(
            config=result_config,
            checkpoint={
                **checkpoint,
                "channel_values": channel_values,
            },
            metadata=metadata,
            parent_config=(
                {
                    "configurable": {
                        "thread_id": thread_id,
                        "checkpoint_ns": checkpoint_ns,
                        "checkpoint_id": parent_checkpoint_id,
                    }
                }
                if parent_checkpoint_id
                else None
            ),
            pending_writes=pending_writes,
        )

    def list(
        self,
        config: RunnableConfig | None,
        *,
        filter: dict[str, Any] | None = None,
        before: RunnableConfig | None = None,
        limit: int | None = None,
    ) -> Iterator[CheckpointTuple]:
        if not config:
            docs = self._run_query(self.checkpoints_collection, [], order_by="checkpoint_id")
        else:
            thread_id = config["configurable"]["thread_id"]
            checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
            docs = self._run_query(
                self.checkpoints_collection,
                [("thread_id", thread_id), ("checkpoint_ns", checkpoint_ns)],
                order_by="checkpoint_id",
            )

        before_checkpoint_id = get_checkpoint_id(before) if before else None
        remaining = limit

        for doc in docs:
            data = _decode_fields(doc)
            checkpoint_id = data.get("checkpoint_id")
            if before_checkpoint_id and checkpoint_id >= before_checkpoint_id:
                continue

            checkpoint = self.serde.loads_typed((data["checkpoint_type"], data["checkpoint_data"]))
            metadata = self.serde.loads_typed((data["metadata_type"], data["metadata_data"]))
            if filter and not all(metadata.get(k) == v for k, v in filter.items()):
                continue

            if remaining is not None and remaining <= 0:
                break
            if remaining is not None:
                remaining -= 1

            thread_id = data["thread_id"]
            checkpoint_ns = data["checkpoint_ns"]
            channel_values = self._load_blobs(thread_id, checkpoint_ns, checkpoint["channel_versions"])

            yield CheckpointTuple(
                config={
                    "configurable": {
                        "thread_id": thread_id,
                        "checkpoint_ns": checkpoint_ns,
                        "checkpoint_id": checkpoint_id,
                    }
                },
                checkpoint={
                    **checkpoint,
                    "channel_values": channel_values,
                },
                metadata=metadata,
                parent_config=(
                    {
                        "configurable": {
                            "thread_id": thread_id,
                            "checkpoint_ns": checkpoint_ns,
                            "checkpoint_id": data.get("parent_checkpoint_id"),
                        }
                    }
                    if data.get("parent_checkpoint_id")
                    else None
                ),
                pending_writes=None,
            )

    def put(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        c = checkpoint.copy()
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")

        values: dict[str, Any] = c.pop("channel_values")  # type: ignore[misc]
        for channel, version in new_versions.items():
            if channel in values:
                blob_type, blob_data = self.serde.dumps_typed(values[channel])
            else:
                blob_type, blob_data = "empty", b""
            blob_id = self._blob_doc_id(thread_id, checkpoint_ns, channel, version)
            path = self._doc_path(self.blobs_collection, blob_id)
            self.documents.patch(
                name=path,
                body=_encode_fields(
                    {
                        "thread_id": thread_id,
                        "checkpoint_ns": checkpoint_ns,
                        "channel": channel,
                        "version": str(version),
                        "blob_type": blob_type,
                        "blob_data": blob_data,
                    }
                ),
            ).execute()

        checkpoint_type, checkpoint_data = self.serde.dumps_typed(c)
        metadata_type, metadata_data = self.serde.dumps_typed(get_checkpoint_metadata(config, metadata))
        parent_checkpoint_id = config["configurable"].get("checkpoint_id")

        doc_id = self._checkpoint_doc_id(thread_id, checkpoint_ns, checkpoint["id"])
        path = self._doc_path(self.checkpoints_collection, doc_id)
        self.documents.patch(
            name=path,
            body=_encode_fields(
                {
                    "thread_id": thread_id,
                    "checkpoint_ns": checkpoint_ns,
                    "checkpoint_id": checkpoint["id"],
                    "checkpoint_type": checkpoint_type,
                    "checkpoint_data": checkpoint_data,
                    "metadata_type": metadata_type,
                    "metadata_data": metadata_data,
                    "parent_checkpoint_id": parent_checkpoint_id,
                }
            ),
        ).execute()

        return {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_ns": checkpoint_ns,
                "checkpoint_id": checkpoint["id"],
            }
        }

    def put_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        checkpoint_id = config["configurable"]["checkpoint_id"]

        for idx, (channel, value) in enumerate(writes):
            write_idx = WRITES_IDX_MAP.get(channel, idx)
            write_id = self._write_doc_id(thread_id, checkpoint_ns, checkpoint_id, task_id, write_idx)
            value_type, value_data = self.serde.dumps_typed(value)
            payload = _encode_fields(
                {
                    "thread_id": thread_id,
                    "checkpoint_ns": checkpoint_ns,
                    "checkpoint_id": checkpoint_id,
                    "task_id": task_id,
                    "idx": write_idx,
                    "channel": channel,
                    "value_type": value_type,
                    "value_data": value_data,
                    "task_path": task_path,
                }
            )
            if write_idx >= 0:
                try:
                    self.documents.createDocument(
                        parent=self.base_path,
                        collectionId=self.writes_collection,
                        documentId=write_id,
                        body=payload,
                    ).execute()
                except HttpError as exc:
                    if exc.resp.status != 409:
                        raise
            else:
                path = self._doc_path(self.writes_collection, write_id)
                self.documents.patch(name=path, body=payload).execute()

    def delete_thread(self, thread_id: str) -> None:
        for collection in [self.checkpoints_collection, self.blobs_collection, self.writes_collection]:
            docs = self._run_query(collection, [("thread_id", thread_id)])
            for doc in docs:
                name = doc.get("name")
                if name:
                    self.documents.delete(name=name).execute()
