import sys
import json
import logging

from pprint import pformat
from rich.console import Console
from rich.prompt import Prompt, Confirm


console = Console()


def _load_components(custom_text_components_path):
    custom_text_components = json.load(open(custom_text_components_path))
    # creating a list of keys [for warning message]
    components_choices = ", ".join(map(lambda component: f'\'{component["key"]}\'', custom_text_components))
    logging.debug(f'[CustomUserInputs] keys configured in the bot :: {components_choices}')
    # replacing the last , with or.
    # TODO is there any better approach to do this in python??
    components_choices = components_choices[::-1].replace(" ,", " ro ", 1)[::-1]

    # adding I'm and idiot to the components list :p
    logging.debug('[CustomUserInputs] Adding IDIOT key to the text components')
    custom_text_components.append({
        "key": "IDIOT",
        "display_name": "I'm and idiot",
        "tracker_reference_key": "",
        "title": "false"
    })
    return custom_text_components, components_choices


def _create_choice_list_for_user(custom_text_components):
    list_of_num = []
    for i in range(len(custom_text_components)):
        i += 1
        list_of_num.append(str(i))
    return list_of_num


def collect_custom_messages_from_user(custom_text_components_path):
    logging.debug("[CustomUserInputs] Starting to collect custom messages from user for torrent description")

    user_custom_texts = []
    custom_text_components, components_choices = _load_components(custom_text_components_path)
    # creating the choices list for user
    list_of_num = _create_choice_list_for_user(custom_text_components)

    console.rule("[bold red on white] :warning: Custom Torrent Descriptions! :warning: [/bold red on white]",style='bold red', align='center')
    console.print(f"You can add custom messages and texts to the torrent description as various text components. These could be {components_choices}", justify='center')
    console.print("[bold red]:warning: Please note that only few trackers supports all these different types. :warning:[/bold red]", highlight=False, justify='center')
    console.print("If any tracker does not support one of the type, then it will be defaulted to 'PLAIN TEXT'", justify='center')
    console.print("[bold red]:warning: The text components added will be added to torrent description in the order which they are entered :warning:[/bold red]", justify='center')

    keep_going_mate = True
    while keep_going_mate == True:
        # starting a loop to accept multiple components from user
        # displaying the list of components available
        for index, component in enumerate(custom_text_components):
            console.print(f'{index + 1}. {component["display_name"]}')

        choice = Prompt.ask("Choose which type of content to add:", choices=list_of_num, default="1")
        # the last component is always the hardcoded IDIOT key
        if choice == str(len(custom_text_components)):
            console.print("[bold blue]:facepunch: Yes... Yes you are.:facepunch: [/bold blue] [bold red]Skipping further custom torrent descriptions collection and proceeding with upload[/bold red] :angry_face: ", justify='center')
            keep_going_mate = False
        else:
            title = None
            if custom_text_components[int(choice) - 1]["title"]:
                console.print("Please provide the title for the component ([bold green]One Liner[/bold green])")
                title = input("::").split("\\n")[0]
                logging.debug(f'[CustomUserInputs] User provided {title} as title for {custom_text_components[int(choice) - 1]["key"]}')

            console.print(f"Please provide the contents for '{custom_text_components[int(choice) - 1]['key']}'. [bold red on white] Send EOF or Ctrl + D from new line to stop text grabbing [/bold red on white]")
            custom_text = sys.stdin.read()
            console.print("[green] ----------------- USER INPUT COLLECTED ----------------- [/green]")
            console.print(custom_text)
            console.print("[green] ---------------------------------------------------------- \n\n[/green]")
            # adding the user provided custom text to the return list
            # the data is added as an object with `key` : `tracker_reference_key` and `value` : `user input`
            user_custom_texts.append(
                {
                    "key": custom_text_components[int(choice) - 1]['tracker_reference_key'],
                    "value": custom_text,
                    "title": title
                }
            )
            if not Confirm.ask("Do you want to add more custom texts?", default="n"):
                logging.debug("[CustomUserInputs] Stopping custom input data collection.")
                keep_going_mate = False

    logging.debug(f'[CustomUserInputs] Custom text components collected :: {pformat(user_custom_texts)}')
    return user_custom_texts
