from pathlib import Path
import pkgutil

__path__ = pkgutil.extend_path(__path__, __name__)
_src_pkg = Path(__file__).resolve().parents[1] / "src" / "depression_detection"
if _src_pkg.exists():
    src_text = str(_src_pkg)
    if src_text not in __path__:
        __path__.append(src_text)

__all__ = ["__version__"]
__version__ = "0.1.0"
