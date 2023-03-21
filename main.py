import argparse
import json
import openai
import os
import requests
import sseclient
import textwrap
import traceback

from spinner import spinner
from pathlib import Path
from prompt_toolkit import prompt
from prompt_toolkit.formatted_text import HTML
from pygments import highlight
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.formatters import TerminalFormatter

def format_output(input_string):
    terminal_width = os.get_terminal_size().columns
    lines = input_string.split('\n')
    formatted_output = []
    in_code_block = False
    code_block_lines = []

    for line in lines:
        if line.startswith("```"):
            if in_code_block:
                in_code_block = False
                block = '\n'.join(code_block_lines)
                try:
                    lexer = get_lexer_by_name(language, stripall=True)
                except:
                    try:
                        lexer = guess_lexer(block)
                    except:
                        lexer = PythonLexer()

                highlighted_code = highlight(block, lexer, TerminalFormatter())
                formatted_output.append(highlighted_code.rstrip('\n'))
                code_block_lines = []

            else:
                in_code_block = True
                language = line.strip("```")

        elif in_code_block:
            code_block_lines.append(line)
        else:
            wrapped_lines = textwrap.fill(line, width=terminal_width)
            formatted_output.extend(wrapped_lines.split("\n"))

    return "\n".join(formatted_output)

def get_api_key():
    api_key_path = Path.home() / '.config/termgpt/api_key.json'

    if api_key_path.exists():
        with api_key_path.open('r') as f:
            api_key = json.load(f)['api_key']
    else:
        print('Welcome to termGPT!')
        api_key = prompt('Please enter your OpenAI API key: ')
        api_key_path.parent.mkdir(parents=True, exist_ok=True)
        with api_key_path.open('w') as f:
            json.dump({'api_key': api_key}, f)

    return api_key

@spinner(text="Thinking...")
def get_response(messages, model):
    try:
        response = openai.ChatCompletion.create(
            model=model,
            messages=messages,
            max_tokens=2000,
            temperature=0.8,
            top_p=1,
        )
    except openai.error.InvalidRequestError:
        if len(messages) == 1:
            raise
        messages.pop(0)
        return get_response(messages, model)

    return response.choices[0].message['content'].strip()

def prompt_continuation(width, line_number, wrap_count):
    if wrap_count > 0:
        return " " * (width - 3) + "-> "
    else:
        text = "...: ".rjust(width)
        return HTML("<ansigray>%s</ansigray>") % text

# TODO
# class TokenFormatter:
#     def __init__(self):
#         self.in_code_block = False
#         self.indent_level = 0
#         self.new_line = True
# 
#     def process_token(self, token):
#         output = ""
#         if token == "```":
#             self.in_code_block = not self.in_code_block
#             output += "```"
#             if self.in_code_block:
#                 self.indent_level = 1
#             else:
#                 self.indent_level = 0
#             self.new_line = True
#         elif self.in_code_block and self.new_line:
#             output += "\t" * self.indent_level + token
#             self.new_line = token.endswith("\n")
#         else:
#             output += token
#             self.new_line = token.endswith("\n")
# 
#         return output

def stream_chat_completion(messages, model):
    headers = {'Accept': 'text/event-stream', 'Authorization': 'Bearer ' + get_api_key()}
    data = {'model': model, 'messages': messages, 'max_tokens': 2000, 'temperature': 0.8, 'stream': True}
    response = requests.post('https://api.openai.com/v1/chat/completions', headers=headers, json=data, stream=True)
    client = sseclient.SSEClient(response)
    message = ''
    skip_assistant_newlines = False
    # formatter = TokenFormatter()

    for event in client.events():
        if event.event == 'message':
            try:
                data = json.loads(event.data)
                if 'role' in data['choices'][0]['delta']:
                    skip_assistant_newlines = True
            except:
                pass
            if data == '[DONE]':
                break
            else:
                try:
                    token = data['choices'][0]['delta']['content']
                    if token == '\n\n' and skip_assistant_newlines:
                        skip_assistant_newlines = False
                        continue

                    message += token
                    print(token, end='', flush=True)
                    # formatted_token = formatter.process_token(token)
                    # print(formatted_token, end='', flush=True)
                except:
                    pass
    return message

def main():
    parser = argparse.ArgumentParser(description="A CLI wrapper for OpenAI API with chat interface.")
    parser.add_argument(
        "--model",
        type=str,
        default="gpt-3.5-turbo",
        help="The model to use for the chat. Default is 'gpt-3.5-turbo'.",
    )

    parser.add_argument(
        '--stream',
        action="store_true",
        help="Enable token streaming",
    )

    args = parser.parse_args()
    openai.api_key = get_api_key()

    messages = []
    end_chat = False
    skip_input = False
    color = {
        'gpt-4': 'ansigreen',
        'gpt-3.5-turbo': 'ansicyan',
    }[args.model]

    while not end_chat:
        try:
            if not skip_input:
                try:
                    user_input = prompt(
                        HTML(f"<{color}>termGPT> </{color}>"),
                        multiline=True,
                        prompt_continuation=prompt_continuation
                    )

                except EOFError:
                    end_chat = True
                    continue
                except KeyboardInterrupt:
                    continue
                if user_input.lower() == "quit":
                    end_chat = True
                    continue

                messages.append({"role": "user", "content": user_input})

            # Make the API call
            try:
                if args.stream:
                    print()
                    assistant_response = stream_chat_completion(messages, args.model)
                    print('\n')
                else:
                    assistant_response = get_response(messages, args.model)
                    print(f"\n{format_output(assistant_response)}\n")
            except KeyboardInterrupt:
                print()
                continue

            messages.append({"role": "assistant", "content": assistant_response})

        except:
            traceback.print_exc()
            end_chat = True

if __name__ == '__main__':
    main()
