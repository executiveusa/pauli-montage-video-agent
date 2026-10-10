"""Import smoke: the renderer image carries only yappy_clipz/__init__.py and code_animator/."""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import yappy_clipz

SMOKE = (
    "import sys\n"
    "import yappy_clipz.code_animator.render_service, yappy_clipz.code_animator.remote, yappy_clipz.code_animator.renderer\n"
    "bad = [m for m in sys.modules if m == 'packages' or m.startswith(('packages.', 'yappy_clipz.repository', 'yappy_clipz.service', 'yappy_clipz.factory', 'jsonschema', 'pydantic'))]\n"
    "assert not bad, bad\n"
    "print('import-smoke-ok')\n"
)


def test_renderer_modules_import_with_only_the_renderer_files(tmp_path):
    src = Path(yappy_clipz.__file__).parent
    dest = tmp_path / "yappy_clipz"
    dest.mkdir()
    shutil.copy(src / "__init__.py", dest / "__init__.py")
    shutil.copytree(src / "code_animator", dest / "code_animator", ignore=shutil.ignore_patterns("__pycache__"))
    done = subprocess.run([sys.executable, "-c", SMOKE], cwd=tmp_path, env={"PYTHONPATH": str(tmp_path), "PATH": "/usr/bin:/bin"},
                          capture_output=True, text=True, timeout=60)
    assert done.returncode == 0 and "import-smoke-ok" in done.stdout, done.stderr[-600:]
