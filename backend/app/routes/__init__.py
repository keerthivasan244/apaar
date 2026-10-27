"""Router registry. Every module exposes `router`."""
from importlib import import_module

MODULES = [
    "auth", "colleges", "students", "flags", "matches", "analytics", "risk", "credentials",
    "consents", "verify", "audit", "reports", "admin_demo", "nlq",
]


def all_routers():
    routers = []
    for name in MODULES:
        try:
            mod = import_module(f"{__name__}.{name}")
        except ModuleNotFoundError as exc:
            if exc.name == f"{__name__}.{name}":
                continue  # module not implemented yet
            raise
        routers.append(mod.router)
    return routers
