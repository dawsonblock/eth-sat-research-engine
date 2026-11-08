"""Copy changed validation outputs from an isolated CI run for artifact upload."""
from filecmp import cmp
from pathlib import Path
import shutil
import sys


def collect(sealed, working, output):
    output.mkdir(parents=True, exist_ok=True)
    for path in sorted(working.rglob('*')):
        if path.is_file():
            relative = path.relative_to(working)
            baseline = sealed / relative
            if baseline.is_file() and cmp(path, baseline, shallow=False):
                continue
            destination = output / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, destination)


if __name__ == '__main__':
    collect(*(Path(arg) for arg in sys.argv[1:]))
