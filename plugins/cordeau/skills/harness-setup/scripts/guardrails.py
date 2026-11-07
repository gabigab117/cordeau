#!/usr/bin/env python3
"""Refuse destructive git commands and skipped checks before an agent runs them.

PreToolUse hook: reads the tool call as JSON on stdin, exits 2 with the reason on stderr to refuse, exits 0 otherwise to
let the normal permissions decide, and answers Cursor in JSON as well. It reads the text of the command, so it stops
accidents, not an attacker: a script that calls git itself goes through. Standard library only, no network, nothing written.
"""

import itertools, json, os, re, shlex, sys

REMOTE = "this rewrites or deletes history on the remote."
WORK = "this throws away uncommitted work for good."
CHECKS = "this skips the checks of the project."
SEPARATORS = ";&|()\n"
ASSIGNMENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=")
BYPASS = re.compile(r"(SKIP|HUSKY|HUSKY_SKIP_HOOKS|LEFTHOOK)=")
# Quotes and escapes come first, so that a # or an apostrophe inside them is not read as a comment or a quote.
QUOTE_OR_COMMENT = re.compile(r"""'[^']*'|"(?:\\.|[^"\\])*"|\\.|(?<![^\s;&|()])#[^\n]*""", re.DOTALL)
# A heredoc body is not run, unless a shell reads it (`bash <<EOF`, not `cat > a.sh <<EOF`) or it holds a substitution.
HEREDOC = re.compile(r"(?:(?<!sh )|(?<=\.sh ))<<-?[ \t]*\\?(['\"]?)(\w+)\1([^\n]*)\n(?:.*\n)*?[ \t]*\2[ \t]*(?:\n|$)")
SUBSTITUTION = re.compile(r"\$\(([^()]*)\)")
SHELLS = {"bash", "dash", "ksh", "sh", "zsh"}
PROGRAMS = SHELLS | {"echo", "eval", "git", "pre-commit", "printf"}
WRAPPERS = ("! { command do doas elif else env exec find if nice nohup sudo then time timeout until while xargs "
            "pipenv poetry pyenv uv").split()
GIT_OPTIONS_WITH_VALUE = {"-C", "-c", "--attr-source", "--config-env", "--git-dir", "--namespace", "--work-tree"}
RUNS_HOOKS = {"am", "cherry-pick", "commit", "merge", "pull", "push", "rebase", "revert"}


def given(args, *options, letters="", takes_value=""):
    """Tell if an option is given: in full, abbreviated as git accepts, or in a short bundle such as -fu."""
    names = [word.split("=")[0] for word in args if word.startswith("--")]
    if any(name == option or (len(name) > 2 and option.startswith(name)) for name in names for option in options):
        return True
    return bool(letters) and any(re.match(f"-[^- {letters}{takes_value}]*[{letters}]", word) for word in args)


def checkout_loses_work(args, directory):
    """Tell if a checkout overwrites files: forced, with `--`, or naming a path rather than a branch."""
    if given(args, "--force", "--pathspec-from-file", letters="f", takes_value="bB") or "--" in args[:-1]:
        return True
    if set(args) & {"-b", "-B", "--orphan"}:
        return False
    paths = [word for word in args if not word.startswith("-")]
    return any(re.search(r"^[.:~]|/$|[*?[]|\{\}", p) or os.path.exists(os.path.join(directory, p)) for p in paths)


def subcommand_reason(name, args, directory):
    """Apply the rules of one git subcommand."""
    if name in RUNS_HOOKS and given(args, "--no-verify", letters="n" if name == "commit" else "", takes_value="mFcCtSu"):
        return CHECKS
    if name == "config":
        values = [word.lower() for word in args if not word.startswith("-")]
        return CHECKS if "core.hookspath" in values and (len(values) > 1 or "--unset" in args) else None
    if name == "submodule" and "foreach" in args:
        return line_reason("env " + " ".join(args[args.index("foreach") + 1 :]), directory)
    if name == "push":
        refspec = any(word.startswith("+") or (word.startswith(":") and len(word) > 1) for word in args)
        options = ("--force", "--force-with-lease", "--force-if-includes", "--mirror", "--delete", "--prune")
        return REMOTE if refspec or given(args, *options, letters="fd", takes_value="o") else None
    loses_work = {
        "checkout": checkout_loses_work(args, directory),
        "clean": given(args, "--force", letters="f", takes_value="e") and not given(args, "--dry-run", letters="n"),
        "reset": given(args, "--hard", "--merge"),
        "restore": given(args, "--worktree", letters="W") or not given(args, "--staged", letters="S", takes_value="s"),
        "switch": given(args, "--force", "--discard-changes", letters="f", takes_value="cC"),
    }
    return WORK if loses_work.get(name) else None


def git_reason(words, directory):
    """Read the global options of git, then apply the rules of its subcommand."""
    while words and words[0].startswith("-"):
        has_value = words[0] in GIT_OPTIONS_WITH_VALUE
        value = "".join(words[1:2]) if has_value else words[0]
        if "core.hookspath" in value.lower():
            return CHECKS
        if words[0] == "-C" and "$" not in value:
            directory = os.path.join(directory, os.path.expanduser(value))
        words = words[2:] if has_value else words[1:]
    return subcommand_reason(words[0], words[1:], directory) if words else None


def command_reason(words, directory):
    """Tell why one simple command is refused, past its assignments and wrappers such as sudo, or return None."""
    if words[0] == "export" and any(BYPASS.match(word) for word in words[1:]):
        return CHECKS
    names = [os.path.basename(word).replace(".exe", "") for word in words]
    runs = next((index for index, word in enumerate(words) if not ASSIGNMENT.match(word)), len(words))
    if runs < len(words) and names[runs] in WRAPPERS:
        runs = next((index for index in range(runs + 1, len(words)) if names[index] in PROGRAMS), len(words))
    # xargs adds paths to the command, so `xargs git checkout --` restores files.
    program, args = "".join(names[runs : runs + 1]), words[runs + 1 :] + ["./from-xargs"] * ("xargs" in names[:runs])
    if program in ("git", "pre-commit") and any(BYPASS.match(word) for word in words[:runs]):
        return CHECKS
    if program == "git":
        return git_reason(args, directory)
    if program == "eval":
        return line_reason(" ".join(args), directory)
    scripts = [script for option, script in zip(args, args[1:]) if re.fullmatch(r"-[a-zA-Z]*c[a-zA-Z]*", option)]
    return line_reason(scripts[0], directory) if program in SHELLS and scripts else None


def simple_commands(line):
    """Split a command line into simple commands, each a list of words, with what the shell never runs left out."""
    line = re.sub(r"`([^`]*)`", r"$(\1)", line.replace("\\\n", "").replace("\\`", "").replace("\\$(", ""))
    line = HEREDOC.sub(lambda m: m[3] + "".join("\n" + text for text in SUBSTITUTION.findall(m[0]) if not m[1]), line)
    line = QUOTE_OR_COMMENT.sub(lambda m: {"#": "", "'": m[0].replace("$(", "")}.get(m[0][0], m[0]), line)
    line = re.sub(r"\d*[<>]+&?\s*[^\s;&|()<>]+", " ", line)  # a redirection can sit anywhere in a command
    substituted = []  # moved to lines of their own, since the closing parenthesis would end the command
    while SUBSTITUTION.search(line):
        substituted += SUBSTITUTION.findall(line)
        line = SUBSTITUTION.sub("$X", line)
    line = "\n".join([line, *substituted])
    lexer = shlex.shlex(line, posix=True, punctuation_chars=SEPARATORS)
    lexer.whitespace, lexer.whitespace_split, lexer.commenters = " \t\r", True, ""
    try:
        tokens = list(lexer)
    except ValueError:  # an unbalanced quote: read the raw words rather than give up
        tokens = re.findall(r"[;&|()\n]+|[^\s;&|()]+", line)
    return [list(w) for sep, w in itertools.groupby(tokens, lambda t: bool(t) and set(t) <= set(SEPARATORS)) if not sep]


def line_reason(line, directory):
    """Tell why a command line is refused, or return None."""
    for words in simple_commands(line):
        if words[0] == "cd" and len(words) == 2 and "$" not in words[1]:
            directory = os.path.join(directory, os.path.expanduser(words[1]))
        reason = command_reason(words, directory)
        if reason:
            return reason


def main():
    call = json.loads(sys.stdin.buffer.read())
    tool_input = call.get("tool_input") or call.get("toolInput") or {}  # Grok Build writes toolInput
    reason = line_reason(tool_input.get("command") or call.get("command") or "", call.get("cwd") or ".")
    answer = {"permission": "allow"}
    if reason:
        message = f"Refused by Cordeau: {reason} If wanted, the user runs it in their own terminal."
        print(message, file=sys.stderr)
        answer = {"permission": "deny", "user_message": message, "agent_message": message}
    if call.get("hook_event_name") == "beforeShellExecution":  # Cursor blocks the command if its hook prints no answer
        print(json.dumps(answer))
    return 2 if reason else 0


if __name__ == "__main__":
    sys.exit(main())
