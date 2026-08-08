# ruleid: pass-only-function
def stub_callback():
    pass


# ruleid: pass-only-function
def unused_helper(x, y):
    pass


def real_function():
    return 42


def function_with_docstring():
    """This is a documented no-op placeholder."""
    pass


def function_with_body():
    x = 1
    pass
