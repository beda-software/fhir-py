import inflection


def convert_to_underscore(data):
    new = {}
    for key, value in data.items():
        if isinstance(value, dict):
            value = convert_to_underscore(value)

        if isinstance(value, list):
            value_list = []

            for item in value:
                if isinstance(item, dict):
                    item = convert_to_underscore(item)

                value_list.append(item)

            new[inflection.underscore(key)] = value_list
        else:
            new[inflection.underscore(key)] = value

    return new
