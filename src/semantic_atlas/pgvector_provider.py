from __future__ import annotations

"""PostgreSQL/pgvector adapter for Semantic ABI Oracle Protocol v1."""

import math
import re
from typing import Any, Mapping, Sequence

from .protocol_v1 import NeighborRequest, OracleManifest, ScorePair

_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_METRICS = {"cosine", "l2", "inner_product"}


def _identifier(value: str, *, name: str) -> str:
    text = str(value)
    parts = text.split(".")
    if not parts or any(not _IDENTIFIER.fullmatch(part) for part in parts):
        raise ValueError(f"invalid SQL identifier for {name}: {value!r}")
    return ".".join(f'"{part}"' for part in parts)


def _vector_text(value: Any) -> str:
    if isinstance(value, str):
        text = value.strip()
        if not (text.startswith("[") and text.endswith("]")):
            raise ValueError("pgvector query string must use '[x,y,...]' vector syntax")
        return text
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        numbers = []
        for item in value:
            number = float(item)
            if not math.isfinite(number):
                raise ValueError("pgvector query vectors must contain finite numbers")
            numbers.append(format(number, ".17g"))
        if not numbers:
            raise ValueError("pgvector query vector cannot be empty")
        return "[" + ",".join(numbers) + "]"
    raise ValueError("pgvector query catalog values must be vector strings or numeric arrays")


class PgVectorOracleV1:
    """Semantic ABI adapter over a DB-API compatible PostgreSQL connection.

    Stable external anchors are materialized through ``query_catalog``. A logical ID
    absent from the catalog is interpreted as a row ID and its vector is loaded from the
    configured table. SQL identifiers are restricted to simple identifiers; all data
    values are bound as parameters.

    ``deterministic`` is deliberately opt-in. Exact scans over an immutable snapshot can
    reasonably declare it true, but ANN indexes, mutable tables or changing planner
    settings must not inherit a stronger guarantee by default.
    """

    def __init__(
        self,
        connection,
        *,
        table: str,
        id_column: str = "id",
        vector_column: str = "embedding",
        query_catalog: Mapping[str, Any] | None = None,
        metric: str = "cosine",
        implementation_id: str | None = None,
        deterministic: bool = False,
        state_digest: str | None = None,
    ) -> None:
        metric = str(metric)
        if metric not in _METRICS:
            raise ValueError(f"unsupported pgvector metric: {metric!r}")
        self.connection = connection
        self.table = _identifier(table, name="table")
        self.id_column = _identifier(id_column, name="id_column")
        self.vector_column = _identifier(vector_column, name="vector_column")
        self.query_catalog = {str(key): _vector_text(value) for key, value in dict(query_catalog or {}).items()}
        self.metric = metric
        self._anchor_cache: dict[str, str] = {}
        metadata: dict[str, Any] = {
            "provider": "pgvector",
            "table": str(table),
            "id_column": str(id_column),
            "vector_column": str(vector_column),
            "metric": metric,
            "query_catalog_anchors": len(self.query_catalog),
        }
        if state_digest:
            metadata["state_digest"] = str(state_digest)
        self.manifest = OracleManifest(
            implementation_id=implementation_id or f"pgvector:{table}:{metric}",
            implementation_kind="pgvector",
            score_semantics=f"pgvector-{metric}-similarity",
            score_directionality="symmetric",
            deterministic=bool(deterministic),
            metadata=metadata,
        )

    @classmethod
    def psycopg(
        cls,
        dsn: str,
        *,
        table: str,
        id_column: str = "id",
        vector_column: str = "embedding",
        query_catalog: Mapping[str, Any] | None = None,
        metric: str = "cosine",
        implementation_id: str | None = None,
        deterministic: bool = False,
        state_digest: str | None = None,
        connect_timeout: int = 10,
    ) -> "PgVectorOracleV1":
        try:
            import psycopg
        except ImportError as exc:
            raise RuntimeError("psycopg is required for PgVectorOracleV1.psycopg; install the 'postgres' extra") from exc
        connection = psycopg.connect(str(dsn), connect_timeout=max(1, int(connect_timeout)), autocommit=True)
        return cls(
            connection,
            table=table,
            id_column=id_column,
            vector_column=vector_column,
            query_catalog=query_catalog,
            metric=metric,
            implementation_id=implementation_id,
            deterministic=deterministic,
            state_digest=state_digest,
        )

    def close(self) -> None:
        close = getattr(self.connection, "close", None)
        if callable(close):
            close()

    def _fetchall(self, sql: str, params=()):
        cursor = self.connection.cursor()
        try:
            cursor.execute(sql, params)
            return list(cursor.fetchall())
        finally:
            close = getattr(cursor, "close", None)
            if callable(close):
                close()

    def _anchor_vector(self, anchor: str) -> tuple[str, bool]:
        if anchor in self.query_catalog:
            return self.query_catalog[anchor], True
        if anchor in self._anchor_cache:
            return self._anchor_cache[anchor], False
        rows = self._fetchall(
            f"SELECT {self.vector_column}::text FROM {self.table} WHERE {self.id_column}::text = %s LIMIT 1",
            (str(anchor),),
        )
        if not rows:
            raise KeyError(f"pgvector anchor row is missing: {anchor!r}")
        vector = str(rows[0][0])
        self._anchor_cache[anchor] = vector
        return vector, False

    def _distance_expr(self) -> str:
        if self.metric == "cosine":
            return f"{self.vector_column} <=> %s::vector"
        if self.metric == "l2":
            return f"{self.vector_column} <-> %s::vector"
        return f"{self.vector_column} <#> %s::vector"

    def _score_expr(self) -> str:
        distance = self._distance_expr()
        if self.metric == "cosine":
            return f"1 - ({distance})"
        if self.metric == "l2":
            return f"-1 * ({distance})"
        # <#> is negative inner product in pgvector.
        return f"-1 * ({distance})"

    def contains_many(self, object_ids: Sequence[str]) -> Mapping[str, bool]:
        ids = [str(value) for value in object_ids]
        output = {value: True for value in ids if value in self.query_catalog}
        row_ids = [value for value in ids if value not in self.query_catalog]
        if row_ids:
            rows = self._fetchall(
                f"SELECT {self.id_column}::text FROM {self.table} WHERE {self.id_column}::text = ANY(%s)",
                (row_ids,),
            )
            found = {str(row[0]) for row in rows}
            output.update({value: value in found for value in row_ids})
        return {value: bool(output.get(value, False)) for value in ids}

    def score_many(self, pairs: Sequence[ScorePair]) -> Mapping[ScorePair, float]:
        output: dict[ScorePair, float] = {}
        score_expr = self._score_expr()
        for pair in pairs:
            vector, _ = self._anchor_vector(pair.anchor)
            rows = self._fetchall(
                f"SELECT {score_expr} AS score FROM {self.table} WHERE {self.id_column}::text = %s LIMIT 1",
                (vector, str(pair.candidate)),
            )
            if not rows:
                raise KeyError(f"pgvector candidate row is missing: {pair.candidate!r}")
            score = float(rows[0][0])
            if not math.isfinite(score):
                raise ValueError("pgvector returned a non-finite score")
            output[pair] = score
        return output

    def neighbors_many(self, requests: Sequence[NeighborRequest]) -> Mapping[NeighborRequest, Sequence[str]]:
        output: dict[NeighborRequest, Sequence[str]] = {}
        distance = self._distance_expr()
        for req in requests:
            vector, external = self._anchor_vector(req.anchor)
            params: list[Any] = [vector]
            where = ""
            if not external:
                where = f"WHERE {self.id_column}::text <> %s"
                params.append(str(req.anchor))
            params.append(int(req.k))
            # Selecting the distance gives the vector placeholder a stable first
            # parameter position even when a row-anchor exclusion adds a WHERE value.
            rows = self._fetchall(
                f"SELECT {self.id_column}::text, {distance} AS distance FROM {self.table} {where} ORDER BY distance ASC LIMIT %s",
                tuple(params),
            )
            output[req] = tuple(str(row[0]) for row in rows[: req.k])
        return output