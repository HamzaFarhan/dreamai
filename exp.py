# %%
from dreamai.ai import ModelName
from dreamai.dialog import Dialog

dialog = Dialog(task="src/dreamai/dialogs/assistant_task.txt")
creator, kwargs = dialog.creator_with_kwargs(
    model=ModelName.GEMINI_FLASH, user="what is the capital of france?"
)

res = creator.create(response_model=str, **kwargs)
print(res)
