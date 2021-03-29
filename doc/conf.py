"""Sphinx configuration file for an LSST stack package.

This configuration only affects single-package Sphinx documentation builds.
"""

from documenteer.sphinxconfig.stackconf import build_package_configs
import lsst.amplifier_images


_g = globals()
_g.update(
    build_package_configs(
        project_name="amplifier_images",
        version=lsst.amplifier_images.version.__version__,
    )
)
