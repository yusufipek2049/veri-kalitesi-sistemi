def _compute(x):
    return x * 2


# ruleid: forwarding-wrapper
def wrapper(x):
    return _compute(x)


def real_function(x):
    """Adds validation before delegating."""
    if x < 0:
        raise ValueError
    return _compute(x)


class Foo:
    # __call__ is excluded from forwarding-wrapper
    def __call__(self, x):
        return _compute(x)
