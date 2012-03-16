import cPickle as pickle
import sys
import _ast

import pyflakes.checker as pyflakes

from python_exceptions import (
    OffsetError,
    PythonError
)

def pyflakes_check(code, filename, ignore=None):
    try:
        tree = compile(code, filename, "exec", _ast.PyCF_ONLY_AST)
    except (SyntaxError, IndentationError), value:
        msg = value.args[0]

        (lineno, offset, text) = value.lineno, value.offset, value.text

        # If there's an encoding problem with the file, the text is None.
        if text is None:
            # Avoid using msg, since for the only known case, it contains a
            # bogus message that claims the encoding the file declared was
            # unknown.
            if msg.startswith('duplicate argument'):
                arg = msg.split('duplicate argument ', 1)[1].split(' ', 1)[0].strip('\'"')
                error = pyflakes.messages.DuplicateArgument(filename, value, arg)
            else:
                error = PythonError(filename, value, msg)
        else:
            line = text.splitlines()[-1]

            if offset is not None:
                offset = offset - (len(text) - len(line))

            if offset is not None:
                error = OffsetError(filename, value, msg, offset)
            else:
                error = PythonError(filename, value, msg)
        return [error]
    except ValueError, e:
        return [PythonError(filename, 0, e.args[0])]
    else:
        # Okay, it's syntactically valid.  Now check it.
        if ignore is not None:
            old_magic_globals = pyflakes._MAGIC_GLOBALS
            pyflakes._MAGIC_GLOBALS += ignore
        w = pyflakes.Checker(tree, filename)
        if ignore is not None:
            pyflakes._MAGIC_GLOBALS = old_magic_globals
        return w.messages

if __name__ == '__main__':
    filename = sys.argv[-1]
    try:
        code, filename, ignore = pickle.load(sys.stdin)
        results = pyflakes_check(code, filename, ignore=ignore)
        pickle.dump(results, sys.stdout)
    except Exception, e:
        pickle.dump(e, sys.stdout)
