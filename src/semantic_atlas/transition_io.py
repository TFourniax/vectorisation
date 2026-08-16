from __future__ import annotations
import json
from pathlib import Path
import numpy as np
from .alignment import LinearTransition, TransitionAtlas, TransitionDiagnostics
_FORMAT_VERSION = 1

def _write_map(payload: dict[str, np.ndarray], prefix: str, model: LinearTransition) -> None:
    payload[f'{prefix}_source_mean'] = model.source_mean
    payload[f'{prefix}_target_mean'] = model.target_mean
    payload[f'{prefix}_matrix'] = model.matrix
    payload[f'{prefix}_source_centroid'] = model.source_centroid
    payload[f'{prefix}_scale'] = np.asarray([model.scale], dtype=np.float64)
    payload[f'{prefix}_quality'] = np.asarray([model.quality], dtype=np.float64)
    payload[f'{prefix}_support'] = np.asarray([model.support], dtype=np.int64)

def _read_map(payload: np.lib.npyio.NpzFile, prefix: str) -> LinearTransition:
    return LinearTransition(source_mean=payload[f'{prefix}_source_mean'].astype(np.float32), target_mean=payload[f'{prefix}_target_mean'].astype(np.float32), matrix=payload[f'{prefix}_matrix'].astype(np.float32), scale=float(payload[f'{prefix}_scale'][0]), source_centroid=payload[f'{prefix}_source_centroid'].astype(np.float32), quality=float(payload[f'{prefix}_quality'][0]), support=int(payload[f'{prefix}_support'][0]))

def save_transition(transition: TransitionAtlas, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    d = transition.fit_diagnostics
    metadata = {'format': 'semantic-coordinate-transition', 'format_version': _FORMAT_VERSION, 'source_space': transition.source_space, 'target_space': transition.target_space, 'temperature': transition.temperature, 'local_map_count': len(transition.local_maps), 'diagnostics': {'n': d.n, 'mean_pair_cosine': d.mean_pair_cosine, 'p10_pair_cosine': d.p10_pair_cosine, 'pair_recall_at_1': d.pair_recall_at_1, 'neighborhood_jaccard': d.neighborhood_jaccard, 'held_out': d.held_out, 'n_train': d.n_train}}
    arrays: dict[str, np.ndarray] = {'metadata_json': np.asarray(json.dumps(metadata, sort_keys=True))}
    _write_map(arrays, 'global', transition.global_map)
    for i, model in enumerate(transition.local_maps):
        _write_map(arrays, f'local_{i}', model)
    np.savez_compressed(path, **arrays)
    return path

def load_transition(path: str | Path) -> TransitionAtlas:
    with np.load(Path(path), allow_pickle=False) as payload:
        metadata = json.loads(str(payload['metadata_json'].item()))
        if metadata.get('format') != 'semantic-coordinate-transition':
            raise ValueError('not a Semantic Coordinate transition file')
        if int(metadata.get('format_version', -1)) != _FORMAT_VERSION:
            raise ValueError('unsupported transition format version')
        d = metadata['diagnostics']
        diagnostics = TransitionDiagnostics(n=int(d['n']), mean_pair_cosine=float(d['mean_pair_cosine']), p10_pair_cosine=float(d['p10_pair_cosine']), pair_recall_at_1=float(d['pair_recall_at_1']), neighborhood_jaccard=float(d['neighborhood_jaccard']), held_out=bool(d.get('held_out', False)), n_train=int(d.get('n_train', 0)))
        global_map = _read_map(payload, 'global')
        locals_ = [_read_map(payload, f'local_{i}') for i in range(int(metadata['local_map_count']))]
        return TransitionAtlas(metadata['source_space'], metadata['target_space'], global_map, locals_, diagnostics, float(metadata['temperature']))
