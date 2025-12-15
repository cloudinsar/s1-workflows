import importlib.metadata

from sar.utils.workflow_utils import *

__version__ = importlib.metadata.version("sar")
print("__version__: " + str(__version__))
