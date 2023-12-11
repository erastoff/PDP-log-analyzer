#!/usr/bin/env python
# -*- coding: utf-8 -*-

from functools import update_wrapper, wraps


def disable(func):
    """
    Disable a decorator by re-assigning the decorator's name
    to this function. For example, to turn off memoization:

    # >>> memo = disable

    """

    @wraps(func)
    def wrapper(*args):
        return func(*args)

    return wrapper


def decorator(func):
    """
    Decorate a decorator so that it inherits the docstrings
    and stuff from the function it's decorating.
    """

    def wrapper(*args):
        return func(*args)

    update_wrapper(wrapper, func)
    return wrapper


def countcalls(func):
    """Decorator that counts calls made to the function decorated."""

    @wraps(func)
    def wrapper(*args):
        wrapper.calls += 1
        return func(*args)

    wrapper.calls = 0
    return wrapper


def memo(func):
    """
    Memorize a function so that it caches all return values for
    faster future lookups.
    """
    cache = {}

    @wraps(func)
    def wrapper(*args):
        key = args
        if key not in cache:
            result = func(*args)
            cache[key] = result
            # print("FUNCTION VALUE CALCULATED!")
            return result
        else:
            # print("CACHED VALUE HAS BEEN GOT!")
            return cache[key]

    # print(cache)
    return wrapper


def n_ary(func):
    """
    Given binary function f(x, y), return an n_ary function such
    that f(x, y, z) = f(x, f(y,z)), etc. Also allow f(x) = x.
    """

    @wraps(func)
    def wrapper(*args):
        if len(args) == 1:
            return args[0]
        elif len(args) == 2:
            return func(*args)
        else:
            return func(args[0], wrapper(*args[1:]))

    return wrapper


def trace(prefix):
    """Trace calls made to function decorated.

    @trace("____")
    def fib(n):
        ....

    # >>> fib(3)
     --> fib(3)
    ____ --> fib(2)
    ________ --> fib(1)
    ________ <-- fib(1) == 1
    ________ --> fib(0)
    ________ <-- fib(0) == 1
    ____ <-- fib(2) == 2
    ____ --> fib(1)
    ____ <-- fib(1) == 1
     <-- fib(3) == 3

    """

    def trasing_deco(func):
        def reset():
            wrapper.rdepth = 0
            wrapper.ncalls = 0

        @wraps(func)
        def wrapper(*args, **kwargs):
            if wrapper.depth == 0:
                reset()
            wrapper.depth += 1
            wrapper.ncalls += 1
            wrapper.rdepth = max(wrapper.rdepth, wrapper.depth)
            arg_str = ", ".join(map(repr, args))
            print(f"{prefix*(wrapper.depth - 1)} --> {func.__name__}({arg_str})")
            result = func(*args)
            print(
                f"{prefix*(wrapper.depth - 1)} <-- {func.__name__}({arg_str}) == {result}"
            )
            try:
                return result
            finally:
                wrapper.depth -= 1

        wrapper.depth = 0
        reset()
        return wrapper

    return trasing_deco


@memo
@countcalls
@n_ary
def foo(a, b):
    return a + b


@countcalls
@memo
@n_ary
def bar(a, b):
    return a * b


@countcalls
@trace("####")
@memo
def fib(n):
    """Some doc"""
    return 1 if n <= 1 else fib(n - 1) + fib(n - 2)


def main():
    print(foo(4, 3))
    print(foo(4, 3, 2))
    print(foo(4, 3))
    print("foo was called", foo.calls, "times")

    print(bar(4, 3))
    print(bar(4, 3, 2))
    print(bar(4, 3, 2, 1))
    print("bar was called", bar.calls, "times")

    print(fib.__doc__)
    fib(3)
    print(fib.calls, "calls made")


if __name__ == "__main__":
    main()
