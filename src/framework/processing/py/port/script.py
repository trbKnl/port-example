import port.api.props as props
from port.api.commands import (CommandSystemDonate, CommandUIRender)

import pandas as pd
import zipfile

def process(participant_id: str):
    platform = "Twitter"
    progressbar_percentage = 50

    # Start of the data donation flow
    while True:
        # Ask the participant to submit a file
        file_prompt = generate_file_prompt(platform, "application/zip, text/plain")
        file_prompt_result = yield render_page(platform, file_prompt, progressbar_percentage)

        # If the participant submitted a file: continue
        if file_prompt_result.__type__ == 'PayloadString':

            # Validate the file the participant submitted
            # In general this is wise to do 
            is_data_valid = validate_the_participants_input(file_prompt_result.value)

            # Happy flow:
            # The file the participant submitted is valid
            if is_data_valid == True:
                progressbar_percentage += 50

                # Extract the data you as a researcher are interested in, and put it in a pandas DataFrame
                # Show this data to the participant in a table on screen
                # The participant can now decide to donate
                extracted_data = extract_the_data_you_are_interested_in(file_prompt_result.value)
                consent_prompt = generate_consent_prompt(extracted_data)
                consent_prompt_result = yield render_page(platform, consent_prompt, progressbar_percentage)

                # If the participant wants to donate the data gets donated
                if consent_prompt_result.__type__ == "PayloadJSON":
                    yield donate(f"{participant_id}-{platform}", consent_prompt_result.value)

                break

            # Sad flow:
            # The data was not valid, ask the participant to retry
            if is_data_valid == False:
                retry_prompt = generate_retry_prompt(platform)
                retry_prompt_result = yield render_page(platform, retry_prompt, progressbar_percentage)

                # The participant wants to retry: start from the beginning
                if retry_prompt_result.__type__ == 'PayloadTrue':
                    continue
                # The participant does not want to retry or pressed skip
                else:
                    break

        # The participant did not submit a file and pressed skip
        else:
            break

    yield render_end_page()


def extract_the_data_you_are_interested_in(zip_file: str) -> pd.DataFrame:
    """
    This function extracts the data the researcher is interested in

    In this case we extract from the zipfile:
    * The filesnames
    * The compressed file size
    * The file size

    You could extract anything here
    """
    names = []
    out = pd.DataFrame()

    try:
        file = zipfile.ZipFile(zip_file)
        data = []
        for name in file.namelist():
            names.append(name)
            info = file.getinfo(name)
            data.append((name, info.compress_size, info.file_size))

        out = pd.DataFrame(data, columns=["File name", "Compressed file size", "File size"])

    except Exception as e:
        print(f"Something went wrong: {e}")

    return out


def validate_the_participants_input(zip_file: str) -> bool:
    """
    Check if the participant actually submitted a zipfile
    Returns True if participant submitted a zipfile, otherwise False

    In reality you need to do a lot more validation.
    Some things you could check:
    - Check if the the file(s) are the correct format (json, html, binary, etc.)
    - If the files are in the correct language
    """

    try:
        with zipfile.ZipFile(zip_file) as zf:
            return True
    except zipfile.BadZipFile:
        return False


def render_end_page():
    """
    Renders a thank you page
    """
    page = props.PropsUIPageEnd()
    return CommandUIRender(page)


def render_page(platform: str, body, progress: int):
    """
    Renders the UI components
    """
    header = props.PropsUIHeader(props.Translatable({"en": platform, "nl": platform }))
    footer = props.PropsUIFooter(progress)
    page = props.PropsUIPageDonation(platform, header, body, footer)
    return CommandUIRender(page)


def generate_retry_prompt(platform: str) -> props.PropsUIPromptConfirm:
    text = props.Translatable({
        "en": f"Unfortunately, we cannot process your {platform} file. Continue, if you are sure that you selected the right file. Try again to select a different file.",
        "nl": f"Helaas, kunnen we uw {platform} bestand niet verwerken. Weet u zeker dat u het juiste bestand heeft gekozen? Ga dan verder. Probeer opnieuw als u een ander bestand wilt kiezen."
    })
    ok = props.Translatable({
        "en": "Try again",
        "nl": "Probeer opnieuw"
    })
    cancel = props.Translatable({
        "en": "Continue",
        "nl": "Verder"
    })
    return props.PropsUIPromptConfirm(text, ok, cancel)


def generate_file_prompt(platform, extensions) -> props.PropsUIPromptFileInput:
    description = props.Translatable({
        "en": f"Please follow the download instructions and choose the file that you stored on your device. Click “Skip” at the right bottom, if you do not have a {platform} file. ",
        "nl": f"Volg de download instructies en kies het bestand dat u opgeslagen heeft op uw apparaat. Als u geen {platform} bestand heeft klik dan op “Overslaan” rechts onder."
    })
    return props.PropsUIPromptFileInput(description, extensions)


def generate_consent_prompt(df: pd.DataFrame) -> props.PropsUIPromptConsentForm:
    table_title = props.Translatable({
        "en": "Zip file contents",
        "nl": "Inhoud zip bestand"
    })
    table = props.PropsUIPromptConsentFormTable("zip_contents", table_title, df)
    return props.PropsUIPromptConsentForm([table], [])


def donate(key, json_string):
    return CommandSystemDonate(key, json_string)
