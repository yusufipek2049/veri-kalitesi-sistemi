# ruleid: nested-function
def outer(x):
    def inner(y):
        return y + 1
    return inner(x)


# ruleid: nested-function
def make_validator():
    def validate(value):
        return value > 0
    return validate


def flat_function(x):
    return x + 1


def decorator_factory(func):
    """Legitimate decorator — closure captures func."""
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper
