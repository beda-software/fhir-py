import re
from urllib.parse import urlencode


def camelize(string, uppercase_first_letter=True):
    """
    Convert strings to CamelCase.

    >>> camelize("device_type")
    "DeviceType"
    >>> camelize("device_type", False)
    "deviceType"
    """
    if uppercase_first_letter:
        return re.sub(r"(?:^|_)(.)", lambda m: m.group(1).upper(), string)
    else:
        return string[0].lower() + camelize(string)[1:]


def underscore(word):
    """
    Make an underscored, lowercase form from the expression in the string.

    >>> underscore("DeviceType")
    "device_type"
    """
    word = re.sub(r"([A-Z]+)([A-Z][a-z])", r'\1_\2', word)
    word = re.sub(r"([a-z\d])([A-Z])", r'\1_\2', word)
    word = word.replace("-", "_")
    return word.lower()


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


def convert_keys_to_underscore(data):
    """
    >>> convert_keys_to_underscore(
    ... {'resourceType': 'Patient',
    ...  'genPr': [{'resourceType': 'Practitioner'}]})
    {'resource_type': 'Patient', 'gen_pr': [{'resource_type': 'Practitioner'}]}
    """
    return convert_keys(data, underscore)


def convert_keys_to_camelcase(data):
    return convert_keys(data, lambda key: camelize(key, False))


def select_keys(data, keys):
    """
    >>> select_keys({'key1': 'value1', 'key2': 'value2'}, ['key2'])
    {'key2': 'value2'}
    """
    return {key: value for key, value in data.items() if key in keys}
