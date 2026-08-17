import numpy as np
from semantic_atlas.alignment import TransitionAtlas
from semantic_atlas.geometry import normalize
from semantic_atlas.transition_io import load_transition, save_transition


def test_transition_roundtrip_preserves_transport_and_diagnostics(tmp_path):
    rng = np.random.default_rng(44)
    x = normalize(rng.normal(size=(80, 14)))
    q, _ = np.linalg.qr(rng.normal(size=(14, 14)))
    y = normalize(x @ q)
    transition = TransitionAtlas.fit("encoder-a", "encoder-b", x, y, chart_size=30)
    probe = normalize(rng.normal(size=(1, 14)))[0]
    before = transition.map(probe).vector
    path = save_transition(transition, tmp_path / "a-to-b.sct.npz")
    loaded = load_transition(path)
    after = loaded.map(probe).vector
    assert np.allclose(before, after, atol=1e-6)
    assert loaded.fit_diagnostics.held_out is True
    assert loaded.source_space == "encoder-a"
    assert loaded.target_space == "encoder-b"
