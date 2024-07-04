from typing import Any

from termcolor import colored

from .auth import API_SCOPES, create_service

API_NAME = "forms"
API_VERSION = "v1"


def create_quiz(
    service: Any,
    token_file: str = "",
    client_secrets_file: str = "",
    api_name: str = API_NAME,
    api_version: str = API_VERSION,
    scopes: list = API_SCOPES,
    name: str = "DREAMAI QUIZ",
    title: str = "DREAMAI",
) -> dict:
    assert (
        service or token_file or client_secrets_file
    ), "No service or credentials provided."
    service = service or create_service(
        api_name=api_name,
        api_version=api_version,
        token_file=token_file,
        client_secrets_file=client_secrets_file,
        scopes=scopes,
    )
    new_form_request = {"info": {"title": title, "documentTitle": name}}
    update_request_body = {
        "requests": [
            {
                "updateSettings": {
                    "settings": {"quizSettings": {"isQuiz": True}},
                    "updateMask": "quizSettings.isQuiz",
                }
            }
        ]
    }
    form = service.forms().create(body=new_form_request).execute()
    quiz_id = form["formId"]
    _ = service.forms().batchUpdate(formId=quiz_id, body=update_request_body).execute()
    print(colored(f"Created quiz with ID:{quiz_id}", "green"))
    return quiz_id


def create_question_request(
    question: str, answers: list[str], correct_index: int, points_per_question: int = 1
) -> dict:
    return {
        "createItem": {
            "item": {
                "title": question,
                "questionItem": {
                    "question": {
                        "required": True,
                        "grading": {
                            "pointValue": points_per_question,
                            "correctAnswers": {
                                "answers": [{"value": answers[correct_index]}]
                            },
                            "whenRight": {"text": "You got it!"},
                            "whenWrong": {"text": "Sorry, that's wrong"},
                        },
                        "choiceQuestion": {
                            "type": "RADIO",
                            "options": [{"value": answer} for answer in answers],
                        },
                    }
                },
            },
            "location": {"index": 0},
        },
    }


def add_question(
    service: Any,
    quiz_id: str,
    question: str,
    answers: list[str],
    correct_index: int,
    points_per_question: int = 1,
):
    new_question_request = create_question_request(
        question=question,
        answers=answers,
        correct_index=correct_index,
        points_per_question=points_per_question,
    )
    request_body = {"requests": [new_question_request]}
    return service.forms().batchUpdate(formId=quiz_id, body=request_body).execute()
