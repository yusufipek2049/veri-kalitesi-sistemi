# ruleid: duplicate-except-handler
try:
    x = 1
except ValueError:
    raise RuntimeError("bad value")
except TypeError:
    raise RuntimeError("bad value")


try:
    y = 2
except ValueError:
    raise RuntimeError("value error")
except TypeError:
    raise RuntimeError("type error")


try:
    z = 3
except ValueError as e1:
    log(e1)
except TypeError as e2:
    log(e2)
