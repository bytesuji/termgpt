import os
import re
import shutil
import sys

# ANSI escape codes
RESET = '\033[0m'
STRING_COLOR = '\033[1;32m'
NEUTRAL_COLOR = '\033[1;30m'
KEYWORD_COLOR = '\033[1;93m'
VALUE_COLOR = '\033[1;31m'
TYPE_COLOR = '\033[1;36m'

class TokenFormatter:
    def __init__(self):
        self.code_block = False
        self.terminal_width = 0
        self.current_line_len = 0
        self.in_string = False
        self.in_comment = False
        self.string_delimiter = None

        self.consecutive_ticks = 0
        self.last_was_tick = False
        self.prev_token = ""

        self.operators = ['+', '-', '*', '/', '%', '//', '**', '==', '!=', '<', '>', '<=', '>=', '&', '|', '^', '~', '<<', '>>']

    def _update_terminal_width(self):
        width, _ = shutil.get_terminal_size()
        self.terminal_width = width

    @staticmethod
    def _count_leading_ticks(s):
        count = 0
        for c in s:
            if c == '`':
                count += 1
            else:
                break

        return count

    def _watch_for_codeblock(self, token):
        token = token.strip()
        if not token:
            return

        tick_count = self._count_leading_ticks(token)

        if self.last_was_tick:
            self.consecutive_ticks += tick_count
        else:
            self.consecutive_ticks = tick_count
        
        self.last_was_tick = token[-1] == '`'

        if self.consecutive_ticks == 3:
            self.consecutive_ticks = 0
            self.code_block = not self.code_block
            print()
            self.current_line_len = 0

    def process_token(self, token):
        self._update_terminal_width()
        self._watch_for_codeblock(token)

        if self.code_block:
            self.print_code_token(token)
        else:
            self.print_token(token)

        self.prev_token = token

    def print_token(self, token):
        if self.current_line_len + len(token) + 1 > self.terminal_width:
            print()
            self.current_line_len = 0

        if '\n' in token:
            self.current_line_len = 0

        sys.stdout.write(token)
        sys.stdout.flush()
        self.current_line_len += len(token)

    def print_code_token(self, token):
        ht = self.syntax_highlight(token)
        sys.stdout.write(ht)
        sys.stdout.flush()

    def is_keyword(self, token):
        keywords = set(['if', 'else', 'for', 'while', 'return', 'class',
            'def', 'function', 'import', 'from', 'export', 'const',
            'let', 'var', 'switch', 'case', 'try', 'catch', 'finally',
            'break', 'continue', 'with', 'as', 'in', 'match', 'case',
            'elif',
        ])

        return token in keywords

    def is_typeval(self, token):
        types_and_values = set(['int', 'float', 'str', 'bool',
            'None', 'True', 'False','complex', 'tuple', 'list',
            'dict', 'set', 'frozenset', 'bytes', 'bytearray',
            'memoryview', 'range', 'enumerate', 'len', 'print',
            'exit',
        ])

        result = token in types_and_values
        result = result or token + '(' in types_and_values
        return result

    def is_digit(self, token):
        prev = self.prev_token
        try:
            last_char = prev[-1]
        except:
            last_char = None

        result = token.isdigit()
        result = result and \
                (prev.strip().isdigit() \
                or last_char in ' ({[.' \
                or prev.strip() in self.operators)

        return result

    def syntax_highlight(self, token):
        highlighted_token = token
        set_in_string = False

        s_token = token.strip()

        if self.is_keyword(s_token) and not self.in_string and not self.in_comment:
            highlighted_token = KEYWORD_COLOR + token + RESET

        if self.is_typeval(s_token) and not self.in_string and not self.in_comment:
            highlighted_token = TYPE_COLOR + token + RESET

        comment_start = re.compile('\/\/|\/\*|\#')

        if comment_start.match(s_token) and not self.in_string:
            self.in_comment = True
            highlighted_token = NEUTRAL_COLOR + token + RESET

        if self.in_comment and '\n' in token:
            self.in_comment = False

        if self.in_comment and s_token.endswith('*/'):
            self.in_comment = False
            highlighted_token = NEUTRAL_COLOR + token + RESET

        string_start = re.compile('\"|\'')
        string_match = string_start.search(s_token)
        if string_match and not self.in_string and not self.in_comment:
            self.in_string = True
            self.string_delimiter = string_match[0]
            delimiter_index = token.index(self.string_delimiter)
            highlighted_token = token[:delimiter_index] + STRING_COLOR + token[delimiter_index:] + RESET
            if len(string_start.findall(s_token)) != 2 or token[delimiter_index - 1] =='\\':
                set_in_string = True

        if not set_in_string and self.in_string and self.string_delimiter in s_token:
            delimiter_index = token.index(self.string_delimiter)
            if token[delimiter_index - 1] != '\\':
                self.in_string = False
                highlighted_token = STRING_COLOR + token[:delimiter_index+1] + RESET + token[delimiter_index+1:]
            else:
                highlighted_token = STRING_COLOR + token + RESET

        if not set_in_string and self.in_string or self.in_comment:
            highlighted_token = STRING_COLOR + token + RESET

        if self.is_digit(s_token) and not self.in_string and not self.in_comment:
            highlighted_token = VALUE_COLOR + token + RESET

        return highlighted_token
