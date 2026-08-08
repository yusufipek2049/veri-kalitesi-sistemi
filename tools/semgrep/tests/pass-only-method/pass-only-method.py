# ruleid: pass-only-method
class MyService:
    def on_error(self, exc):
        pass

    def real_method(self):
        return 1


# MyInit has __init__ with pass — excluded by pattern-not
class MyInit:
    def __init__(self):
        pass

    def work(self):
        return 2


# MyDel has __del__ with pass — excluded by pattern-not
class MyDel:
    def __del__(self):
        pass


class EmptyClass:
    pass
