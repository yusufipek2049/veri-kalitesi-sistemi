# ruleid: redundant-mapper
def identity(x):
    return x


# typed identity — may serve as a default callable
def typed_identity(x: int) -> int:
    return x


def transform(x):
    return x * 2


def pipeline(x):
    """Non-trivial function."""
    y = x + 1
    return y
