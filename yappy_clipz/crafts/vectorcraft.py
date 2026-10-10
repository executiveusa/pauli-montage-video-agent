"""Pinned VectorCraft CLI with bounded, self-contained SVG input and fixed edit/export commands."""
from __future__ import annotations
import hashlib
import json
import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any
from .pdfcraft import CraftRunError, _run, _fail, _sha
from .imagecraft import _num, ImageSpecError, sniff as image_sniff

PINNED_VERSION = '0.8.0'
MAX_INPUT_BYTES = 2 * 1024 * 1024
MAX_STEPS = 12
MAX_EDGE = 2048
OPS = {
    'rotate': ('object.rotate', {'angle': (-180, 180, 15)}),
    'move': ('object.move', {'dx': (-1024, 1024, 10), 'dy': (-1024, 1024, 0)}),
    'scale': ('object.scale', {'sx': (10, 200, 90), 'sy': (10, 200, 90)}),
    'reflectHorizontal': ('object.reflect', {}),
    'reflectVertical': ('object.reflect', {}),
}
class VectorSpecError(ValueError): pass

def binary_path() -> str:
    return os.environ.get('YAPPY_VECTORCRAFT_BIN', '/opt/vectorcraft/bin/vectorcraft-cli')
def binary_available() -> bool:
    return Path(binary_path()).is_file() and os.access(binary_path(), os.X_OK)
def parse_spec(spec: Any) -> dict[str, Any]:
    if not isinstance(spec, dict) or set(spec) - {'title', 'input', 'steps', 'output'}:
        raise VectorSpecError('spec may only set title, input, steps, output')
    title = spec.get('title')
    if not isinstance(title, str) or not 1 <= len(title.strip()) <= 120 or re.search(r'[\x00-\x1f\x7f]', title):
        raise VectorSpecError('title is required (1-120 characters)')
    if not isinstance(spec.get('input'), str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', spec['input']):
        raise VectorSpecError('input must be one registered SVG asset id')
    output = spec.get('output', {})
    if not isinstance(output, dict) or set(output) - {'format'} or output.get('format', 'svg') not in {'svg', 'pdf'}:
        raise VectorSpecError('output may only set format: svg or pdf')
    steps = spec.get('steps')
    if not isinstance(steps, list) or not 1 <= len(steps) <= MAX_STEPS:
        raise VectorSpecError('steps must contain 1-12 operations')
    clean = []
    for step in steps:
        if not isinstance(step, dict) or set(step) - {'op', 'params'} or step.get('op') not in OPS:
            raise VectorSpecError('unknown vector operation')
        defs = OPS[step['op']][1]; params = step.get('params', {})
        if not isinstance(params, dict) or set(params) - set(defs):
            raise VectorSpecError('unknown operation parameters')
        try: values = {k: _num(params.get(k, d), lo, hi, k) for k, (lo, hi, d) in defs.items()}
        except ImageSpecError as exc: raise VectorSpecError(str(exc)) from exc
        clean.append({'op': step['op'], 'params': values})
    return {'title': title.strip(), 'input': spec['input'], 'steps': clean, 'output': {'format': output.get('format', 'svg')}}

# Intentionally small SVG subset: no links, CSS, text/fonts, images, scripts, filters or entities.
_TAGS = {'svg', 'g', 'path', 'rect', 'circle', 'ellipse', 'line', 'polyline', 'polygon'}
_ATTRS = {'id', 'x', 'y', 'x1', 'x2', 'y1', 'y2', 'width', 'height', 'viewBox', 'cx', 'cy', 'r', 'rx', 'ry', 'd', 'points', 'transform', 'fill', 'stroke', 'stroke-width', 'opacity', 'fill-opacity', 'stroke-opacity', 'fill-rule', 'stroke-linecap', 'stroke-linejoin', 'stroke-miterlimit', 'stroke-dasharray', 'stroke-dashoffset', 'preserveAspectRatio'}
def sniff(data: bytes) -> tuple[str, int, int]:
    if not data or len(data) > MAX_INPUT_BYTES or re.search(br'<!|url\s*\(|(?:file|data):', data, re.I):
        raise VectorSpecError('SVG must be bounded and self-contained (no declarations or references)')
    try: root = ET.fromstring(data)
    except ET.ParseError as exc: raise VectorSpecError('invalid SVG') from exc
    if root.tag != '{http://www.w3.org/2000/svg}svg': raise VectorSpecError('SVG namespace required')
    count = 0
    for el in root.iter():
        count += 1
        if count > 2000 or el.tag not in {'{http://www.w3.org/2000/svg}' + t for t in _TAGS}:
            raise VectorSpecError('SVG element is not allowlisted or too many objects')
        if set(el.attrib) - _ATTRS or (el.text or '').strip() or (el.tail or '').strip():
            raise VectorSpecError('SVG attributes/text are not allowlisted')
        if any(len(v) > 100000 or re.search(r'(?:https?|file|data):|url\s*\(', v, re.I) for v in el.attrib.values()): raise VectorSpecError('SVG attribute too large')
    try:
        w = float(root.attrib['width']); h = float(root.attrib['height'])
        if not w.is_integer() or not h.is_integer() or not 16 <= w <= MAX_EDGE or not 16 <= h <= MAX_EDGE: raise ValueError()
    except (ValueError, KeyError): raise VectorSpecError('SVG needs integer width/height from 16 to 2048') from None
    if count < 2: raise VectorSpecError('SVG has no artwork')
    return 'svg', int(w), int(h)

def spec_digest(spec: dict[str, Any], sha: str) -> str:
    return hashlib.sha256(json.dumps({'engine': 'vectorcraft', 'version': PINNED_VERSION, 'spec': spec, 'input': sha}, sort_keys=True).encode()).hexdigest()
def _input(job_dir: Path, names: list[str]) -> bytes:
    if names != ['in0.svg'] or not (job_dir / 'in0.svg').is_file(): raise CraftRunError('one uploaded in0.svg is required')
    data = (job_dir / 'in0.svg').read_bytes()
    try: sniff(data)
    except VectorSpecError as exc: raise CraftRunError(str(exc)) from exc
    return data

def _info(job_dir: Path, name: str, timeout: int) -> dict[str, Any]:
    proc = _run([binary_path(), 'info', name], job_dir, timeout)
    if proc.returncode: raise _fail(proc, 'vector info')
    return json.loads(proc.stdout)
def run_info(job_dir: Path, names: list[str]) -> dict[str, Any]:
    data = _input(job_dir, names); _, w, h = sniff(data)
    if not binary_available(): raise CraftRunError('VectorCraft not installed')
    info = _info(job_dir, 'in0.svg', 120)
    return {'engine': 'vectorcraft', 'version': PINNED_VERSION, 'documents': [{'format': 'svg', 'width': w, 'height': h, 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data), 'warnings': info['warnings'], 'objects': info['info']['objects']} ]}
def run_build(job_dir: Path, spec: dict[str, Any], names: list[str], *, timeout: int = 120) -> dict[str, Any]:
    spec = parse_spec(spec); data = _input(job_dir, names); _, w, h = sniff(data)
    if not binary_available(): raise CraftRunError('VectorCraft not installed')
    (job_dir / 'previews').mkdir(exist_ok=True)
    imported = _info(job_dir, 'in0.svg', timeout)
    if imported['warnings']: raise CraftRunError('SVG import has warnings')
    baseline_name = 'baseline.' + spec['output']['format']
    baseline = _run([binary_path(), 'convert', 'in0.svg', baseline_name], job_dir, timeout)
    if baseline.returncode: raise _fail(baseline, 'vector baseline export')
    before = _run([binary_path(), 'convert', baseline_name, 'previews/before.png'], job_dir, timeout)
    if before.returncode: raise _fail(before, 'vector before preview')
    out = 'out.' + spec['output']['format']
    argv = [binary_path(), 'run', '--in', 'in0.svg', '--cmd', 'select.all', '--params', '{}']
    for step in spec['steps']:
        params = dict(step['params'])
        if step['op'].startswith('reflect'): params['axis'] = 'horizontal' if step['op'] == 'reflectHorizontal' else 'vertical'
        argv += ['--cmd', OPS[step['op']][0], '--params', json.dumps(params)]
    argv += ['--export', out, '--export', 'previews/after.png']
    proc = _run(argv, job_dir, timeout)
    if proc.returncode or not (job_dir / out).is_file(): raise _fail(proc, 'VectorCraft')
    try: events = [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]
    except ValueError as exc: raise CraftRunError('VectorCraft returned invalid receipts') from exc
    out_data = (job_dir / out).read_bytes()
    if len(out_data) > 25 * 1024 * 1024: raise CraftRunError('output too large')
    if spec['output']['format'] == 'pdf':
        if not out_data.startswith(b'%PDF-'): raise CraftRunError('invalid PDF export')
    else:
        try: ET.fromstring(out_data)
        except ET.ParseError as exc: raise CraftRunError('invalid SVG export') from exc
    # Preview the actual exported artifact, not just the editor's in-memory document.
    preview = _run([binary_path(), 'convert', out, 'previews/after.png'], job_dir, timeout)
    if preview.returncode: raise _fail(preview, 'export preview')
    exported_info = _info(job_dir, out, timeout)
    _, ow, oh = image_sniff((job_dir / 'previews/after.png').read_bytes())
    return {'engine': 'vectorcraft', 'version': PINNED_VERSION, 'argv': [Path(argv[0]).name, *argv[1:]], 'output': out,
            'sha256': _sha(job_dir / out), 'bytes': len(out_data), 'previews': [{'file': 'previews/before.png'}, {'file': 'previews/after.png'}],
            'inputInfo': {'format': 'svg', 'width': w, 'height': h, 'sha256': hashlib.sha256(data).hexdigest()},
            'outInfo': {'format': spec['output']['format'], 'width': ow, 'height': oh}, 'expected': {'width': w, 'height': h, 'format': spec['output']['format']},
            'warnings': exported_info['warnings'] + [warning for e in events for warning in (e.get('result', {}).get('warnings') or [])],
            'commands': [e.get('command') for e in events if e.get('step') == 'cmd']}
