def _inner(x, y):
    return x + y


# ruleid: pass-through-param
def middle(x, y):
    return _inner(x, y)
