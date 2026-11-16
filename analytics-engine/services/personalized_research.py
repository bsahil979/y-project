"""Serve the saved Phase 8 replay with explicit freshness and integrity checks."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / 'research/personalized_phase8_2026-11-16'


def personalized_study_results():
    manifest = json.loads((STUDY / 'manifest.json').read_text(encoding='utf-8'))

    def changed(root, mapping):
        return [name for name, expected in mapping.items()
                if not (root/name).is_file() or hashlib.sha256((root/name).read_bytes()).hexdigest() != expected]

    changed_sources = changed(ROOT, manifest['source_sha256'])
    changed_inputs = changed(ROOT, manifest['input_sha256'])
    changed_outputs = changed(STUDY, manifest['output_sha256'])
    if changed_outputs:
        raise ValueError('Personalized study artifacts failed integrity validation: ' + ', '.join(changed_outputs))
    summary = json.loads((STUDY/'summary.json').read_text(encoding='utf-8'))
    return {**summary, 'stale': bool(changed_sources or changed_inputs),
            'changed_sources': changed_sources, 'changed_inputs': changed_inputs,
            'manifest': manifest}
