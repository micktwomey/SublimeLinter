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

import pyflakes.checker as pyflakes

from base_linter import BaseLinter
from python_exceptions import (
    OffsetError,
    Pep8Warning,
    Pep8Error,
)
from python_external import (
    pep8_check,
    pyflakes_check,
)

pyflakes.messages.Message.__str__ = lambda self: self.message % self.message_args

CONFIG = {
    'language': 'python',
    "executable": sys.executable,
}

def external_check(code, filename, pep8_ignore, pyflakes_ignore):
    env = {
        "PYTHONPATH": ":".join([
            os.path.join(os.path.dirname(__file__)),
            os.path.join(os.path.dirname(__file__), "libs"),
        ])
    }
    cmd = [sys.executable, "-m", "python_external"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    stdout, stderr = p.communicate(pickle.dumps((code, filename, pep8_ignore, pyflakes_ignore)))
    if stderr:
        print "stderr from {!r}: {}".format(cmd, stderr)
    output = pickle.loads(stdout)
    if isinstance(output, Exception):
        raise output
    return output

class Linter(BaseLinter):

    def executable_check(self, view, code, filename):
        return self.built_in_check(view, code, filename)

    def built_in_check(self, view, code, filename):
        errors = []

        pep8_ignore = view.settings().get('pep8_ignore', [])
        pyflakes_ignore = view.settings().get('pyflakes_ignore', None)
        pyflakes_disabled = view.settings().get('pyflakes_disabled', False)

        if not pyflakes_disabled:
            if self.executable:
                print "Using %s for pyflakes and pep8" % self.executable
                pep8_results, pyflakes_results = external_check(code, filename, pep8_ignore, pyflakes_ignore)
                errors.extend(pep8_results)
                errors.extend(pyflakes_results)
            else:
                print "Using sublime's python for pyflakes and pep8"
                errors.extend(pep8_check(code, filename, ignore=pep8_ignore))
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

            elif isinstance(error, OffsetError):
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
