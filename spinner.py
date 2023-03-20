import sys
import time
import threading
import traceback

from functools import wraps

SPINNER_COLOR = "\033[92;1m"
RESET_COLOR = "\033[0m"

def spinner(text=""):
    def actual_decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            spinner_animation = '⢿⣻⣽⣾⣷⣯⣟⡿'

            def show_spinner():
                i = 0
                while not func_done.is_set():
                    curr = spinner_animation[i % len(spinner_animation)]
                    sys.stdout.write(f"\r{text}{SPINNER_COLOR} {curr}{RESET_COLOR} ")
                    sys.stdout.flush()
                    time.sleep(0.1)
                    i += 1

            func_done = threading.Event()
            spinner_thread = threading.Thread(target=show_spinner)
            spinner_thread.start()

            result = None
            exception = None
            try:
                result = func(*args, **kwargs)
            except BaseException as e:
                exception = e
                result = traceback.format_exc()
            finally:
                func_done.set()
                spinner_thread.join()

                sys.stdout.write("\r" + " " * 20 + "\r")  # Clear the spinner line
                sys.stdout.flush()

                if isinstance(exception, KeyboardInterrupt):
                    return "__KEYBOARD_INTERRUPT"

                return result

        return wrapper
    return actual_decorator
