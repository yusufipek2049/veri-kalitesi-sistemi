# ruleid: redundant-mapper
def identity(x):
    return x


def typed_identity(x: int) -> int:
    return x


def transform(x):
    return x * 2


def pipeline(x):
    y = x + 1
    return y
