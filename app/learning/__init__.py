import logging
import pkgutil
import importlib

__path__ = pkgutil.extend_path(__path__, __name__)

def load_submodules():
    for loader, module_name, is_pkg in pkgutil.walk_packages(__path__):
        full_module_name = f"{__name__}.{module_name}"
        try:
            importlib.import_module(full_module_name)
        except ImportError as e:
            logging.error(f"Cannot import module {full_module_name}: {e}")

load_submodules()
