import os

def snake_to_camel(snake_str: str, lower_first: bool = True) -> str:
    """
    Returns a given snake_case string in camelCase (/ CamelCase).

    Arguments:
    snake_str -- string to convert from snake to camel case
    lower_first -- bool to indicate if first character
        should be upper case.
    """

    snake_str = snake_str.lower()

    result = "".join(
        word.capitalize() if i != 0 else word 
        for i, word in enumerate(snake_str.split("_"))
    )
    if not lower_first:
        result = result.capitalize()
    return result


def generate_absolute_path(relative_path: str) -> str:
    """
    Generate an absolute path to a file.

    Arguments:
    relative_path -- path relative to current script. 
    """
    path_to_script = os.path.dirname(os.path.abspath(__file__))
    return path_to_script + "/" + relative_path