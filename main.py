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

def stream_chat_completion(messages, model): # TODO use streaming
    headers = {
        'Accept': 'text/event-stream',
        'Authorization': 'Bearer ' + get_api_key()
    }

    data = {
      "model": model,
      "messages": messages,
      "max_tokens": 2000,
      "temperature": 0.8,
      "stream": True,
    }

    response = requests.post('https://api.openai.com/v1/chat/completions', headers=headers, json=data, stream=True)
    client = sseclient.SSEClient(response)
    message = ""
    for event in client.events():
        if event.event == 'message':
            try:
                data = json.loads(event.data)
            except:
                pass
            if data == '[DONE]':
                print('done')
                break
            else:
                try:
                    token = data['choices'][0]['delta']['content']
                    message += token
                    print(token, end='', flush=True)
                except:
                    pass

    return message

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
        return HTML("<strong>%s</strong>") % text

def main():
    parser = argparse.ArgumentParser(description="A CLI wrapper for OpenAI API with chat interface.")
    parser.add_argument(
        "--model",
        type=str,
        default="gpt-3.5-turbo",
        help="The model to use for the chat. Default is 'gpt-3.5-turbo'.",
    )

    args = parser.parse_args()
    openai.api_key = get_api_key()

    messages = []
    end_chat = False
    skip_input = False

    while not end_chat:
        try:
            if not skip_input:
                try:
                    user_input = prompt(
                        HTML("<ansigreen>termGPT> </ansigreen>"),
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
            assistant_response = get_response(messages, args.model)
            print(f"\n{format_output(assistant_response)}\n")
            skip_input = False

            # try:
            #     assistant_response = stream_chat_completion(messages, args.model)
            #     print()
            #     skip_input = False
            # except:
            #     continue

            messages.append({"role": "assistant", "content": assistant_response})

        except:
            traceback.print_exc()
            end_chat = True

if __name__ == '__main__':
    main()
