import os
import re
import shutil
import sys

import logging
import logging.config

logging_config = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file_handler': {
            'class': 'logging.FileHandler',
            'filename': '/tmp/formatter.log',
            'mode': 'w',
            'formatter': 'my_formatter',
        },
    },
    'formatters': {
        'my_formatter': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        },
    },
    'loggers': {
        '': {
            'handlers': ['file_handler'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}

logging.config.dictConfig(logging_config)

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

    def syntax_highlight(self, token):
        highlighted_token = token
        set_in_string = False

        keywords = set(['if', 'else', 'for', 'while', 'return', 'class',
            'def', 'function', 'import', 'from', 'export', 'const',
            'let', 'var', 'switch', 'case', 'try', 'catch', 'finally',
            'break', 'continue', 'with', 'as', 'in', 'match', 'case',
        ])

        s_token = token.strip()

        if s_token in keywords and not self.in_string and not self.in_comment:
            highlighted_token = '\033[1;36m' + token + '\033[0m'

        comment_start = re.compile('\/\/|\/\*|\#')

        if comment_start.match(s_token) and not self.in_string:
            self.in_comment = True
            highlighted_token = '\033[1;30m' + token + '\033[0m'

        if self.in_comment and '\n' in token:
            self.in_comment = False

        if self.in_comment and s_token.endswith('*/'):
            self.in_comment = False
            highlighted_token = '\033[1;30m' + token + '\033[0m'

        string_start = re.compile('\"|\'')
        string_match = string_start.search(s_token)
        if string_match and not self.in_string and not self.in_comment:
            self.in_string = True
            self.string_delimiter = string_match[0]
            delimiter_index = token.index(self.string_delimiter)
            logging.debug('in the opening branch')
            logging.debug(f'token = <{token}>')
            logging.debug(f'delim_i = {delimiter_index}')
            highlighted_token = token[:delimiter_index] +'\033[1;32m' + token[delimiter_index:] +'\033[0m'
            logging.debug(f'upto = <{token[:delimiter_index]}>')
            logging.debug(f'past = <{token[delimiter_index:]}>')
            logging.debug(f'hi_token = <{highlighted_token}>')
            if len(string_start.findall(s_token)) != 2 or token[delimiter_index - 1] =='\\':
                set_in_string = True

        if not set_in_string and self.in_string and self.string_delimiter in s_token:
            delimiter_index = token.index(self.string_delimiter)
            if token[delimiter_index - 1] != '\\':
                self.in_string = False
                highlighted_token ='\033[1;32m' + token[:delimiter_index+1] +'\033[0m' + token[delimiter_index+1:]
            else:
                highlighted_token ='\033[1;32m' + token +'\033[0m'

            logging.debug('in the closure branch')
            logging.debug(f'token = <{token}>')
            logging.debug(f'delim_i = {delimiter_index}')
            logging.debug(f'upto = <{token[:delimiter_index+1]}>')
            logging.debug(f'past = <{token[delimiter_index+1:]}>')
            logging.debug(f'hi_token = <{highlighted_token}>')

        if not set_in_string and self.in_string or self.in_comment:
            logging.debug('in the current branch')
            highlighted_token ='\033[1;32m' + token +'\033[0m'
            logging.debug(f'token = <{token}>')
            logging.debug(f'hi_token = <{highlighted_token}>')

        if s_token.isdigit() and not self.in_string and not self.in_comment:
            highlighted_token = '\033[1;31m' + token + '\033[0m'

        return highlighted_token
