"""paramparse.py - Universal parameter parser."""

import re


def parse_parameters(syntax, rewrite_plus_minus):
    """Parse user parameter input, allowing for multi-word values."""
    parameters = re.sub(r":", r"=", syntax)

    if rewrite_plus_minus:
        # Some builders allow for `key+value`, which remaps to `key+=value`.
        # Others, however, do not and instead allow +/- to appear within the
        # values themselves. Thus, we need to be able to enable/disable this
        # replacer behavior.
        parameters = re.sub(r"(\w)\s*([+-])\s*(\w)", r"\g<1>=\g<2>\g<3>", parameters)

    parameters = re.sub(r"\s*([+-])\s*=\s*", r"=\g<1>", parameters) # Allow +=, -=
    parameters = re.sub(r"\s*=\s*([+-])\s*", r"=\g<1>", parameters) # Remove k, v gaps

    params = {}

    pattern = re.compile(r"([A-z]+)=")
    match = pattern.match(parameters)

    while match is not None and parameters:
        key = match.groups(0)[0]
        parameters = parameters[match.span()[1]:]

        # Get the value
        match = pattern.search(parameters)
        if match is None:
            value = parameters
            parameters = ""
        else:
            value = parameters[:match.span()[0]]
            parameters = parameters[match.span()[0]:]

        params[key] = value.strip()
        match = pattern.match(parameters)

    if parameters:
        raise SyntaxError(f"Invalid syntax: `{parameters}`.")

    return params
