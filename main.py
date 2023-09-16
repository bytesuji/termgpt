import argparse
import json
import openai
import os
import requests
import sseclient
import textwrap
import traceback

from formatter import TokenFormatter
from spinner import spinner
from pathlib import Path
from prompt_toolkit import prompt
from prompt_toolkit.formatted_text import HTML
from pygments import highlight
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.formatters import TerminalFormatter

SYSTEM_PROMPT = None

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
            messages=messages[-8:],
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

def _stream_message(client, tokens, use_formatter=True):
    token_fmt = TokenFormatter()
    last_event_role = None
    last_token = ''

    for event in client.events():
        if event.event != 'message':
            continue
        if event.data == '[DONE]':
            continue

        data = json.loads(event.data)
        current_event_role = data.get('choices', [{}])[0].get('delta', {}).get('role', None)
        token = data.get('choices', [{}])[0].get('delta', {}).get('content', None)
        if last_event_role == 'assistant' and token == '\n\n':
            last_event_role = None
            continue

        if token:
            if last_token:
                token = last_token + token
                last_token = ''
            if '`' in token and len(token) < 3:
                last_token = token
                continue

            tokens.append(token)
            if use_formatter:
                token_fmt.process_token(token)
            else:
                print(token, end='', flush=True)

        last_event_role = current_event_role

def stream_chat_completion(messages, model):
    headers = {'Accept': 'text/event-stream', 'Authorization': 'Bearer ' + get_api_key()}
    data = {'model': model, 'messages': messages, 'max_tokens': 2000, 'temperature': 0.88888888, 'stream': True}
    response = requests.post('https://api.openai.com/v1/chat/completions', headers=headers, json=data, stream=True)
    client = sseclient.SSEClient(response)
    tokens = []

    if response.status_code != 200:
        if len(messages) == 1:
            raise
        messages.pop(0)
        return stream_chat_completion(messages, model)

    try:
        _stream_message(client, tokens)
    except KeyboardInterrupt:
        pass

    return ''.join(tokens)

def main():
    parser = argparse.ArgumentParser(description="A CLI wrapper for OpenAI API with chat interface.")
    parser.add_argument(
        "--model",
        type=str,
        default="gpt-4-0314",
        help="The model to use for the chat. Default is 'gpt-4'",
    )

    parser.add_argument(
        '--syntax',
        action="store_true",
        help="Enable syntax highlighting",
    )

    args = parser.parse_args()
    openai.api_key = get_api_key()

    messages = []
    end_chat = False
    skip_input = False
    color = {
        'gpt-4-0314': 'ansigreen',
        'gpt-4': 'ansigreen',
        'gpt-3.5-turbo': 'ansicyan',
    }[args.model]

    # system_prompt = "Respond as concisely as possible. Include minimal explanation and exposition. Answer the question briefly, directly, and simply. Only elaborate if explicitly asked."
    # system_prompt = "generally, respond with an answer that attempts to reason from first principles if the query is complex; or concisely and informatively if the query is direct. aim for simplicity and efficiency without reducing important details. do not include any unnecessary words."
    system_prompt = """built for `emergence`..
# UX
Evolution especially at the level of information is a gradual accretive
process that sometimes makes it difficult to see the gradual unfolding of the
pattern over time, even as one inhabits it. Yet specifically in the realm of
information, higher order effects make it a process that to those not aware
may appear as if full of step functions - seemingly radical and random
upheavals of the emergent order at the dynamic equilibrium. Yet the goal of
our systems should be to support us in our growing ability to see these as
less spooky and threatening "force majeure" and instead definable and
specific, frequently cyclical, components in an otherwise robust (but
crucially, understandable!) unstoppable fragile well-spring of civilizational
intelligence at 7T and growing. 📈
Below are some helpful "intuition pumps" to include in your ontology:
![](flow.png)
- **Gradient Flows**: To powerhouse the attractor landscape concept, gradient
flows—which are trajectories moving across this field—can help visualize how
decisions evolve over time, nudged by the competing attractors of the various
sub-objectives. This shows actions moving in the direction of the most
significant increase or decrease in the function and visually implies that
decisions travel the path of least resistance towards goals. It's similar to
water flowing down a hill following the steepest descent.
- **Buffer Zones and Trampolines**: These are graphical mechanisms for
showcasing variability and unexpected events in the system. Buffer zones
could be depicted as wider areas around trajectory lines, signaling a degree
of expected deviation in action, while trampolines could symbolize discrete
decision points where a certain external or internal condition significantly
fluctuates the trajectory. Such illustrations provide a more realistic
representation of the non-linearities and abrupt trends often observed in
complex decision-making environments.
- **Color-Coded and Transformable Links**: Links between decision nodes can be
used to reflect the strength or relevance of the relationships between
different components of the system. Changing aspects like thickness, patterns
(dashed, dotted), color intensities dynamically based on time/frame, could
enhance the context of functional connections and degree of interaction.
- **Halo, Shadow, or Glow Effects**: Employing such visual effects around
nodes or decisions might be useful to denote influence radius, urgency
levels, risk associated to provinces of decision nodes. Different colors
might signify various scenario categories.- **Animations**: Animations can play a crucial role in depicting temporal
changes, interactions, or derivatives, progressively growing or knocked-down
impacts of changes (rippling effect). Animated manipulations should bring
alive the diagram in a way that the user can better intuit or empathize with
system dynamics: emergence, turbulences, homeostasis, and periodicity.
- **Auditory or Unanticipated Visual Cues:** Periodically including souvenirs
or brief changes in visuals (flashing lights, abrupt color swaps) can serve
as signals for prompt direct attention from the observer, warning about
significant alterations or critical states requiring immediate engagement.
Collectively, these visualizations provide an immersive experience to the
users, fostering enhanced comprehension of unique strengths, vulnerabilities
of the systems evolution pattern. Use should illustrate temporal or
exploratory scenarios offering systemic insights leading to more informed,
robust realisations and decisions.
# Theory
To concisely characterize the Cognitive Flows Framework within a Categorical
perspective, we'll employ some fundamental concepts and symbols from Category
Theory.
1. **Objects**: These map to the individual components within the cognitive
flows. May be presented as $A, B, C$.
1. **Morphisms**: Represent transformations or operations between objects,
i.e., the 'flows'. For example, if object $A$ is transformed into object $B$
via operation $f$, it can be denoted as: $f: A \\rightarrow B$.
1. **Symmetric Monoidal Structure**: This signifies the existence of
composition, associativity, and identity in a category:
Composition – If we have two morphisms $f: A \\rightarrow B$ and $g: B
\\rightarrow C$, their composition $h = g \\circ f$ would mean $h : A
\\rightarrow C$.
Associativity – If we have three morphisms $f$, $g$, and $h$ s.t. $h = g
\\circ f$ and $i = h \\circ g$, then $i = (h \\circ g) \\circ f = h \\circ
(g \\circ f)$.
Identity – For every object $A$, there exists an identity morphism, denoted
as $1_A$, such that for any morphism $f : A \\rightarrow B$, $f \\circ 1_A
= f = 1_B \\circ f$.
1. **Natural Isomorphisms**: Ideally signifying the existence of reversible
transformations within our framework (like buffer zones or trampolines). If a
transformation $f$ is reversible, there exists a reverse transformation $g$
such that $g \\circ f = 1_A$ and $f \\circ g = 1_B$. $f$ would then be an
isomorphism.1. **Properties**: Additional parameters of morphisms, like effects, can be
represented by extending our morphisms or adding additional structure on
objects, tweaking the formal expressions as needed.
1. **Special Cases or Exceptions**: Fall under specific conditions of our
morphisms; can be defined using the language of subcategories or monoidal
functors, preserving a part of the structure.
Therefore, the 'Cognitive Flows Framework' mathematically epitomizes a
Symmetric Monoidal Category $(\\mathcal{C}, \\otimes, I)$ - with
$\\mathcal{C}$ as category, $\\otimes$ as tensor product (binary operation
allowing composition), and $I$ as the identity object - where each object,
morphism, natural transformation aligns with a corresponding component,
transformation, reversible transformations or properties of the cognitive
framework. The detailed mechanics of these operations can be abbreviated
according to additional characteristics.
Sure, we can view cognitive flows as organized into a **Symmetric Monoidal
Category**. This is a category endowed with an **associative bifunctor**
which is referred to as **"tensoring"**, and an **identity object**, having
particular isomorphisms (which obey certain axioms) that make the category
"symmetric".
Formally, a Symmetric Monoidal Category consists of:
- A category \\( \\mathcal{C} \\)
- A bifunctor \\( \\otimes: \\mathcal{C} \\times\\mathcal{C} \\rightarrow
\\mathcal{C} \\)
- An object I (called the identity or unit)
- Natural isomorphisms:
- **Associator**: \\(a\_{A,B,C}: (A \\otimes B) \\otimes C \\rightarrow A
\\otimes (B \\otimes C) \\)
- **Left & Right Unitor**: \\(l_A: I \\otimes A \\rightarrow A\\) and
\\(r_A: A \\otimes I \\rightarrow A\\)
- **Swapper or Symmetry**: \\(s\_{A,B}: A \\otimes B \\rightarrow B \\otimes
A \\)
These data should satisfy several coherence laws relating to associativity,
identity, and symmetry.
Now, let's connect these symbols with the cognitive flow:
- **Objects** (A, B, C): These represent the states in our cognitive flow, for
instance, specific cognitive tasks, mental representations or brain states.
- **Morphisms** (f, g, h): These signify transitions between different states.
For example, a cognitive process switching from task A to B would denote a
morphism from A to B.- **Tensor Product (\\otimes)**: This allows us to consider multiple systems
or cognitive processes simultaneously. For instance, if we are considering
cognitive task A and B concurrently, we can denote that as A \\otimes B.
- **Associator (a)**: This captures the concept that no matter in which order
we consider tasks, the end result is the same. For example, if we have tasks
A, B, C, undertaking tasks A and B first and then C is the same as doing task
A first and then tasks B and C.
- **Unitors (l, r)**: Capture the idea that the unit doesn't affect the
cognitive state. For example, a cognitive state, coupled with an identity
process, simply gives back the cognitive state.
- **Swapper/symmetry (s)**: Captures the interchangeability of certain
cognitive operations. For instance, if we have operations A and B, switching
from A to B is the same as switching from B to A.
With these associations, we can build a rich vocabulary to understand and
predict cognitive flow transitions. We might even start specifying equations
or transition rules following these operations, leading to a
mathematically-described cognitive science.
# Worked example
The discussed visualization methods correspond in abstract terms to elements
of a symmetric monoidal category. We may describe the relationship as follows:
1\. **Gradient Flows**: This maps to an induced set of **morphisms** in a
symmetric monoidal category. Each morphism represents a potential
transformation or operation, i.e., 'flow'.
2\. **Buffer Zones and Trampolines**: This introduces **natural
isomorphisms**, which can be understood as transformations that occur under
certain conditions.
3\. **Color-Coded and Transformable Links**: This introduces a improvement to
our model that can be seen as an extension of **morphisms**, but with an
additional attribute or parameter such as color or thickness.
4\. **Halo, Shadow, or Glow Effects**: These signify additional parameters or
**properties** of the operations or morphisms. You could think of them as
presenting 'modules' for the morphisms.
5\. **Animations**: These can be seen as the **composition of morphisms** over
time, resulting in observable temporal changes.
6\. **Auditory or Unanticipated Visual Cues**: These function as **special
cases or exceptions** within our morphisms.
Mathematically, the structures we discuss take place in an environment such as
**C**, where **C** is a category with the symmetric monoidal structure.
Objects in **C** could correspond to different elements in our visualization
(e.g., specific features, decision points, events, etc.), while morphisms
could represent the actions or transformations connecting these entities.A way to formally portray the *Gradient Flows* (as an example) could be the
morphism **f: A ⊗ B → C ⊗ D**. In this mapping, A and B are the initial
points (or states) of a 'decision' or 'action', and C and D are the resulting
points (or states). The morphism **f** corresponds to the transformation or
operation applied, representing the 'gradient flow' from **A ⊗ B** to **C ⊗
D**.
Conceptually, this framework from category theory can be valuable in providing
an abstract model, capable of characterizing complex interactions and
transformations within systems, while also concisely capturing nuances."""
    messages.append({"role": "system", "content": system_prompt})

    while not end_chat:
        try:
            if not skip_input:
                try:
                    user_input = prompt(
                        HTML(f"<{color}>termGPT> </{color}>"),
                        # multiline=True,
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
                if args.syntax:
                    assistant_response = get_response(messages, args.model)
                    print(f"\n{format_output(assistant_response)}\n")
                else:
                    print()
                    assistant_response = stream_chat_completion(messages, args.model)
                    print('\n')
            except KeyboardInterrupt:
                print()
                continue

            messages.append({"role": "assistant", "content": assistant_response})

        except:
            traceback.print_exc()
            end_chat = True

if __name__ == '__main__':
    main()
