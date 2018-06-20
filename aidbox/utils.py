import inflection


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
    if data is None:
        return None

    new = {}
    for key, value in data.items():
        if isinstance(value, dict):
            value = convert_values(value, fn)

        if isinstance(value, list):
            value_list = []

            for item in value:
                if isinstance(item, dict):
                    item = convert_values(item, fn)
                else:
                    item = fn(item)

                value_list.append(item)

            new[key] = value_list
        else:
            new[key] = fn(value)

    return new


def convert_to_underscore(data):
    return convert_keys(data, inflection.underscore)


def convert_to_camelcase(data):
    return convert_keys(data, lambda key: inflection.camelize(key, False))
