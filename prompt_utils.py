import string


def format_prompt(task_description, question, choices):
    # todo implement few shot functionality
    def format_choices_by_letter(choices):
        alphabet_list = list(string.ascii_uppercase[:len(choices)])
        content = "\n".join([f"{letter}: {choice}" for letter, choice in zip(alphabet_list, choices)])
        return content

    formatted_choices = format_choices_by_letter(choices)

    prompt = task_description + '\n' + question + '\n' + formatted_choices
    return prompt
