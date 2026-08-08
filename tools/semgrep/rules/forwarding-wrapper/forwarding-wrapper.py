def _compute(x):
    return x * 2


# ruleid: forwarding-wrapper
def wrapper(x):
    return _compute(x)


def real_function(x):
    if x < 0:
        raise ValueError
    return _compute(x)


class Foo:
    def __call__(self, x):
        return _compute(x)
