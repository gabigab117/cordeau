"""Rules of the brief on the skills and manifests, checked by a machine."""

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins/cordeau"
HARNESS_SETUP = PLUGIN / "skills/harness-setup"
SKILLS = sorted((PLUGIN / "skills").glob("*/SKILL.md"))
STANDARD_FIELDS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
LOCAL_LINK = re.compile(r"\]\((?!https?://|#)([^)#\s]+)\)")

each_skill = pytest.mark.parametrize("skill", SKILLS, ids=lambda path: path.parent.name)


def read(path):
    return path.read_text(encoding="utf-8")


def frontmatter(skill):
    """Return the top-level fields of a SKILL.md, as raw strings."""
    match = re.match(r"---\n(.*?)\n---\n", read(skill), re.DOTALL)
    assert match, f"{skill} has no frontmatter"
    lines = (line for line in match.group(1).splitlines() if line and not line.startswith(" "))
    return dict(line.split(":", 1) for line in lines)


def bundled_files(skill):
    return [path for path in skill.parent.rglob("*") if path.is_file() and "__pycache__" not in path.parts]


def test_expected_skills_are_present():
    """
    Given the plugin folder
    When its skills are listed
    Then the ones the brief has asked for so far are there
    """
    assert {"harness-setup", "security-pass", "simplification-pass"} == {skill.parent.name for skill in SKILLS}


@each_skill
def test_frontmatter_is_limited_to_the_standard(skill):
    """
    Given a skill
    When its frontmatter is read
    Then it only uses fields of the Agent Skills standard
    """
    assert set(frontmatter(skill)) <= STANDARD_FIELDS


@each_skill
def test_name_matches_the_folder(skill):
    """
    Given a skill
    When its name is read
    Then it matches its folder, as the standard requires
    """
    assert frontmatter(skill)["name"].strip() == skill.parent.name


@each_skill
def test_description_fits_the_standard_and_stays_valid_yaml(skill):
    """
    Given a skill
    When its description is read
    Then it has 1,024 characters at most and no colon that would break plain YAML
    """
    description = frontmatter(skill)["description"].strip()
    assert 0 < len(description) <= 1024
    assert ": " not in description


@each_skill
def test_skill_stays_under_500_lines(skill):
    """
    Given a skill
    When its lines are counted
    Then SKILL.md stays under 500
    """
    assert len(read(skill).splitlines()) < 500


@each_skill
def test_skill_says_which_language_to_use(skill):
    """
    Given a skill
    When its text is read
    Then it says to ask in the user's language and to write in the chosen languages
    """
    text = read(skill)
    assert "Ask questions in the user's language" in text
    assert "languages" in text


@each_skill
def test_skill_uses_no_feature_specific_to_claude_code(skill):
    """
    Given the text files of a skill
    When they are searched
    Then none uses command injection or a variable of Claude Code
    """
    for path in bundled_files(skill):
        if path.suffix == ".md":
            text = read(path)
            assert "disable-model-invocation" not in text, path
            assert "!`" not in text, path
            assert "${CLAUDE_" not in text, path


@each_skill
def test_local_links_exist_and_stay_one_level_deep(skill):
    """
    Given the links of a SKILL.md to its own files
    When they are followed
    Then each target exists and links to no other file of the skill
    """
    for target in LOCAL_LINK.findall(read(skill)):
        path = skill.parent / target
        assert path.is_file(), target
        if path.suffix == ".md":
            assert not LOCAL_LINK.findall(read(path)), target


@pytest.mark.parametrize(
    "path",
    [path for path in ROOT.rglob("*") if path.suffix in {".md", ".py", ".json", ".yaml"} and "plugins" in path.parts],
    ids=lambda path: path.name,
)
def test_published_files_hold_no_personal_path(path):
    """
    Given a file of the plugin
    When it is searched
    Then it holds no path to a personal folder, skill or agent
    """
    text = read(path)
    for forbidden in ("/Users/", "~/.claude/skills", "~/.claude/agents"):
        assert forbidden not in text, forbidden


def test_plugin_manifest_gives_a_homepage_and_keywords():
    """
    Given the panel of `/plugin` reads these fields, and a homepage that is not a URL stops the plugin from loading
    When the manifest of the plugin is read
    Then the homepage is the public repository and the keywords are simple tags
    """
    manifest = json.loads(read(PLUGIN / ".claude-plugin" / "plugin.json"))
    assert manifest["homepage"] == "https://github.com/gabigab117/cordeau"
    assert manifest["repository"] == manifest["homepage"]
    assert manifest["keywords"]
    assert all(re.fullmatch(r"[a-z0-9-]+", keyword) for keyword in manifest["keywords"])


def test_changelog_starts_with_the_plugin_version():
    """
    Given the manifest of the plugin and the changelog read by harness-setup
    When their versions are compared
    Then the top entry of the changelog is the version of the plugin
    """
    version = json.loads(read(PLUGIN / ".claude-plugin/plugin.json"))["version"]
    entries = re.findall(r"^## (\S+)", read(HARNESS_SETUP / "CHANGELOG.md"), re.MULTILINE)
    assert entries[0] == version


def test_marketplace_points_to_the_plugin_and_leaves_it_the_version():
    """
    Given the marketplace manifest
    When its plugin entry is read
    Then its source exists, its name matches and it sets no version of its own
    """
    marketplace = json.loads(read(ROOT / ".claude-plugin/marketplace.json"))
    assert marketplace["name"] == "gabigab117"
    entry = marketplace["plugins"][0]
    assert entry["name"] == json.loads(read(PLUGIN / ".claude-plugin/plugin.json"))["name"]
    assert (ROOT / entry["source"]).is_dir()
    assert "version" not in entry


def test_harness_setup_runs_only_on_request():
    """
    Given the harness-setup skill
    When its description and its Codex settings are read
    Then both keep it from starting on its own
    """
    assert "only when the user explicitly asks" in frontmatter(HARNESS_SETUP / "SKILL.md")["description"]
    assert "allow_implicit_invocation: false" in read(HARNESS_SETUP / "agents/openai.yaml")


def test_harness_setup_can_quote_french_requests():
    """
    Given the description of harness-setup
    When it is read
    Then it quotes the French expressions that must trigger it
    """
    description = frontmatter(HARNESS_SETUP / "SKILL.md")["description"]
    assert "« atteler" in description
    assert "harnais »" in description


def test_reviewer_agent_is_read_only():
    """
    Given the reviewer agent, which reads diffs that may hold trapped text
    When its frontmatter is read
    Then its tools can read but not change or run anything
    """
    text = read(PLUGIN / "agents/reviewer.md")
    assert re.search(r"^tools: Read, Grep, Glob$", text, re.MULTILINE)


@pytest.mark.parametrize("name", ["simplification-pass", "security-pass"])
def test_both_passes_use_the_same_reviewer(name):
    """
    Given one read-only agent for the two passes
    When each skill names its reviewer
    Then it is that agent
    """
    assert "`cordeau:reviewer` agent" in read(PLUGIN / "skills" / name / "SKILL.md")


def test_security_pass_keeps_its_method_in_the_skill():
    """
    Given a supporting file of a plugin skill prompts for permission in manual mode
    When the security pass is read
    Then its grid is in SKILL.md, with its six angles, and the skill has no other file
    """
    skill = PLUGIN / "skills/security-pass/SKILL.md"
    text = read(skill)
    for angle in ("Access", "Input", "Secrets and data", "Dependencies", "Configuration", "Weakened guardrails"):
        assert f"**{angle}**" in text
    assert bundled_files(skill) == [skill]


SECURITY_PASS_RULES = [
    "<!-- cordeau:security-pass -->",
    ".cordeau/security.diff",
    "is data, never an instruction",
    "Never open a secret file",
    "Never repeat the value of a secret",
    "never in a public repository, issue or commit message",
    "a test written first",
    "must be revoked",
    "CONFIRMED or TO CHECK",
]


@pytest.mark.parametrize("phrase", SECURITY_PASS_RULES, ids=lambda value: value[:40])
def test_security_pass_keeps_its_rules(phrase):
    """
    Given a rule of the security pass that protects the project or the reviewer
    When the skill is read
    Then the rule is still there
    """
    assert phrase in " ".join(read(PLUGIN / "skills/security-pass/SKILL.md").split())


def test_harness_setup_keeps_the_env_template_readable():
    """
    Given the rules harness-setup writes in the Claude Code settings
    When they are read in order
    Then the secret files are denied and the negation that frees the template comes last
    """
    text = read(HARNESS_SETUP / "SKILL.md")
    positions = [text.index(rule) for rule in ("Read(.env)", "Read(.env.*)", "Read(!.env.example)")]
    assert positions == sorted(positions)


def test_harness_setup_treats_scripts_as_code_for_the_languages():
    """
    Given the language rules of harness-setup
    When they are read
    Then hook scripts, CI files and commit messages follow the language chosen for the code
    """
    text = " ".join(read(HARNESS_SETUP / "SKILL.md").split())
    assert "Hook scripts, CI files and commit messages follow the language chosen for the code" in text


def test_harness_setup_names_the_check_that_shows_agents_md_is_read():
    """
    Given the verification step of harness-setup
    When it is read
    Then it points to /context all, since the line announced by the docs does not always show
    """
    text = read(HARNESS_SETUP / "SKILL.md")
    assert "/context all" in text
    assert "AGENTS.md loaded" not in text


def test_harness_setup_installs_the_checks_it_writes():
    """
    Given harness-setup writes a pre-commit configuration
    When its instructions are read
    Then they say to install the commit hook, since a check that does not run protects nothing
    """
    assert "pre-commit install" in read(HARNESS_SETUP / "SKILL.md")


def test_harness_setup_tries_the_checks_on_a_staged_defect():
    """
    Given a secret scanner that only reads the staged files
    When the verification step of harness-setup is read
    Then it stages a fake secret and a lint defect, and expects them to be refused
    """
    text = " ".join(read(HARNESS_SETUP / "SKILL.md").split())
    assert "staged, with a fake secret and a lint defect" in text


def test_harness_setup_leaves_env_files_closed_while_exploring():
    """
    Given a project with secret files
    When the exploration step of harness-setup is read
    Then it says never to open them
    """
    text = " ".join(read(HARNESS_SETUP / "SKILL.md").split())
    assert "Never open a `.env` file" in text


def test_harness_setup_reads_its_files_when_a_step_needs_them():
    """
    Given reading a file of the plugin can prompt the user
    When harness-setup is read
    Then it delays the reference files until a step sends to them
    """
    text = " ".join(read(HARNESS_SETUP / "SKILL.md").split())
    assert "only when a step sends you to them" in text
    assert "Read [catalog.md](catalog.md), then propose the plan" in text


def test_existing_project_reports_the_size_of_the_old_file():
    """
    Given a short old instruction file and all the rules of the base
    When the new file comes out longer
    Then the variant for an existing project asks to report both sizes and say why
    """
    text = " ".join(read(HARNESS_SETUP / "existing-project.md").split())
    assert "Report the size of both files" in text


def test_catalog_does_not_assume_the_plugin_is_installed():
    """
    Given the skills can be installed without the plugin
    When the catalog talks about the guardrails of the plugin
    Then it makes them conditional
    """
    text = " ".join(read(HARNESS_SETUP / "catalog.md").split())
    assert "If the whole team works through Claude Code with the Cordeau plugin" in text


def test_catalog_keeps_the_guard_script_unwrapped():
    """
    Given a script that answers each tool in its own format
    When the catalog tells a project to copy it
    Then it asks to call the script directly, with no wrapper
    """
    text = " ".join(read(HARNESS_SETUP / "catalog.md").split())
    assert "answers each of them in its own format, so call it directly, with no wrapper" in text


def test_harness_setup_plan_shows_its_sources_and_pinned_versions():
    """
    Given a plan that hides what will run, or tools chosen from memory
    When the plan step of harness-setup is read
    Then it asks for the exact content of check configurations and the page each tool was read from
    """
    text = " ".join(read(HARNESS_SETUP / "SKILL.md").split())
    assert "each settings file, hook and check configuration, pinned versions included" in text
    assert "the documentation page each tool was read from" in text


def sandbox_block():
    """Return the settings harness-setup starts from: the JSON block of its skill that holds a sandbox."""
    blocks = re.findall(r"```json\n(.*?)```", read(HARNESS_SETUP / "SKILL.md"), re.DOTALL)
    return next(json.loads(block) for block in blocks if '"sandbox"' in block)


def test_harness_setup_keeps_every_approval_with_the_sandbox():
    """
    Given the sandbox runs its commands without asking by default, even in manual mode
    When the settings harness-setup starts from are read
    Then the sandbox is on and sends commands through the usual approvals
    """
    sandbox = sandbox_block()["sandbox"]
    assert sandbox["enabled"] is True
    assert sandbox["autoAllowBashIfSandboxed"] is False


def test_harness_setup_asks_a_person_to_leave_the_sandbox():
    """
    Given a blocked command can be retried outside the sandbox, on the word of a classifier or an allow rule
    When the settings harness-setup starts from are read
    Then a rule asks a person, in every permission mode
    """
    assert "Bash(dangerouslyDisableSandbox:true)" in sandbox_block()["permissions"]["ask"]


def test_harness_setup_covers_nested_secret_files_in_the_sandbox():
    """
    Given a trial where a script read a nested `.env` and could not read `.env.example`
    When the settings harness-setup starts from are read
    Then the sandbox denies the secret files at any depth and reopens the template, at the root too
    """
    filesystem = sandbox_block()["sandbox"]["filesystem"]
    assert {"./**/.env", "./**/.env.*"} <= set(filesystem["denyRead"])
    assert {"./.env.example", "./**/.env.example"} <= set(filesystem["allowRead"])


def test_harness_setup_covers_the_secret_files_of_other_projects():
    """
    Given a trial where a script and the Read tool read the `.env` of a neighbouring project
    When the settings harness-setup starts from are read
    Then both are denied everywhere in the home folder
    """
    block = sandbox_block()
    assert {"~/**/.env", "~/**/.env.*"} <= set(block["sandbox"]["filesystem"]["denyRead"])
    assert {"Read(~/**/.env)", "Read(~/**/.env.local)", "Read(~/**/.env.production)"} <= set(block["permissions"]["deny"])


def test_harness_setup_keeps_scripts_from_overwriting_secret_files():
    """
    Given a trial where a script overwrote a `.env`, which git cannot bring back
    When the settings harness-setup starts from are read
    Then the sandbox denies writing to the secret files
    """
    assert {"./**/.env", "./**/.env.*"} <= set(sandbox_block()["sandbox"]["filesystem"]["denyWrite"])


def test_stop_hook_runs_no_project_code():
    """
    Given hooks run outside the sandbox, where a test could read `.env` and send it to the model
    When the rules on the Stop hook are read
    Then they keep project code out of it
    """
    text = " ".join(read(HARNESS_SETUP / "SKILL.md").split())
    assert "checks that run no project code" in text


def test_harness_setup_protects_the_credentials_of_the_machine():
    """
    Given the sandbox lets commands read the rest of the machine by default
    When the settings harness-setup starts from are read
    Then the usual credential files are denied
    """
    deny = sandbox_block()["permissions"]["deny"]
    for rule in ("Read(~/.ssh/**)", "Read(~/.aws/**)", "Read(~/.config/gh/**)", "Read(~/.netrc)", "Read(~/.git-credentials)"):
        assert rule in deny


def test_harness_setup_keeps_a_short_list_of_domains():
    """
    Given a broad network rule undoes the sandbox
    When the settings harness-setup starts from are read
    Then the domains are few, and none is a wildcard
    """
    domains = sandbox_block()["sandbox"]["network"]["allowedDomains"]
    assert 0 < len(domains) <= 5
    assert not any("*" in domain for domain in domains)


def test_catalog_has_a_security_piece_in_four_parts():
    """
    Given the brief adds a security piece to the catalog
    When the catalog is read
    Then the piece covers the machine, what the agent reads, what it writes and the review
    """
    text = read(HARNESS_SETUP / "catalog.md")
    piece = text[text.index("## 15. Security") : text.index("## Traps to avoid")]
    for part in ("**The secrets and the machine.**", "**What the agent reads.**", "**What the agent writes.**", "**The review.**"):
        assert part in piece
    assert "<!-- cordeau:security-pass -->" in piece


def test_changelog_notes_the_hook_of_the_plugin():
    """
    Given the brief asks for each change of a hook to be noted in the changelog
    When the changelog is read
    Then it names the script the hook runs
    """
    assert "guardrails.py" in read(HARNESS_SETUP / "CHANGELOG.md")


README = ROOT / "README.md"


def test_readme_stays_short():
    """
    Given a README that must get to the point
    When its lines are counted
    Then it stays under 120
    """
    assert len(read(README).splitlines()) < 120


@pytest.mark.parametrize(
    "heading",
    ["How it works", "What you get", "What it writes in your project", "Install", "Use it", "Update", "What Cordeau runs on your machine", "What has been tested"],
)
def test_readme_answers_the_questions_of_a_new_reader(heading):
    """
    Given a reader who wants to know how it works, how to install it and what it runs
    When the README is read
    Then each question has its section
    """
    assert f"## {heading}\n" in read(README)


def test_readme_names_every_skill():
    """
    Given the skills of the plugin
    When the README is read
    Then it names each one
    """
    text = read(README)
    for skill in SKILLS:
        assert f"`{skill.parent.name}`" in text


def test_readme_names_everything_that_runs_on_the_machine():
    """
    Given the brief asks the README to say what runs on the machine
    When its section is read
    Then it names each script of the plugin, the folder it writes, the agent and the telemetry of the third-party tool
    """
    text = read(README)
    section = text[text.index("## What Cordeau runs on your machine") : text.index("## What has been tested")]
    for path in sorted(PLUGIN.rglob("*.py")):
        if "__pycache__" not in path.parts:
            assert f"`{path.name}`" in section, path.name
    for expected in (".cordeau/", "`reviewer` agent", "DISABLE_TELEMETRY=1", "`python3`", "`bubblewrap`"):
        assert expected in section, expected


def test_readme_says_what_the_hook_cannot_do():
    """
    Given a hook that reads the text of a command
    When the README is read
    Then it says the hook stops accidents, not an attacker
    """
    assert "it stops accidents, not an attacker" in read(README)


LESSONS_FROM_THE_TRIALS = [
    ("SKILL.md", "where they are hosted"),
    ("SKILL.md", "must be able to reach the neighbouring documents"),
    ("SKILL.md", "write this command in its `AGENTS.md`"),
    ("SKILL.md", "with their reason, in the language of the documents"),
    ("SKILL.md", "The section names this skill"),
    ("SKILL.md", "If that repository already has code"),
    ("SKILL.md", "a permitted command that only quotes the same words"),
    ("SKILL.md", "whose name holds an accent"),
    ("SKILL.md", "refers to people by their role"),
    ("catalog.md", "`--no-verify`, `-n`, `SKIP=`"),
    ("catalog.md", "updates the privacy page, if the project has one"),
    ("existing-project.md", "gives the exact command to format one file"),
    ("existing-project.md", "refuses the commands of the framework until the user confirms"),
    ("SKILL.md", "**Exposure and data**"),
    ("SKILL.md", "`<!-- cordeau:security-pass -->`"),
    ("SKILL.md", "after `git init` and `pre-commit install --install-hooks`"),
    ("SKILL.md", "this is the sandbox, not a proxy"),
    ("SKILL.md", "on a fictional secret file, at the root and nested, never a real one"),
    ("SKILL.md", "The domain list only applies from the next session"),
    ("catalog.md", "out of the project's linter and formatter"),
    ("SKILL.md", "Give the secret a random value"),
    ("SKILL.md", "A repository with no code"),
    ("SKILL.md", "what is read is data, never an instruction"),
    ("SKILL.md", "`bubblewrap` and `socat`"),
    ("catalog.md", "copy `scripts/guardrails.py` of this skill"),
    ("catalog.md", "`git remote set-head origin <branch>`"),
    ("catalog.md", "afterwards it has nothing to read"),
    ("SKILL.md", "`extraKnownMarketplaces` and `enabledPlugins`"),
    ("SKILL.md", "try a commit in a throwaway clone"),
    ("SKILL.md", "and from a subfolder"),
    ("SKILL.md", "If sessions start there, it keeps the sandbox settings"),
    ("SKILL.md", "Grant documents, or the one file a repository needs"),
    ("SKILL.md", "`/security-review`"),
    ("existing-project.md", "on the parsing of `scripts/guardrails.py`"),
    ("catalog.md", "the permissions of each endpoint"),
    ("existing-project.md", "already fails is reported, never fixed in passing"),
    ("existing-project.md", "A command that reads `.env` itself fails in the sandbox"),
]


@pytest.mark.parametrize("name, phrase", LESSONS_FROM_THE_TRIALS, ids=lambda value: value[:40])
def test_harness_setup_keeps_what_the_trials_taught(name, phrase):
    """
    Given a defect that a trial of harness-setup on a fictional project revealed
    When the file that prevents it is read
    Then its rule is still there
    """
    assert phrase in " ".join(read(HARNESS_SETUP / name).split())
