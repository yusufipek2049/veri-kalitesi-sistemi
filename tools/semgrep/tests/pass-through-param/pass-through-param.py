def _inner(x, y):
    return x + y


# ruleid: pass-through-param
def middle(x, y):
    return _inner(x, y)


# transforms y before passing — should not match
def transform_middle(x, y):
    y = y * 2
    return _inner(x, y)


# adds validation — should not match
def validated_middle(x, y):
    if x < 0:
        raise ValueError
    return _inner(x, y)
