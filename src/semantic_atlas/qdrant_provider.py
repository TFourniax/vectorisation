from __future__ import annotations

"""Logical-ID-safe Qdrant adapter.

Qdrant's native point identity is a backend concern. Semantic ABI logical IDs may use
arbitrary stable names, so production deployments can provide an explicit reversible
mapping without contaminating the portable contract with provider-native IDs.
"""

from typing import Any, Mapping, Sequence

from .protocol_v1 import NeighborRequest
from .providers import ProviderHttpTransport, QdrantOracleV1, _id_text, _point_id


class PortableQdrantOracleV1(QdrantOracleV1):
    def __init__(
        self,
        *,
        object_id_map: Mapping[str, Any] | None = None,
        score_directionality: str = "unknown",
        **kwargs,
    ) -> None:
        if score_directionality not in {"symmetric", "asymmetric", "unknown"}:
            raise ValueError("invalid Qdrant score_directionality")
        self.object_id_map = {str(key): value for key, value in dict(object_id_map or {}).items()}
        reverse: dict[str, str] = {}
        for logical, native in self.object_id_map.items():
            native_text = _id_text(native)
            if native_text in reverse and reverse[native_text] != logical:
                raise ValueError(f"Qdrant object_id_map is not one-to-one for native id {native_text!r}")
            reverse[native_text] = logical
        self._logical_by_native = reverse
        super().__init__(**kwargs)
        metadata = dict(self.manifest.metadata)
        metadata["object_id_mappings"] = len(self.object_id_map)
        self.manifest = type(self.manifest)(
            implementation_id=self.manifest.implementation_id,
            implementation_kind=self.manifest.implementation_kind,
            score_semantics=self.manifest.score_semantics,
            score_directionality=score_directionality,
            deterministic=self.manifest.deterministic,
            capabilities=self.manifest.capabilities,
            metadata=metadata,
        )

    @classmethod
    def http(
        cls,
        base_url: str,
        *,
        collection: str,
        query_catalog: Mapping[str, Any] | None = None,
        object_id_map: Mapping[str, Any] | None = None,
        api_key: str | None = None,
        vector_name: str | None = None,
        timeout: float = 15.0,
        require_https: bool = False,
        implementation_id: str | None = None,
        deterministic: bool = False,
        state_digest: str | None = None,
        score_directionality: str = "unknown",
    ) -> "PortableQdrantOracleV1":
        headers = {} if api_key is None else {"api-key": str(api_key)}
        http = ProviderHttpTransport(
            base_url,
            timeout=timeout,
            headers=headers,
            require_https=require_https,
        )
        return cls(
            collection=collection,
            query_catalog=query_catalog,
            object_id_map=object_id_map,
            transport=http.json,
            vector_name=vector_name,
            implementation_id=implementation_id,
            deterministic=deterministic,
            state_digest=state_digest,
            score_directionality=score_directionality,
        )

    def _backend_id(self, logical_id: str):
        logical = str(logical_id)
        if logical in self.object_id_map:
            return self.object_id_map[logical]
        return _point_id(logical)

    def _logical_id(self, native_id: Any) -> str:
        native = _id_text(native_id)
        return self._logical_by_native.get(native, native)

    def _query(self, anchor: str) -> Any:
        if anchor in self.query_catalog:
            return self.query_catalog[anchor]
        return self._backend_id(anchor)

    def contains_many(self, object_ids: Sequence[str]) -> Mapping[str, bool]:
        ids = [str(value) for value in object_ids]
        result = {value: True for value in ids if value in self.query_catalog}
        logical_rows = [value for value in ids if value not in self.query_catalog]
        if logical_rows:
            native_by_logical = {value: self._backend_id(value) for value in logical_rows}
            response = self.transport(
                "POST",
                self._base,
                {
                    "ids": list(native_by_logical.values()),
                    "with_payload": False,
                    "with_vector": False,
                },
            )
            found = {
                _id_text(row.get("id"))
                for row in response.get("result", ())
                if isinstance(row, Mapping) and row.get("id") is not None
            }
            result.update(
                {
                    logical: _id_text(native) in found
                    for logical, native in native_by_logical.items()
                }
            )
        return {value: bool(result.get(value, False)) for value in ids}

    def _search_body(self, *, anchor: str, limit: int, candidate: str | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {
            "query": self._query(anchor),
            "limit": max(1, int(limit)),
            "with_payload": False,
            "with_vector": False,
        }
        if self.vector_name:
            body["using"] = self.vector_name
        if candidate is not None:
            body["filter"] = {"must": [{"has_id": [self._backend_id(candidate)]}]}
        return body

    def neighbors_many(self, requests: Sequence[NeighborRequest]) -> Mapping[NeighborRequest, Sequence[str]]:
        searches = []
        for req in requests:
            external = req.anchor in self.query_catalog
            searches.append(self._search_body(anchor=req.anchor, limit=req.k if external else req.k + 1))
        rows = self._batch(searches)
        output: dict[NeighborRequest, Sequence[str]] = {}
        for req, row in zip(requests, rows):
            values: list[str] = []
            for point in row.get("points", ()):
                if not isinstance(point, Mapping) or point.get("id") is None:
                    continue
                logical = self._logical_id(point["id"])
                if req.anchor not in self.query_catalog and logical == req.anchor:
                    continue
                values.append(logical)
                if len(values) >= req.k:
                    break
            output[req] = tuple(values)
        return output
