"""Load Seamfit and real Robust Weight Transfer for Blender-hosted checks."""

import importlib
import os
from pathlib import Path
import sys
import bpy

ROOT = Path(__file__).resolve().parents[1]


def load_addons():
    # Prefer a normally installed extension so packaging regressions are visible.
    installed = next(
        (
            name
            for name in bpy.context.preferences.addons.keys()
            if name.startswith("bl_ext.") and name.endswith(".seamfit")
        ),
        None,
    )
    if installed:
        seamfit = importlib.import_module(installed)
    else:
        if os.environ.get("SEAMFIT_REQUIRE_INSTALLED") == "1":
            raise RuntimeError(
                "Install and enable the Seamfit ZIP in this Blender profile first."
            )
        sys.path.insert(0, str(ROOT))
        seamfit = importlib.import_module("seamfit")
        seamfit.register()

    if not hasattr(bpy.context.scene, "robust_weight_transfer_settings"):
        dep_dir = os.environ.get("SEAMFIT_RWT_DEPS", str(ROOT / "rwt-deps"))
        addon_dir = os.environ.get("SEAMFIT_RWT_PARENT", str(ROOT / "upstream"))
        sys.path[:0] = [dep_dir, addon_dir]
        rwt = importlib.import_module("robust-weight-transfer-libigl26")
        if rwt.missing_deps:
            raise RuntimeError(
                f"Install the upstream dependencies first: {rwt.missing_deps}"
            )
        rwt.register()
    return seamfit
