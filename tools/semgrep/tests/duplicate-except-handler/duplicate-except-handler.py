# ruleid: duplicate-except-handler
try:
    x = 1
except ValueError:
    raise RuntimeError("bad value")
except TypeError:
    raise RuntimeError("bad value")


# different bodies — should not match
try:
    y = 2
except ValueError:
    raise RuntimeError("value error")
except TypeError:
    raise RuntimeError("type error")


# uses `as` variable — should not match
try:
    z = 3
except ValueError as e1:
    log(e1)
except TypeError as e2:
    log(e2)
