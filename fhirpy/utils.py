from urllib.parse import urlencode


def encode_params(params):
    return urlencode(params or {}, doseq=True, safe=':,')


def convert_values(data, fn):
    """
    Recursively converts data values with `fn`
    which must return tuple of (converted data, stop flag).
    Conversion will be stopped for this branch if stop flag is True

    >>> convert_values({}, lambda x: (x, False))
    {}

    >>> convert_values([], lambda x: (x, False))
    []

    >>> convert_values('str', lambda x: (x, False))
    'str'

    >>> convert_values(
    ... [{'key1': [1, 2]}, {'key2': [3, 4]}],
    ... lambda x: (x + 1, False) if isinstance(x, int), False else (x, False))
    [{'key1': [2, 3]}, {'key2': [4, 5]}]

    >>> convert_values(
    ... [{'replaceable': True}, {'replaceable': False}],
    ... lambda x: ('replaced', False)
    ...     if isinstance(x, dict) and x.get('replaceable', False)
    ...     else (x, False))
    ['replaced', {'replaceable': False}]
    """

    data, stop = fn(data)

    if stop:
        return data

    if isinstance(data, list):
        return [convert_values(x, fn) for x in data]
    if isinstance(data, dict):
        return {key: convert_values(value, fn)
                for key, value in data.items()}
    return data
