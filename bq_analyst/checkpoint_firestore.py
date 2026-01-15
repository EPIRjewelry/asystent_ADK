"""
Firestore checkpoint saver for LangGraph.
Minimal persistent storage for thread memory in Cloud Run.
"""
from __future__ import annotations

import logging
from typing import Any, Iterator, Sequence

from google.cloud import firestore
from google.api_core.exceptions import AlreadyExists
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


class FirestoreCheckpointSaver(BaseCheckpointSaver[str]):
    """Persistent checkpointer using Cloud Firestore (Native)."""

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
        self.client = firestore.Client(project=project_id, database=database)
        self.checkpoints = self.client.collection(checkpoints_collection)
        self.blobs = self.client.collection(blobs_collection)
        self.writes = self.client.collection(writes_collection)

    def _checkpoint_doc_id(self, thread_id: str, checkpoint_ns: str, checkpoint_id: str) -> str:
        return f"{_safe_id(thread_id)}__{_safe_id(checkpoint_ns)}__{checkpoint_id}"

    def _blob_doc_id(self, thread_id: str, checkpoint_ns: str, channel: str, version: str | int | float) -> str:
        return f"{_safe_id(thread_id)}__{_safe_id(checkpoint_ns)}__{_safe_id(channel)}__{version}"

    def _write_doc_id(self, thread_id: str, checkpoint_ns: str, checkpoint_id: str, task_id: str, idx: int) -> str:
        return f"{_safe_id(thread_id)}__{_safe_id(checkpoint_ns)}__{checkpoint_id}__{_safe_id(task_id)}__{idx}"

    def _load_blobs(self, thread_id: str, checkpoint_ns: str, versions: ChannelVersions) -> dict[str, Any]:
        channel_values: dict[str, Any] = {}
        for channel, version in versions.items():
            blob_id = self._blob_doc_id(thread_id, checkpoint_ns, channel, version)
            doc = self.blobs.document(blob_id).get()
            if not doc.exists:
                continue
            data = doc.to_dict() or {}
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
            doc = self.checkpoints.document(doc_id).get()
            if not doc.exists:
                return None
        else:
            query = (
                self.checkpoints
                .where("thread_id", "==", thread_id)
                .where("checkpoint_ns", "==", checkpoint_ns)
                .order_by("checkpoint_id", direction=firestore.Query.DESCENDING)
                .limit(1)
            )
            docs = list(query.stream())
            if not docs:
                return None
            doc = docs[0]
            checkpoint_id = doc.to_dict().get("checkpoint_id")

        data = doc.to_dict() or {}
        checkpoint = self.serde.loads_typed((data["checkpoint_type"], data["checkpoint_data"]))
        metadata = self.serde.loads_typed((data["metadata_type"], data["metadata_data"]))
        parent_checkpoint_id = data.get("parent_checkpoint_id")

        channel_values = self._load_blobs(thread_id, checkpoint_ns, checkpoint["channel_versions"])

        writes_query = (
            self.writes
            .where("thread_id", "==", thread_id)
            .where("checkpoint_ns", "==", checkpoint_ns)
            .where("checkpoint_id", "==", checkpoint_id)
        )
        pending_writes = []
        for write_doc in writes_query.stream():
            w = write_doc.to_dict() or {}
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
            query = self.checkpoints.order_by("checkpoint_id", direction=firestore.Query.DESCENDING)
        else:
            thread_id = config["configurable"]["thread_id"]
            checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
            query = (
                self.checkpoints
                .where("thread_id", "==", thread_id)
                .where("checkpoint_ns", "==", checkpoint_ns)
                .order_by("checkpoint_id", direction=firestore.Query.DESCENDING)
            )

        before_checkpoint_id = get_checkpoint_id(before) if before else None
        remaining = limit

        for doc in query.stream():
            data = doc.to_dict() or {}
            checkpoint_id = data.get("checkpoint_id")
            if before_checkpoint_id and checkpoint_id >= before_checkpoint_id:
                continue

            checkpoint = self.serde.loads_typed((data["checkpoint_type"], data["checkpoint_data"]))
            metadata = self.serde.loads_typed((data["metadata_type"], data["metadata_data"]))
            if filter and not all(metadata.get(k) == v for k, v in filter.items()):
                continue

            thread_id = data["thread_id"]
            checkpoint_ns = data["checkpoint_ns"]
            channel_values = self._load_blobs(thread_id, checkpoint_ns, checkpoint["channel_versions"])

            if remaining is not None and remaining <= 0:
                break
            if remaining is not None:
                remaining -= 1

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
            self.blobs.document(blob_id).set(
                {
                    "thread_id": thread_id,
                    "checkpoint_ns": checkpoint_ns,
                    "channel": channel,
                    "version": version,
                    "blob_type": blob_type,
                    "blob_data": blob_data,
                },
                merge=True,
            )

        checkpoint_type, checkpoint_data = self.serde.dumps_typed(c)
        metadata_type, metadata_data = self.serde.dumps_typed(get_checkpoint_metadata(config, metadata))
        parent_checkpoint_id = config["configurable"].get("checkpoint_id")

        doc_id = self._checkpoint_doc_id(thread_id, checkpoint_ns, checkpoint["id"])
        self.checkpoints.document(doc_id).set(
            {
                "thread_id": thread_id,
                "checkpoint_ns": checkpoint_ns,
                "checkpoint_id": checkpoint["id"],
                "checkpoint_type": checkpoint_type,
                "checkpoint_data": checkpoint_data,
                "metadata_type": metadata_type,
                "metadata_data": metadata_data,
                "parent_checkpoint_id": parent_checkpoint_id,
            },
            merge=True,
        )

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
            payload = {
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
            if write_idx >= 0:
                try:
                    self.writes.document(write_id).create(payload)
                except AlreadyExists:
                    continue
            else:
                self.writes.document(write_id).set(payload, merge=True)

    def delete_thread(self, thread_id: str) -> None:
        for doc in self.checkpoints.where("thread_id", "==", thread_id).stream():
            doc.reference.delete()
        for doc in self.blobs.where("thread_id", "==", thread_id).stream():
            doc.reference.delete()
        for doc in self.writes.where("thread_id", "==", thread_id).stream():
            doc.reference.delete()
