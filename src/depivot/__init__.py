"""Depivot - Excel unpivot/melt CLI tool."""

__version__ = "0.1.0"
__author__ = "depivot"

from depivot.core import depivot_file, depivot_batch
from depivot.exceptions import DepivotError

__all__ = ["depivot_file", "depivot_batch", "DepivotError", "__version__"]
