import pytest

from pathlib import Path
from pymediainfo import MediaInfo

from utilities.utils_user_input import collect_custom_messages_from_user


working_folder = Path(__file__).resolve().parent.parent.parent


def test_collect_custom_messages_from_user(monkeypatch):
    """
        adding custom user inputs.
        here we'll add all components and vaidate the result.

        Generated User Input Flow:
        1.  bot asks to choose a type:   [user selects PLAIN_TEXT]   [prompt_answers]
        2.  bot asks for input data:     [user provides user INPUT]  [input_answers]
        3.  bot asks to continue or not: [user says YES]             [confirm_answers]
        4.  bot asks to choose a type:   [user selects SPOILER]      [prompt_answers]
        5.  bot asks for the title data: [user gives TITLE data]     [stdin_answers]
        6.  bot asks for input data:     [user provides user INPUT]  [input_answers]
        7.  bot asks to continue or not: [user says YES]             [confirm_answers]
        8.  bot asks to choose a type:   [user selects CODE]         [prompt_answers]
        9.  bot asks for input data:     [user provides user INPUT]  [input_answers]
        10. bot asks to continue or not: [user says YES]             [confirm_answers]
        11. bot asks to choose a type:   [user selects IDIOT]        [prompt_answers]
    """

    prompt_answers = iter(["1", "3", "2", "7"])
    input_answers = iter(["Spoiler Title"])
    stdin_answers = iter(["Plain Text Data", "Spoiler Data", "Code Data"])
    confirm_answers = iter(["y", "y", "y"])

    monkeypatch.setattr('rich.prompt.Prompt.ask', lambda name, choices, default: next(prompt_answers))
    monkeypatch.setattr('builtins.input', lambda name: next(input_answers))
    monkeypatch.setattr('sys.stdin.read', lambda: next(stdin_answers))
    monkeypatch.setattr('rich.prompt.Confirm.ask', lambda name, default: next(confirm_answers))

    expected = [
        {
            "key": "plain_text_code",
            "value": "Plain Text Data",
            "title": None
        },
        {
            "key": "spoiler_code",
            "value": "Spoiler Data",
            "title": "Spoiler Title"
        },
        {
            "key": "code_code",
            "value": "Code Data",
            "title": None
        }
    ]
    assert collect_custom_messages_from_user(f"{working_folder}/tests/resources/custom_input/custom_text_components.json") == expected


def test_collect_custom_messages_from_user_no_idiot(monkeypatch):
    """
        adding custom user inputs.
        here we'll add all components and vaidate the result.

        Generated User Input Flow:
        1. bot asks to choose a type:   [user selects PLAIN_TEXT]   [prompt_answers]
        2. bot asks for input data:     [user provides user INPUT]  [input_answers]
        3. bot asks to continue or not: [user says YES]             [confirm_answers]
        4. bot asks to choose a type:   [user selects SPOILER]      [prompt_answers]
        5. bot asks for the title data: [user gives TITLE data]     [stdin_answers]
        6. bot asks for input data:     [user provides user INPUT]  [input_answers]
        7. bot asks to continue or not: [user says NO]              [confirm_answers]
    """

    prompt_answers = iter(["1", "3"])
    input_answers = iter(["Spoiler Title"])
    stdin_answers = iter(["Plain Text Data", "Spoiler Data"])
    confirm_answers = iter(["y", ""])

    monkeypatch.setattr('rich.prompt.Prompt.ask', lambda name, choices, default: next(prompt_answers))
    monkeypatch.setattr('builtins.input', lambda name: next(input_answers))
    monkeypatch.setattr('sys.stdin.read', lambda: next(stdin_answers))
    monkeypatch.setattr('rich.prompt.Confirm.ask', lambda name, default: next(confirm_answers))

    expected = [
        {
            "key": "plain_text_code",
            "value": "Plain Text Data",
            "title": None
        },
        {
            "key": "spoiler_code",
            "value": "Spoiler Data",
            "title": "Spoiler Title"
        }
    ]
    assert collect_custom_messages_from_user(f"{working_folder}/tests/resources/custom_input/custom_text_components.json") == expected