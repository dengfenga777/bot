import importlib
import pkgutil
from typing import List, Any


def _iter_integration_packages() -> List[str]:
    packages = []
    try:
        import app.integrations as integrations_pkg

        for m in pkgutil.iter_modules(integrations_pkg.__path__, integrations_pkg.__name__ + "."):
            name = m.name
            # skip loader and example packages explicitly
            if name.endswith(".loader") or name.endswith(".example"):
                continue
            packages.append(name)
    except Exception:
        pass
    return packages


def load_handlers() -> List[Any]:
    """Discover and import telegram handlers from integrations.

    Each integration may provide `handlers.py` that defines variables ending with
    `_handler` (e.g., `foo_handler = CommandHandler(...)`).
    """
    found = []
    for base in _iter_integration_packages():
        mod_name = base + ".handlers"
        try:
            mod = importlib.import_module(mod_name)
        except Exception:
            continue
        for attr in dir(mod):
            if attr.endswith("_handler"):
                handler = getattr(mod, attr)
                found.append(handler)
    return found


def load_routers() -> List[Any]:
    """Discover and import FastAPI routers from integrations.

    Each integration may provide `router.py` that defines a variable `router`
    which is a FastAPI `APIRouter`.
    """
    routers = []
    for base in _iter_integration_packages():
        mod_name = base + ".router"
        try:
            mod = importlib.import_module(mod_name)
        except Exception:
            continue
        router = getattr(mod, "router", None)
        if router is not None:
            routers.append(router)
    return routers

