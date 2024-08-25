import inspect
import typing
from functools import partial
from typing import Callable

from pydantic import create_model


def get_param_names(func: Callable):
    func = func.func if isinstance(func, partial) else func
    return inspect.signature(func).parameters.keys()


def get_required_param_names(func: Callable) -> list[str]:
    if isinstance(func, partial):
        params = inspect.signature(func.func).parameters
        return [
            name
            for name, param in params.items()
            if param.default == inspect.Parameter.empty and name not in func.keywords.keys()
        ]
    params = inspect.signature(func).parameters
    return [name for name, param in params.items() if param.default == inspect.Parameter.empty]


def function_schema(f: Callable) -> dict:
    kw = {
        n: (o.annotation, ... if o.default == inspect.Parameter.empty else o.default)
        for n, o in inspect.signature(f).parameters.items()
    }
    s = create_model(f"Input for `{f.__name__}`", **kw).schema()  # type: ignore
    return dict(name=f.__name__, description=f.__doc__, parameters=s)


def get_function_return_type(func: Callable) -> type:
    func = func.func if isinstance(func, partial) else func
    sig = typing.get_type_hints(func)
    return sig.get("return", None)


def get_function_name(func: Callable) -> str:
    func = func.func if isinstance(func, partial) else func
    return func.__name__


def get_function_source(func: Callable) -> str:
    func = func.func if isinstance(func, partial) else func
    return inspect.getsource(func)


def get_function_info(func: Callable) -> str:
    """Get a string with the name, signature, and docstring of a function."""

    func = func.func if isinstance(func, partial) else func
    name = func.__name__
    signature = inspect.signature(func)
    docstring = inspect.getdoc(func)
    desc = f"\n---\nA function:\nName: {name}\n"
    if signature:
        desc += f"Signature: {signature}\n"
    if docstring:
        desc += f"Docstring: {docstring}\n"
    return inspect.cleandoc(desc + "---\n\n")
