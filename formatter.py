import os
import re
import shutil
import sys
# 
# class TokenFormatter:
#     def __init__(self):
#         self.code_block = False
#         self.terminal_width = 0
#         self.current_line_len = 0
#         self.watch_for_codeblock = False
# 
#     def _update_terminal_width(self):
#         width, _ = shutil.get_terminal_size()
#         self.terminal_width = width
# 
#     def process_token(self, token):
#         self._update_terminal_width()
# 
#         if token.strip() == '``':
#             self.watch_for_codeblock = True
#             return
# 
#         if token.strip() == '`':
#             if self.watch_for_codeblock:
#                 self.code_block = not self.code_block
#                 print()
#                 self.current_line_len = 0
#                 return
# 
#         if self.code_block:
#             self.print_code_token(token)
#         else:
#             self.print_token(token)
# 
#     def print_token(self, token):
#         if self.current_line_len + len(token) + 1 > self.terminal_width:
#             print()
#             self.current_line_len = 0
# 
#         sys.stdout.write(token)
#         sys.stdout.flush()
#         self.current_line_len += len(token)
# 
#     def print_code_token(self, token):
#         ht = self.syntax_highlight(token)
#         sys.stdout.write(ht)
#         sys.stdout.flush()
# 
#     def syntax_highlight(self, token):
#         highlighted_token = token
# 
#         keywords = set(['if', 'else', 'for', 'while', 'return', 'class',
#             'def', 'function', 'import', 'from', 'export', 'const',
#             'let', 'var', 'switch', 'case', 'try', 'catch', 'finally',
#             'break', 'continue',
#         ])
# 
#         s_token = token.strip()
# 
#         if s_token in keywords:
#             highlighted_token = '\033[1;36m' + token + '\033[0m'
# 
#         comment_start = re.compile('\/\/|\/\*|\#')
#         if comment_start.match(s_token):
#             highlighted_token = '\033[1;30m' + token + '\033[0m'
# 
#         string_start = re.compile('\"|\'')
# 
#         if string_start.match(s_token):
#             highlighted_token = '\033[1;32m' + token + '\033[0m'
# 
#         if s_token.isdigit():
#             highlighted_token = '\033[1;31m' + token + '\033[0m'
# 
#         return highlighted_token

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

        sys.stdout.write(token)
        sys.stdout.flush()
        self.current_line_len += len(token)

    def print_code_token(self, token):
        ht = self.syntax_highlight(token)
        sys.stdout.write(ht)
        sys.stdout.flush()

    def syntax_highlight(self, token):
        highlighted_token = token

        keywords = set(['if', 'else', 'for', 'while', 'return', 'class',
            'def', 'function', 'import', 'from', 'export', 'const',
            'let', 'var', 'switch', 'case', 'try', 'catch', 'finally',
            'break', 'continue',
        ])

        s_token = token.strip()

        if s_token in keywords and not self.in_string and not self.in_comment:
            highlighted_token = '\033[1;36m' + token + '\033[0m'

        comment_start = re.compile('\/\/|\/\*|\#')

        if comment_start.match(s_token) and not self.in_string:
            self.in_comment = True
            highlighted_token = '\033[1;30m' + token + '\033[0m'

        if self.in_comment and s_token.endswith('*/'):
            self.in_comment = False
            highlighted_token = '\033[1;30m' + token + '\033[0m'

        string_start = re.compile('\"|\'')

        if string_start.match(s_token) and not self.in_string and not self.in_comment:
            self.in_string = True
            self.string_delimiter = s_token[0]
            highlighted_token = '\033[1;32m' + token + '\033[0m'

        if self.in_string and s_token.endswith(self.string_delimiter):
            self.in_string = False
            highlighted_token = '\033[1;32m' + token + '\033[0m'

        if self.in_string or self.in_comment:
            highlighted_token = '\033[1;32m' + token + '\033[0m'

        if s_token.isdigit() and not self.in_string and not self.in_comment:
            highlighted_token = '\033[1;31m' + token + '\033[0m'

        return highlighted_token
