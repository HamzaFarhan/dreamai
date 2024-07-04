from time import sleep
from typing import Any

from fastcore.utils import nested_idx
from termcolor import colored

from .auth import API_SCOPES, create_service

API_NAME = "slides"
API_VERSION = "v1"
PLACEHOLDER_TYPE = "BODY"
PLACEHOLDER_KEY = "pageElements"
BULLET_PRESET = "BULLET_DISC_CIRCLE_SQUARE"


def presentation_slides(service: Any, presentation_id: str) -> list[dict]:
    return (
        service.presentations()
        .get(presentationId=presentation_id)
        .execute()
        .get("slides", [])
    )


def find_placeholder_in_slide(
    slide: dict,
    placeholder_type: str = PLACEHOLDER_TYPE,
    keys: list[str] = [PLACEHOLDER_KEY],
) -> str:
    # page_elements = slide.get("pageElements")
    body_placeholder = ""
    page_elements = nested_idx(slide, *keys)
    if page_elements is None:
        return body_placeholder
    for pe in page_elements:
        if (
            pe.get("shape")
            and pe.get("shape").get("placeholder")
            and pe.get("shape").get("placeholder").get("type") == placeholder_type
        ):
            body_placeholder = pe.get("objectId")
            break

    return body_placeholder


def insert_text_request(object_id: str, text: str, insertion_index: int = 0) -> dict:
    return {
        "insertText": {
            "objectId": object_id,
            "insertionIndex": insertion_index,
            "text": text,
        }
    }


def create_bullet_request(
    object_id: str, text: str, bullet_preset: str = BULLET_PRESET
) -> dict:
    return {
        "createParagraphBullets": {
            "objectId": object_id,
            "textRange": {
                "type": "FIXED_RANGE",
                "startIndex": 0,
                "endIndex": len(
                    text
                ),  # Adjust end index to include the entire text for bullet
            },
            "bulletPreset": bullet_preset,  # Define the style of bullets you want to use
        }
    }


def add_text_to_slide(
    service: Any,
    presentation_id: str,
    text: str | list[str | list[str]] = ["HELLO", "DREAMAI"],
    placeholder_type: str | list[str] = ["TITLE", "BODY"],
    slide: dict | None = None,
    slide_id: int = -1,
) -> dict:
    assert slide or slide_id is not None, "No slide or slide_id provided."
    if not isinstance(text, list):
        text = [text]
    if not isinstance(placeholder_type, list):
        placeholder_type = [placeholder_type]
    slide = (
        slide
        or presentation_slides(presentation_id=presentation_id, service=service)[
            slide_id
        ]
    )
    batch_update_requests = []
    for text_content, ph_type in zip(text, placeholder_type):
        if ph_type == "NOTES":
            slide_keys = ["slideProperties", "notesPage", "pageElements"]
            ph_type = "BODY"
        else:
            slide_keys = ["pageElements"]
        placeholder = find_placeholder_in_slide(
            slide=slide, placeholder_type=ph_type, keys=slide_keys
        )
        if placeholder:
            # print(f"Found placeholder: {placeholder}")
            # print(f"Adding text: {text_content}")
            if ph_type in ["BODY", "NOTES"]:
                if not isinstance(text_content, list):
                    batch_update_requests.append(
                        insert_text_request(object_id=placeholder, text=text_content)
                    )
                    continue
                bullets = "\n".join(text_content)
                insertion_index = 0
                batch_update_requests.append(
                    insert_text_request(
                        object_id=placeholder,
                        text=bullets,
                        insertion_index=insertion_index,
                    )
                )
                bullet_request = create_bullet_request(
                    placeholder, "".join(text_content)
                )
                batch_update_requests.append(bullet_request)
            elif isinstance(text_content, str):
                batch_update_requests.append(
                    insert_text_request(object_id=placeholder, text=text_content)
                )
    # print(batch_update_requests)
    request_body = {"requests": batch_update_requests}
    return (
        service.presentations()
        .batchUpdate(presentationId=presentation_id, body=request_body)
        .execute()
    )


def create_presentation(
    service: Any | None = None,
    token_file: str = "",
    client_secrets_file: str = "",
    api_name: str = API_NAME,
    api_version: str = API_VERSION,
    scopes: list = API_SCOPES,
    name: str = "DREAMAI PRESENTATION",
    title: str = "DREAMAI",
    subtitle: str = "",
) -> str:
    assert (
        service is not None or token_file or client_secrets_file
    ), "No service or credentials provided."
    service = service or create_service(
        api_name=api_name,
        api_version=api_version,
        token_file=token_file,
        client_secrets_file=client_secrets_file,
        scopes=scopes,
    )
    body = {"title": name}
    presentation = service.presentations().create(body=body).execute()  # type: ignore
    presentation_id = presentation.get("presentationId")
    sleep(1)
    _ = add_text_to_slide(
        service=service,
        presentation_id=presentation_id,
        text=[title, subtitle],
        placeholder_type=["CENTERED_TITLE", "SUBTITLE"],
        slide_id=0,
    )
    print(colored(f"Created presentation with ID:{presentation_id}", "green"))
    return presentation_id


def add_slide(
    service: Any,
    presentation_id: str,
    title_text: str = "DREAMAI",
    body_text: str | list[str] = [
        "Generative AI",
        "Computer Vision",
        "Natural Language Processing",
    ],
    notes_text: str = "slide notes",
) -> dict:
    slides = presentation_slides(service=service, presentation_id=presentation_id)
    next_slide_id = max(1, len(slides))
    batch_update_requests = [
        {
            "createSlide": {
                "objectId": f"slide_{next_slide_id}",
                "insertionIndex": next_slide_id,
                "slideLayoutReference": {"predefinedLayout": "TITLE_AND_BODY"},
            }
        }
    ]
    body = {"requests": batch_update_requests}
    _ = (
        service.presentations()
        .batchUpdate(presentationId=presentation_id, body=body)
        .execute()
    )

    sleep(1)

    return add_text_to_slide(
        service=service,
        presentation_id=presentation_id,
        text=[title_text, body_text, notes_text],
        placeholder_type=["TITLE", "BODY", "NOTES"],
        slide_id=next_slide_id,
    )
