from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import numpy as np

from .core import AtlasIndex, AtlasRecord


class AtlasStore:
    """Hybrid control/data plane persistence.

    SQLite keeps IDs, metadata, provenance and transaction semantics. Dense
    vectors stay in NumPy arrays. The split is intentional: vector geometry is
    not a replacement for relational constraints or durable metadata.
    """

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.db_path = self.root / "atlas.sqlite3"
        self.vector_path = self.root / "vectors.npz"

    def save(self, index: AtlasIndex) -> None:
        ids = np.array([r.id for r in index.records])
        vectors = np.vstack([r.vector for r in index.records]) if index.records else np.empty((0, 0), dtype=np.float32)
        facet_counts = np.array([len(r.facets) for r in index.records], dtype=np.int32)
        flat_facets = np.vstack([v for r in index.records for v in r.facets]) if int(facet_counts.sum()) else np.empty((0, vectors.shape[1] if vectors.ndim == 2 and vectors.shape[0] else 0), dtype=np.float32)
        np.savez_compressed(self.vector_path, ids=ids, vectors=vectors, facet_counts=facet_counts, facets=flat_facets)

        with sqlite3.connect(self.db_path) as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute(
                "CREATE TABLE IF NOT EXISTS records (id TEXT PRIMARY KEY, metadata TEXT NOT NULL, timestamp REAL, provenance TEXT, confidence REAL NOT NULL)"
            )
            db.execute("DELETE FROM records")
            db.executemany(
                "INSERT INTO records VALUES (?, ?, ?, ?, ?)",
                [
                    (r.id, json.dumps(r.metadata, sort_keys=True), r.timestamp, r.provenance, r.confidence)
                    for r in index.records
                ],
            )
            db.commit()

    def load(self, **index_kwargs) -> AtlasIndex:
        payload = np.load(self.vector_path, allow_pickle=False)
        ids = [str(x) for x in payload["ids"]]
        vectors = payload["vectors"]
        counts = payload["facet_counts"]
        flat = payload["facets"]
        rows: dict[str, tuple] = {}
        with sqlite3.connect(self.db_path) as db:
            for row in db.execute("SELECT id, metadata, timestamp, provenance, confidence FROM records"):
                rows[row[0]] = row
        records: list[AtlasRecord] = []
        cursor = 0
        for i, rid in enumerate(ids):
            count = int(counts[i])
            facets = [flat[j] for j in range(cursor, cursor + count)]
            cursor += count
            _, metadata, timestamp, provenance, confidence = rows[rid]
            records.append(
                AtlasRecord(
                    id=rid,
                    vector=vectors[i],
                    facets=facets,
                    metadata=json.loads(metadata),
                    timestamp=timestamp,
                    provenance=provenance,
                    confidence=confidence,
                )
            )
        return AtlasIndex(**index_kwargs).extend_and_build(records)
