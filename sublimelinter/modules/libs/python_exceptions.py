import pyflakes.checker as pyflakes

class PythonError(pyflakes.messages.Message):
    message = '%r'

    def __init__(self, filename, loc, text):
        pyflakes.messages.Message.__init__(self, filename, loc, level='E', message_args=(text,))
        self.text = text

class OffsetError(pyflakes.messages.Message):
    message = '%r at column %r'

    def __init__(self, filename, loc, text, offset):
        pyflakes.messages.Message.__init__(self, filename, loc, level='E', message_args=(text, offset + 1))
        self.text = text
        self.offset = offset

class Pep8Error(pyflakes.messages.Message):
    message = 'PEP 8 (%s): %s'

    def __init__(self, filename, loc, code, text):
        # PEP 8 Errors are downgraded to "warnings"
        pyflakes.messages.Message.__init__(self, filename, loc, level='W', message_args=(code, text))
        self.text = text


class Pep8Warning(pyflakes.messages.Message):
    message = 'PEP 8 (%s): %s'

    def __init__(self, filename, loc, code, text):
        # PEP 8 Warnings are downgraded to "violations"
        pyflakes.messages.Message.__init__(self, filename, loc, level='V', message_args=(code, text))
        self.text = text
