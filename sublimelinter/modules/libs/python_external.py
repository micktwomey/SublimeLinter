import cPickle as pickle
import sys
import _ast

import pep8

import pyflakes.checker as pyflakes

from python_exceptions import (
    OffsetError,
    PythonError,
    Pep8Error,
    Pep8Warning
)

class Dict2Obj:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

def pep8_check(code, filename, ignore=None):
        messages = []
        _lines = code.split('\n')

        if _lines:
            def report_error(self, line_number, offset, text, check):
                code = text[:4]
                msg = text[5:]

                if pep8.ignore_code(code):
                    return
                elif code.startswith('E'):
                    messages.append(Pep8Error(filename, Dict2Obj(lineno=line_number, col_offset=offset), code, msg))
                else:
                    messages.append(Pep8Warning(filename, Dict2Obj(lineno=line_number, col_offset=offset), code, msg))

            pep8.Checker.report_error = report_error
            _ignore = ignore + pep8.DEFAULT_IGNORE.split(',')

            class FakeOptions:
                verbose = 0
                select = []
                ignore = _ignore

            pep8.options = FakeOptions()
            pep8.options.physical_checks = pep8.find_checks('physical_line')
            pep8.options.logical_checks = pep8.find_checks('logical_line')
            pep8.options.counters = dict.fromkeys(pep8.BENCHMARK_KEYS, 0)
            good_lines = [l + '\n' for l in _lines]
            good_lines[-1] = good_lines[-1].rstrip('\n')

            if not good_lines[-1]:
                good_lines = good_lines[:-1]

            try:
                pep8.Checker(filename, good_lines).check_all()
            except:
                pass

        return messages

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
        code, filename, pep8_ignore, pyflakes_ignore = pickle.load(sys.stdin)
        pyflakes_results = pyflakes_check(code, filename, ignore=pyflakes_ignore)
        pep8_results = pep8_check(code, filename, ignore=pep8_ignore)
        pickle.dump((pep8_results, pyflakes_results), sys.stdout)
    except Exception, e:
        pickle.dump(e, sys.stdout)
