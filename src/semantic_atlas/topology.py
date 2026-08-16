from __future__ import annotations

from collections import deque
from dataclasses import dataclass

import numpy as np

from .geometry import cosine_matrix


@dataclass(slots=True)
class NeighborGraph:
    adjacency: list[set[int]]
    similarities: np.ndarray
    density: np.ndarray
    hubness: np.ndarray

    def shortest_path(self, start: int, end: int) -> list[int]:
        if start == end:
            return [start]
        parent: dict[int, int | None] = {start: None}
        q = deque([start])
        while q:
            node = q.popleft()
            for nxt in self.adjacency[node]:
                if nxt in parent:
                    continue
                parent[nxt] = node
                if nxt == end:
                    path = [end]
                    cur: int | None = end
                    while cur is not None and cur != start:
                        cur = parent[cur]
                        if cur is not None:
                            path.append(cur)
                    return list(reversed(path))
                q.append(nxt)
        return []


def build_mutual_knn(vectors: np.ndarray, k: int = 8) -> NeighborGraph:
    n = len(vectors)
    if n == 0:
        return NeighborGraph([], np.empty((0, 0)), np.empty(0), np.empty(0))
    sims = cosine_matrix(vectors, vectors)
    np.fill_diagonal(sims, -np.inf)
    k_eff = max(1, min(k, max(1, n - 1)))
    rankings = np.argsort(-sims, axis=1)[:, :k_eff] if n > 1 else np.empty((1, 0), dtype=int)
    directed = [set(map(int, row)) for row in rankings]
    adjacency: list[set[int]] = [set() for _ in range(n)]
    if n > 1:
        for i, row in enumerate(directed):
            for j in row:
                if i in directed[j]:
                    adjacency[i].add(j)
                    adjacency[j].add(i)
    density = np.zeros(n, dtype=np.float32)
    if n > 1:
        for i, row in enumerate(rankings):
            density[i] = float(np.mean(sims[i, row])) if len(row) else 0.0
    inbound = np.zeros(n, dtype=np.float32)
    for row in directed:
        for j in row:
            inbound[j] += 1
    hubness = inbound / max(1.0, float(k_eff))
    return NeighborGraph(adjacency, sims, density, hubness)
