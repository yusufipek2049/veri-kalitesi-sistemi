# ruleid: single-method-adapter
class JsonFormatter:
    def format(self, data):
        return str(data)


# ruleid: single-method-adapter
class ConfigFormatter:
    def __init__(self, indent):
        self.indent = indent

    def format(self, data):
        return str(data)


# CsvFormatter implements base class — not matched (has base)
class CsvFormatter(BaseFormatter):
    def format(self, data):
        return ",".join(data)


# CallableHandler uses __call__ — excluded by pattern-not
class CallableHandler:
    def __call__(self, request):
        return request
