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
