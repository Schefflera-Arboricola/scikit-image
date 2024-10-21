import functools
from importlib.metadata import entry_points
from functools import cache
import os
import warnings


def _entry_points(group):
    # Support Python versions before 3.10, which do not let you
    # filter groups directly.
    all_entry_points = entry_points()
    if hasattr(all_entry_points, "select"):
        selected_entry_points = all_entry_points.select(group=group)
    else:
        selected_entry_points = all_entry_points.get(group, ())
    return selected_entry_points


def dispatching_disabled():
    """Determine if dispatching has been disabled by the user"""
    no_dispatching = os.environ.get("SKIMAGE_NO_DISPATCHING", False)
    if no_dispatching == "1":
        return True
    else:
        return False


def get_module_name(func):
    """Get the public module name of a scikit-image function.

    This computes the name of the public submodule in which the function can
    be found.
    """
    full_name = func.__module__
    # This relies on the fact that scikit-image does not use
    # sub-submodules in its public API, except in one case.
    # This means that public name can be atmost `skimage.foobar`
    # for everything else
    if full_name.startswith("skimage.filters.rank"):
        public_name = "skimage.filters.rank"
    else:
        public_name = ".".join(full_name.split(".")[:2])

    # It would be nice to sanity check things by doing something like the
    # following. However we can't because this code is executed while the
    # module is being imported, which means this would create a circular
    # import
    # mod = importlib.import_module(public_name)
    # assert getattr(mod, func.__name__) is func

    return public_name


@cache
def all_backends():
    """List all installed backends and information about them"""
    backends = {}
    backends_ = _entry_points(group="skimage_backends")
    backend_infos = _entry_points(group="skimage_backend_infos")

    for backend in backends_:
        backends[backend.name] = {"implementation": backend}
        try:
            info = backend_infos[backend.name]
            # Double () to load and then call the backend information function
            backends[backend.name]["info"] = info.load()()
        except KeyError:
            pass

    return backends


def dispatchable(func):
    """Mark a function as dispatchable.

    When a decorated function is called the installed backends are
    searched for an implementation. If no backend implements the function
    then the scikit-image implementation is used.
    """
    func_name = func.__name__
    func_module = get_module_name(func)

    # If no backends are installed at all or dispatching is disabled,
    # return the original function. This way people who don't care about it
    # don't see anything related to dispatching
    if dispatching_disabled() or not all_backends():
        return func

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Backends are tried in alphabetical order, this makes things
        # predictable and stable across runs. Might need a better solution
        # when it becomes common that users have more than one backend
        # that would accept a call.
        for name in sorted(all_backends()):
            backend = all_backends()[name]
            # If we have a BackendInformation object we check if the
            # function we are looking for is implemented in the backend
            if "info" in backend:
                if (
                    f"{func_module}:{func_name}"
                    not in backend["info"].supported_functions
                ):
                    continue

            backend_impl = backend["implementation"].load()

            # Allow the backend to accept/reject a call based on the function
            # name and the values of the arguments
            wants_it = backend_impl.can_has(
                f"{func_module}:{func_name}", *args, **kwargs
            )
            if not wants_it:
                continue

            # can_has("foo", ...) might be True, but the function might not actually
            # be implemented in the backend
            func_impl = backend_impl.get_implementation(f"{func_module}:{func_name}")
            if func_impl is not None:
                warnings.warn(
                    f"Call to '{func_module}:{func_name}' was dispatched to"
                    f" the '{name}' backend. Set SKIMAGE_NO_DISPATCHING=1 to"
                    " disable this.",
                    DispatchNotification,
                    # XXX from where should this warning originate?
                    # XXX from where the function that was dispatched was called?
                    # XXX or from where the user called a function that called
                    # XXX a function that was dispatched?
                    stacklevel=2,
                )
                return func_impl(*args, **kwargs)

        else:
            return func(*args, **kwargs)

    return wrapper


class BackendInformation:
    """Information about a backend

    A backend that wants to provide additional information about itself
    should return an instance of this from its information entry-point.
    """

    def __init__(self, supported_functions):
        self.supported_functions = supported_functions


class DispatchNotification(RuntimeWarning):
    """Notification issued when a function is dispatched to a backend."""

    pass
