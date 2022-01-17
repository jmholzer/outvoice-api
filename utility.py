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