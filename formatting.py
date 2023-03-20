import os
import textwrap

from pygments import highlight
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.formatters import TerminalFormatter

def format_output(input_string):
    terminal_width = os.get_terminal_size().columns
    lines = input_string.split('\n')
    formatted_output = []

    for line in lines:
        if line.startswith("```"):
            formatted_output.extend(format_code_block(line, lines, terminal_width))
        else:
            formatted_output.extend(format_line(line, terminal_width))

    return "\n".join(formatted_output)

def format_code_block(delimiter, lines, terminal_width):
    try:
        end_index = lines.index(delimiter, lines.index(delimiter) + 1)
    except ValueError:
        end_index = len(lines)

    code_block_lines = lines[lines.index(delimiter) + 1 : end_index]
    language = delimiter.strip("```")
    highlighted_code = format_highlighted_code("\n".join(code_block_lines), language)

    return format_line(highlighted_code, terminal_width)

def format_highlighted_code(code, language):
    try:
        lexer = get_lexer_by_name(language, stripall=True)
    except:
        try:
            lexer = guess_lexer(code)
        except:
            lexer = PythonLexer()

    return highlight(code, lexer, TerminalFormatter()).rstrip("\n")

def format_line(line, terminal_width):
    return textwrap.wrap(line, width=terminal_width)
