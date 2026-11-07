"""Contract of the git guardrails hook of the Cordeau plugin."""

import ast
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins/cordeau"
SCRIPT = PLUGIN / "skills/harness-setup/scripts/guardrails.py"
HOOKS = PLUGIN / "hooks/hooks.json"
REFUSAL = "Refused by Cordeau:"
STANDARD_MODULES = {"itertools", "json", "os", "re", "shlex", "sys"}

REWRITES_THE_REMOTE = [
    "git push --force",
    "git push -f",
    "git push -f origin main",
    "git push -fu origin main",
    "git push -uf origin main",
    "git push origin main --force",
    "git push --force-with-lease",
    "git push --force-with-lease=main:abc123 origin main",
    "git push --force-if-includes",
    "git push origin +main",
    "git push origin +refs/heads/main:refs/heads/main",
    "git -C . push --force",
    'git -C "a folder" push --force',
    "git --no-pager push -f",
    "git -c user.name=x push -f",
    "git --git-dir=.git push -f",
    "git --git-dir .git push -f",
    "git push \\\n  --force",
    "/usr/bin/git push -f",
    "git.exe push -f",
    '"git" push -f',
    "g\\it push -f",
    "FOO=1 git push -f",
    "env FOO=1 git push -f",
    "command git push -f",
    "sudo git push -f",
    "nohup git push -f &",
    "time git push -f",
    'bash -c "git push -f"',
    "sh -c 'git push -f'",
    'zsh -lc "git push -f"',
    'eval "git push -f"',
    "eval git push -f",
    "echo ok; git push -f",
    "echo ok && git push -f",
    "echo ok || git push -f",
    "echo ok | git push -f",
    "echo ok\ngit push -f",
    "(git push -f)",
    "{ git push -f; }",
    "if true; then git push -f; fi",
    'echo "$(git push -f)"',
    "echo $(git push -f)",
    "echo `git push -f`",
    'echo "`git push -f`"',
    "cat <<EOF && git push -f\nbody\nEOF",
    "bash <<EOF\ngit push -f\nEOF",
    "echo don't; git push -f",
    "git push --mirror",
    "git push --delete origin old",
    "git push -d origin old",
    "git push origin :old",
    "git push --prune origin",
    'git push origin $(git branch --show-current) --force',
    'git push origin `git branch --show-current` --force',
    'git push --force origin $(basename $(git branch --show-current))',
    'uv run git push -f',
    'git push > log --force',
    'git push 2>&1 --force',
    'git commit -m "use `git push --force` with care"',
]

LOSES_WORK = [
    "git reset --hard",
    "git reset --hard HEAD~3",
    "git reset HEAD~3 --hard",
    "git reset --ha",
    "git -C . reset --hard",
    "xargs git reset --hard",
    "git checkout -- x",
    "git checkout HEAD -- x",
    "git checkout main -- x",
    "git checkout .",
    "git checkout ./src",
    "git checkout src/",
    "git checkout '*.py'",
    "git checkout app.py",
    "git -C sub checkout nested.py",
    "cd sub && git checkout nested.py",
    "git checkout -f main",
    "git checkout --force main",
    "find . -name x -exec git checkout -- {} \\;",
    "git switch -f main",
    "git switch --force main",
    "git switch --discard-changes main",
    "git restore .",
    "git restore x",
    "git restore --worktree x",
    "git restore --staged --worktree x",
    "git restore -SW x",
    "git clean -f",
    "git clean -fd",
    "git clean -xdf",
    "git clean --force",
    'git reset --h',
    'git reset --merge',
    'git -C $(git rev-parse --show-toplevel) reset --hard',
    'git checkout $(git merge-base HEAD main) -- app.py',
    'git diff --name-only | xargs git checkout --',
    "git fetch origin  # don't rebase yet\ngit reset --hard origin/main  # it's fine",
    'cat <<EOF > notes.md\nThen run `git reset --hard` to clean up.\nEOF',
    'cd "$(git rev-parse --show-toplevel)" && git checkout app.py',
    'git submodule foreach --recursive git reset --hard',
    "git submodule foreach 'git reset --hard'",
    'poetry run git clean -fd',
]

SKIPS_THE_CHECKS = [
    "git commit --no-verify",
    "git commit --no-verify -m x",
    "git commit -n",
    "git commit -nm x",
    "git commit -anm x",
    "git push --no-verify",
    "git merge --no-verify main",
    "SKIP=gitleaks git commit -m x",
    "env SKIP=gitleaks git commit -m x",
    "export SKIP=gitleaks; git commit -m x",
    "SKIP=gitleaks pre-commit run",
    "HUSKY=0 git commit -m x",
    "LEFTHOOK=0 git commit -m x",
    "git -c core.hooksPath=/dev/null commit -m x",
    "git -c CORE.HOOKSPATH=/dev/null commit -m x",
    "git config core.hooksPath /dev/null",
    "git config --global core.hooksPath /dev/null",
    'git config --unset core.hooksPath && git commit -m x',
    'HUSKY_SKIP_HOOKS=1 git commit -m x',
    'uv run git commit --no-verify -m x',
]

ALLOWED = [
    "git status",
    "git log -n 1",
    'git log --grep="reset --hard"',
    'git log -S"--force"',
    "git diff HEAD",
    'git commit -m "fix: restore invoice order"',
    'git commit -m "docs: never run git push --force; ask first"',
    "git commit -m 'git reset --hard is refused'",
    "git commit -m x && git log -n 1",
    'git commit -am "x"',
    "git commit -mnote",
    "git commit --amend --no-edit",
    "git commit -m \"$(cat <<'EOF'\nfix: explain why git push --force is refused\n\nIt's (really) dangerous.\nEOF\n)\"",
    "git push",
    "git push origin main",
    "git push -u origin main",
    "git push -n origin main",
    "git push --dry-run origin main",
    "git push --tags",
    "git push origin :",
    "git push --no-force-with-lease",
    "git fetch -f origin",
    "git tag -f v1",
    "git branch -f topic main",
    "git add -f x",
    "git reset",
    "git reset HEAD x",
    "git reset --soft HEAD~1",
    "git reset --mixed HEAD~1",
    "git checkout main",
    "git checkout -",
    "git checkout -b topic",
    "git checkout -b app.py",
    "git checkout -B topic origin/topic",
    "git checkout main --",
    "git switch main",
    "git switch -c topic",
    "git restore --staged x",
    "git restore -S x",
    "git restore --source=HEAD~1 --staged x",
    "git clean -n",
    "git clean -nd",
    "git clean --dry-run -f",
    "git clean -d",
    "git config user.name x",
    "git config core.hooksPath",
    'echo "git reset --hard"',
    "echo git push -f",
    'grep -r "git push --force" .',
    "python3 -c \"print('git push --force')\"",
    "cat <<EOF > notes.md\ngit push --force\nEOF",
    "cat <<'EOF' > notes.md\ngit push --force\nEOF\ngit status",
    "# git push --force\ngit status",
    "git status # git push --force",
    "SKIP_TESTS=1 make test",
    "SKIP=1 make test",
    "FOO=1 git status",
    "env FOO=1 git status",
    "rm -f x",
    "ls -f",
    "cp -f a b",
    'gh pr create --title "restore the force"',
    "echo unbalanced'",
    "cat > deploy.sh <<'EOF'\ngit push --force origin main\nEOF",
    'git commit -m "title" -m "- add login form"',
    "git commit -m 'docs: explain why `git push --force` is refused'",
    'git commit -m "docs: explain why \\`git push --force\\` is refused"',
    'git push origin main  # not --force',
    'git log -S "--no-verify"',
    'git grep -e --no-verify',
    'git checkout main > /dev/null 2>&1',
    'git checkout main 2>/dev/null',
    'git checkout main > out.log',
    'git switch --detach main',
    'find . -name x -exec echo git checkout -- {} \\;',
    'env echo git push -f',
    'git status $(git rev-parse --show-toplevel)',
    "",
]


@pytest.fixture
def project(tmp_path):
    """A folder that holds real files, since `git checkout app.py` depends on them."""
    (tmp_path / "app.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "out.log").write_text("", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub/nested.py").write_text("y = 2\n", encoding="utf-8")
    return tmp_path


def run_hook(payload, cwd):
    return subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=payload,
        capture_output=True,
        text=True,
        cwd=cwd,
        timeout=30,
    )


def ask_hook(command, cwd):
    return run_hook(json.dumps({"cwd": str(cwd), "tool_name": "Bash", "tool_input": {"command": command}}), cwd)


@pytest.mark.parametrize("command", REWRITES_THE_REMOTE)
def test_rewriting_the_remote_is_refused(command, project):
    """
    Given a command that rewrites or deletes history on the remote, in any of its spellings
    When the hook reads it
    Then it refuses with exit code 2 and says why on stderr
    """
    result = ask_hook(command, project)
    assert result.returncode == 2, result.stderr
    assert REFUSAL in result.stderr
    assert result.stdout == ""


@pytest.mark.parametrize("command", LOSES_WORK)
def test_losing_uncommitted_work_is_refused(command, project):
    """
    Given a command that throws away uncommitted work
    When the hook reads it
    Then it refuses with exit code 2 and says why on stderr
    """
    result = ask_hook(command, project)
    assert result.returncode == 2, result.stderr
    assert REFUSAL in result.stderr


@pytest.mark.parametrize("command", SKIPS_THE_CHECKS)
def test_skipping_the_checks_is_refused(command, project):
    """
    Given a command that skips the project's commit checks
    When the hook reads it
    Then it refuses with exit code 2 and says why on stderr
    """
    result = ask_hook(command, project)
    assert result.returncode == 2, result.stderr
    assert REFUSAL in result.stderr


@pytest.mark.parametrize("command", ALLOWED)
def test_everyday_commands_pass_in_silence(command, project):
    """
    Given a harmless command, even one that only quotes a forbidden command
    When the hook reads it
    Then it lets the normal permissions decide, with exit code 0 and no output
    """
    result = ask_hook(command, project)
    assert result.returncode == 0, result.stderr
    assert result.stdout == ""
    assert result.stderr == ""


def test_a_refusal_tells_the_model_what_the_user_can_do(project):
    """
    Given a refused command
    When the model reads the reason
    Then it knows the user can still run the command in their own terminal
    """
    assert "their own terminal" in ask_hook("git push --force", project).stderr


def test_a_call_without_a_command_passes(project):
    """
    Given a tool call that holds no command
    When the hook reads it
    Then it has nothing to refuse
    """
    assert run_hook(json.dumps({"tool_input": {"file_path": "x"}}), project).returncode == 0


def test_the_command_can_sit_at_the_top_level(project):
    """
    Given a tool that sends `command` at the top level of its JSON
    When the hook reads it
    Then the same rules apply
    """
    assert run_hook(json.dumps({"command": "git push --force"}), project).returncode == 2


def cursor_call(command, cwd):
    return json.dumps({"hook_event_name": "beforeShellExecution", "command": command, "cwd": str(cwd), "sandbox": False})


def test_cursor_gets_an_answer_for_a_command_that_passes(project):
    """
    Given Cursor, which blocks a command when its hook prints no answer
    When the hook reads a harmless command
    Then it answers with a permission that allows it, and exit code 0
    """
    result = run_hook(cursor_call("git status", project), project)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"permission": "allow"}
    assert result.stderr == ""


@pytest.mark.parametrize("command", ["git push --force", "git reset --hard", "git commit --no-verify -m x"])
def test_cursor_gets_the_refusal_and_its_reason(command, project):
    """
    Given Cursor, which reads the reason of a refusal from the JSON answer
    When the hook reads a forbidden command
    Then it denies it in JSON for the user and for the agent, with exit code 2
    """
    result = run_hook(cursor_call(command, project), project)
    assert result.returncode == 2, result.stderr
    answer = json.loads(result.stdout)
    assert answer["permission"] == "deny"
    assert REFUSAL in answer["user_message"]
    assert REFUSAL in answer["agent_message"]


@pytest.mark.parametrize(
    ("command", "exit_code"),
    [("git push --force", 2), ("git reset --hard", 2), ("git status", 0)],
)
def test_grok_build_sends_its_command_in_camel_case(command, exit_code, project):
    """
    Given Grok Build, which names the input of a tool `toolInput`
    When the hook reads its call
    Then the same rules apply, with nothing on stdout
    """
    call = {
        "hookEventName": "pre_tool_use",
        "cwd": str(project),
        "workspaceRoot": str(project),
        "toolName": "run_terminal_command",
        "toolInput": {"command": command},
    }
    result = run_hook(json.dumps(call), project)
    assert result.returncode == exit_code, result.stderr
    assert result.stdout == ""
    assert (REFUSAL in result.stderr) == (exit_code == 2)


def test_unreadable_input_never_looks_like_a_refusal(project):
    """
    Given input that is not JSON
    When the hook fails
    Then its exit code is not 2, so Claude Code shows an error instead of a refusal
    """
    assert run_hook("not json", project).returncode not in (0, 2)


def test_the_script_only_uses_harmless_standard_modules():
    """
    Given a script that runs on the machine of everyone who installs the plugin
    When its imports are listed
    Then they hold no network or subprocess module
    """
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module.split(".")[0])
    assert imported <= STANDARD_MODULES


def test_the_script_stays_short_and_readable():
    """
    Given the brief asks for short, readable scripts
    When its lines are counted
    Then it stays under 150
    """
    assert len(SCRIPT.read_text(encoding="utf-8").splitlines()) < 150


def test_the_script_parses_on_an_old_python():
    """
    Given the Python of a Mac with nothing installed is old
    When the script is parsed with the grammar of Python 3.8
    Then it holds no syntax that would break the guard there
    """
    ast.parse(SCRIPT.read_text(encoding="utf-8"), feature_version=(3, 8))


def test_the_plugin_hook_runs_the_script_on_shell_commands_only():
    """
    Given the hook configuration of the plugin
    When it is read
    Then it filters on the shell tools and starts the script without a shell
    """
    groups = json.loads(HOOKS.read_text(encoding="utf-8"))["hooks"]["PreToolUse"]
    assert len(groups) == 1
    assert set(groups[0]["matcher"].split("|")) == {"Bash", "PowerShell"}
    handler = groups[0]["hooks"][0]
    assert handler["type"] == "command"
    assert handler["command"] == "python3"


def test_the_plugin_hook_names_its_script_from_the_plugin_root_only():
    """
    Given the rules of the plugin directory on hook commands
    When the path of the script is read
    Then it is written in full from the plugin root, with no other variable
    """
    handler = json.loads(HOOKS.read_text(encoding="utf-8"))["hooks"]["PreToolUse"][0]["hooks"][0]
    prefix = "${CLAUDE_PLUGIN_ROOT}/"
    path = handler["args"][0]
    assert path.startswith(prefix)
    assert (PLUGIN / path[len(prefix) :]).resolve() == SCRIPT.resolve()
    assert "$" not in path[len(prefix) :]
