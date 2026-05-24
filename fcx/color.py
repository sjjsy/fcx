"""ANSI color helpers — silent no-ops when stdout is not a TTY."""
import sys

_TTY = sys.stdout.isatty()


def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _TTY else text


def green(text: str) -> str:  return _c("32", text)
def red(text: str) -> str:    return _c("31", text)
def yellow(text: str) -> str: return _c("33", text)
def cyan(text: str) -> str:   return _c("36", text)
def dim(text: str) -> str:    return _c("2",  text)
