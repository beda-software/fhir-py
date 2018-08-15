from urllib.parse import urlencode


def encode_params(params):
    return urlencode(params or {}, doseq=True, safe=':,')


def convert_keys(data, fn):
    if data is None:
        return None

    new = {}
    for key, value in data.items():
        if isinstance(value, dict):
            value = convert_keys(value, fn)

        if isinstance(value, list):
            value_list = []

            for item in value:
                if isinstance(item, dict):
                    item = convert_keys(item, fn)

                value_list.append(item)

            new[fn(key)] = value_list
        else:
            new[fn(key)] = value

    return new


def convert_values(data, fn):
    """
    >>> convert_values({}, lambda x: x)
    {}

    >>> convert_values([], lambda x: x)
    []

    >>> convert_values('str', lambda x: x)
    'str'

    >>> convert_values(
    ... [{'key1': [1, 2]}, {'key2': [3, 4]}],
    ... lambda x: x + 1 if isinstance(x, int) else x)
    [{'key1': [2, 3]}, {'key2': [4, 5]}]

    >>> convert_values(
    ... [{'replaceable': True}, {'replaceable': False}],
    ... lambda x: 'replaced'
    ...     if isinstance(x, dict) and x.get('replaceable', False) else x)
    ['replaced', {'replaceable': False}]
    """
    data = fn(data)
    if isinstance(data, list):
        return [convert_values(x, fn) for x in data]
    if isinstance(data, dict):
        return {key: convert_values(value, fn) for key, value in data.items()}
    return data


def select_keys(data, keys):
    """
    >>> select_keys({'key1': 'value1', 'key2': 'value2'}, ['key2'])
    {'key2': 'value2'}
    """
    return {key: value for key, value in data.items() if key in keys}
