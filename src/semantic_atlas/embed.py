from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

import numpy as np

_TOKEN_RE = re.compile(r"[\w'-]+", flags=re.UNICODE)


@dataclass(slots=True)
class FeatureHashEmbedder:
    """Deterministic, dependency-light text embedder for demos/tests.

    This is deliberately not positioned as a production semantic model. It makes
    the repository runnable without an API key while keeping AtlasIndex agnostic
    to the embedding provider.
    """

    dimensions: int = 256
    ngram_max: int = 2

    def embed(self, text: str) -> np.ndarray:
        tokens = [t.lower() for t in _TOKEN_RE.findall(text)]
        features: list[str] = list(tokens)
        if self.ngram_max >= 2:
            features.extend(f"{a}::{b}" for a, b in zip(tokens, tokens[1:]))

        vec = np.zeros(self.dimensions, dtype=np.float32)
        for feature in features:
            digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=16).digest()
            idx = int.from_bytes(digest[:8], "little") % self.dimensions
            sign = 1.0 if digest[8] & 1 else -1.0
            vec[idx] += sign
        norm = float(np.linalg.norm(vec))
        if norm:
            vec /= norm
        return vec
