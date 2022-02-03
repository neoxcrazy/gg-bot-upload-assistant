import os
import sys
import json
import logging
from pprint import pformat
from rich.console import Console
from rich.prompt import Prompt, Confirm

console = Console()
working_folder = os.path.dirname(os.path.realpath(__file__))
logging.basicConfig(filename=f'{working_folder}/upload_script.log', level=logging.INFO, format='%(asctime)s | %(name)s | %(levelname)s | %(message)s')

def collect_custom_messages_from_user(debug):
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)

    logging.debug(f"[CustomInputs] Starting to collect custom messages from user for torrent description")
    
    is_first = True
    user_custom_texts = []

    custom_text_components = json.load(open(f'{working_folder}/parameters/custom_text_components.json'))
    # creating a list of keys [for warning message]
    components_choices = ", ".join(map(lambda component: f'\'{component["key"]}\'', custom_text_components))
    logging.debug(f'[CustomInputs] keys configured in the bot :: {components_choices}')
    # replacing the last , with or.
    # TODO is there any better approach to do this in python??
    components_choices = components_choices[::-1].replace(" ,", " ro ", 1)[::-1]
    
    # adding I'm and idiot to the components list :p
    logging.debug(f'[CustomInputs] Adding IDIOT key to the text components')
    custom_text_components.append({
        "key" : "IDIOT",
        "display_name": "I'm and idiot",
        "tracker_reference_key" : "",
        "title" : "false"
    })
    
    # creating the choices list for user
    list_of_num = []
    for i in range(len(custom_text_components)):
        i += 1
        list_of_num.append(str(i))

    console.rule(f"[bold red on white] :warning: Custom Torrent Descriptions! :warning: [/bold red on white]", style='bold red', align='center')
    console.print(f"You can add custom messages and texts to the torrent description as various text components. These could be {components_choices}", justify='center')
    console.print(f"[bold red]:warning: Please note that only few trackers supports all these different types. :warning:[/bold red]", highlight=False, justify='center')
    console.print(f"If any tracker does not support one of the type, then it will be defaulted to 'PLAIN TEXT'", justify='center')
    console.print(f"[bold red]:warning: The text components added will be added to torrent description in the order which they are entered :warning:[/bold red]", justify='center')

    while True:
        # starting a loop to accept multiple components from user
        # displaying the list of components available
        for index, component in enumerate(custom_text_components):
            console.print(f'{index + 1}. {component["display_name"]}')
        
        choice = Prompt.ask("Choose which type of content to add:", choices=list_of_num, default="1")
        
        if choice == str(len(custom_text_components)): # the last component is always the hardcoded IDIOT key
            console.print(f"[bold blue]:facepunch: Yes... Yes you are.:facepunch: [/bold blue] [bold red]Skipping custom torrent descriptions and proceeding with upload[/bold red] :angry_face: ", justify='center')
            break
        else:
            title = None
            if custom_text_components[int(choice) - 1]["title"]:
                console.print(f"Please provide the title for the component ([bold green]One Liner[/bold green])")
                title = input("::").split("\\n")[0]
                logging.debug(f'User provided {title} as title for {custom_text_components[int(choice) - 1]["key"]}')

            console.print(f"Please provide the contents for '{custom_text_components[int(choice) - 1]['key']}'. [bold red on white] Send EOF or Ctrl + D to stop text grabbing [/bold red on white]")
            custom_text = sys.stdin.read()
            console.print(f"[green] ----------------- USER INPUT COLLECTED ----------------- [/green]")
            console.print(custom_text)
            console.print(f"[green] ---------------------------------------------------------- \n\n[/green]")
            # adding the user provided custom text to the return list
            # the data is added as an object with `key` : `tracker_reference_key` and `value` : `user input`
            user_custom_texts.append(
                { 
                    "key" : custom_text_components[int(choice) - 1]['tracker_reference_key'], 
                    "value" : custom_text,
                    "title" : title
                }
            )
            if not Confirm.ask("Do you want to add more custom texts?", default="n"):
                break
    logging.debug(f'Custom text components collected :: {pformat(user_custom_texts)}')
    console.print("\n")
    return user_custom_texts