# -*- coding: utf-8 -*-
# python.py - Lint checking for Python - given filename and contents of the code:
# It provides a list of line numbers to outline and offsets to highlight.
#
# This specific module is part of the SublimeLinter project.
# It is a fork by André Roberge from the original SublimeLint project,
# (c) 2011 Ryan Hileman and licensed under the MIT license.
# URL: http://bochs.info/
#
# The original copyright notices for this file/project follows:
#
# (c) 2005-2008 Divmod, Inc.
# See LICENSE file for details
#
# The LICENSE file is as follows:
#
# Copyright (c) 2005 Divmod, Inc., http://www.divmod.com/
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

# TODO:
# * fix regex for variable names inside strings (quotes)

import cPickle as pickle
import os
import subprocess
import re
import sys

import pep8
import pyflakes.checker as pyflakes

from base_linter import BaseLinter
import python_exceptions
sys.modules["python_exceptions"] = python_exceptions
from python_exceptions import OffsetError
import sublimelinter.modules.python_exceptions
sys.modules["sublimelinter.modules.python_exceptions"] = sublimelinter.modules.python_exceptions
from sublimelinter.modules.python_exceptions import OffsetError as OffsetError2
from sublimelinter.modules.python_exceptions import PythonError as PythonError2
from python_external import pyflakes_check

pyflakes.messages.Message.__str__ = lambda self: self.message % self.message_args

CONFIG = {
    'language': 'python',
    "executable": sys.executable,
}

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

class Dict2Obj:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

def external_pyflakes(code, filename, ignore=None):
    env = {
        "PYTHONPATH": ":".join([
            os.path.join(os.path.dirname(__file__)),
            os.path.join(os.path.dirname(__file__), "libs"),
        ])
    }
    cmd = [sys.executable, "-m", "python_external"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    stdout, stderr = p.communicate(pickle.dumps((code, filename, ignore)))
    if stderr:
        print "stderr from {!r}: {}".format(cmd, stderr)
    output = pickle.loads(stdout)
    return output

class Linter(BaseLinter):
    def pep8_check(self, code, filename, ignore=None):
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

    def executable_check(self, view, code, filename):
        return self.built_in_check(view, code, filename)

    def built_in_check(self, view, code, filename):
        errors = []

        if view.settings().get("pep8", True):
            errors.extend(self.pep8_check(code, filename, ignore=view.settings().get('pep8_ignore', [])))

        pyflakes_ignore = view.settings().get('pyflakes_ignore', None)
        pyflakes_disabled = view.settings().get('pyflakes_disabled', False)

        if not pyflakes_disabled:
            if self.executable:
                print "Using %s for pyflakes" % self.executable
                errors.extend(external_pyflakes(code, filename, pyflakes_ignore))
            else:
                print "Using sublime's python for pyflakes"
                errors.extend(pyflakes_check(code, filename, pyflakes_ignore))

        return errors

    def parse_errors(self, view, errors, lines, errorUnderlines, violationUnderlines, warningUnderlines, errorMessages, violationMessages, warningMessages):

        def underline_word(lineno, word, underlines):
            regex = r'((and|or|not|if|elif|while|in)\s+|[+\-*^%%<>=\(\{{])*\s*(?P<underline>[\w\.]*{0}[\w]*)'.format(re.escape(word))
            self.underline_regex(view, lineno, regex, lines, underlines, word)

        def underline_import(lineno, word, underlines):
            linematch = '(from\s+[\w_\.]+\s+)?import\s+(?P<match>[^#;]+)'
            regex = '(^|\s+|,\s*|as\s+)(?P<underline>[\w]*{0}[\w]*)'.format(re.escape(word))
            self.underline_regex(view, lineno, regex, lines, underlines, word, linematch)

        def underline_for_var(lineno, word, underlines):
            regex = 'for\s+(?P<underline>[\w]*{0}[\w*])'.format(re.escape(word))
            self.underline_regex(view, lineno, regex, lines, underlines, word)

        def underline_duplicate_argument(lineno, word, underlines):
            regex = 'def [\w_]+\(.*?(?P<underline>[\w]*{0}[\w]*)'.format(re.escape(word))
            self.underline_regex(view, lineno, regex, lines, underlines, word)

        errors.sort(lambda a, b: cmp(a.lineno, b.lineno))
        ignoreImportStar = view.settings().get('pyflakes_ignore_import_*', True)

        for error in errors:
            if error.level == 'E':
                messages = errorMessages
                underlines = errorUnderlines
            elif error.level == 'V':
                messages = violationMessages
                underlines = violationUnderlines
            elif error.level == 'W':
                messages = warningMessages
                underlines = warningUnderlines

            if isinstance(error, pyflakes.messages.ImportStarUsed) and ignoreImportStar:
                continue

            self.add_message(error.lineno, lines, str(error), messages)

            if isinstance(error, (Pep8Error, Pep8Warning)):
                self.underline_range(view, error.lineno, error.col, underlines)

            elif isinstance(error, (OffsetError, OffsetError2)):
                self.underline_range(view, error.lineno, error.offset, underlines)

            elif isinstance(error, (pyflakes.messages.RedefinedWhileUnused,
                                    pyflakes.messages.UndefinedName,
                                    pyflakes.messages.UndefinedExport,
                                    pyflakes.messages.UndefinedLocal,
                                    pyflakes.messages.RedefinedFunction,
                                    pyflakes.messages.UnusedVariable)):
                underline_word(error.lineno, error.name, underlines)

            elif isinstance(error, pyflakes.messages.ImportShadowedByLoopVar):
                underline_for_var(error.lineno, error.name, underlines)

            elif isinstance(error, pyflakes.messages.UnusedImport):
                underline_import(error.lineno, error.name, underlines)

            elif isinstance(error, pyflakes.messages.ImportStarUsed):
                underline_import(error.lineno, '*', underlines)

            elif isinstance(error, pyflakes.messages.DuplicateArgument):
                underline_duplicate_argument(error.lineno, error.name, underlines)

            elif isinstance(error, pyflakes.messages.LateFutureImport):
                pass

            else:
                print 'Oops, we missed an error type!', type(error), str(error), repr(error)
