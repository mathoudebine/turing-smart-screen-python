import sys
import types


def import_scheduler():
    # Import library.scheduler without pulling in library.stats (which imports library.display and
    # instantiates the hardware driver at import time): the queue writer itself only needs
    # library.config, so stub out library.stats before the (first) import of the scheduler.
    if "library.scheduler" in sys.modules:
        return sys.modules["library.scheduler"]

    import library
    stub = types.ModuleType("library.stats")
    sys.modules["library.stats"] = stub
    library.stats = stub

    import library.scheduler as scheduler
    return scheduler
