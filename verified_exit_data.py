"""Loads the verified validation-only corporate-action settlement map."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
_path = Path(__file__).with_name("verified_exit_settlements.py") / "verified_exit_settlements.py"
_spec = spec_from_file_location("_verified_exit_settlements", _path)
if _spec is None or _spec.loader is None:
    raise ImportError(f"Cannot load verified settlement map from {_path}")
_module = module_from_spec(_spec)
_spec.loader.exec_module(_module)
install_verified_exit_data = _module.install_verified_exit_data
