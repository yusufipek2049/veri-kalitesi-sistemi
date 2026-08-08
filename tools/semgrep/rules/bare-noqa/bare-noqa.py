# ruleid: bare-noqa
import os  # noqa
import sys  # noqa: F401  -- intentional re-export
# ruleid: bare-type-ignore
x = 1  # type: ignore
y = 2  # type: ignore[assignment]  -- documented reason
z = 3  # noqa: E501  -- long URL below


def ok():
    pass  # noqa: E501  -- justified
