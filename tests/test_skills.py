"""Rules of the brief on the skills and manifests, checked by a machine."""

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins/mirepoix"
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
    assert {"harness-setup", "simplification-pass"} <= {skill.parent.name for skill in SKILLS}


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


def test_simplifier_agent_is_read_only():
    """
    Given the simplifier agent
    When its frontmatter is read
    Then its tools can read but not change anything
    """
    text = read(PLUGIN / "agents/simplifier.md")
    assert re.search(r"^tools: Read, Grep, Glob$", text, re.MULTILINE)
