"""Import a module against fake dependencies without leaving the fakes behind.

`patch.dict(sys.modules, fakes)` alone leaves two traces. The import binds the fake-backed
module as an attribute of its parent package. And a real copy removed beforehand is gone, so
the next import builds a second real module, and a patch on that one misses the copy that
earlier importers hold.
"""

import importlib
import sys
from unittest.mock import patch

_MISSING = object()


def load_with_fakes(module_name, fakes, *, also_reload=()):
    """Import `module_name` with `fakes` standing in for the modules they name.

    `also_reload` lists modules that `module_name` imports and that must be imported against
    the fakes too, rather than reused from an earlier real import. Afterwards `sys.modules`
    and the parent packages are as they were before the call.
    """
    reloaded = (module_name, *also_reload)
    for name in reloaded:
        importlib.import_module(name.rpartition(".")[0])

    real_modules = {name: sys.modules[name] for name in reloaded if name in sys.modules}
    parent_attributes = [_parent_attribute(name) for name in reloaded]
    for name in reloaded:
        sys.modules.pop(name, None)

    try:
        with patch.dict(sys.modules, fakes):
            return importlib.import_module(module_name)
    finally:
        sys.modules.update(real_modules)
        for parent, attribute, value in parent_attributes:
            if value is _MISSING:
                parent.__dict__.pop(attribute, None)
            else:
                setattr(parent, attribute, value)


def _parent_attribute(module_name):
    parent_name, _, attribute = module_name.rpartition(".")
    parent = sys.modules[parent_name]
    return parent, attribute, getattr(parent, attribute, _MISSING)
