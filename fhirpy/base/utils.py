import reprlib
from urllib.parse import parse_qs, quote, urlencode, urlparse

from yarl import URL


class AttrDict(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__dict__ = self

    def get_by_path(self, path, default=None):
        keys = parse_path(path)
        return get_by_path(self, keys, default)


class SearchList(list):
    def get_by_path(self, path, default=None):
        keys = parse_path(path)
        return get_by_path(self, keys, default)


def chunks(lst, n):
    """
    Yield successive n-sized chunks from l

    >>> list(chunks([1, 2, 3, 4], 2))
    [[1, 2], [3, 4]]
    """
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


def unique_everseen(seq):
    """
    >>> unique_everseen(['1', '2', '3', '1', '2'])
    ['1', '2', '3']
    """
    seen = set()
    seen_add = seen.add
    return [x for x in seq if not (x in seen or seen_add(x))]


def encode_params(params):
    """
    >>> encode_params({'status:not': ['active', 'entered-in-error']})
    'status:not=active&status:not=entered-in-error'

    >>> encode_params({'status': ['active,waitlist']})
    'status=active,waitlist'

    >>> encode_params({'status': 'active,waitlist'})
    'status=active,waitlist'

    >>> encode_params({'_format': ['json', 'json']})
    '_format=json'

    >>> encode_params(None)
    ''
    """
    params = params or {}
    return urlencode(
        {k: unique_everseen(v) if isinstance(v, list) else [v] for k, v in params.items()},
        doseq=True,
        safe=":,",
        quote_via=quote,
    )


def parse_pagination_url(url):
    """
    Parses Bundle.link pagination url and returns path and params

    >>> parse_pagination_url('/Patient?_count=100&name=ivan&name=petrov')
    ('/Patient', {'_count': ['100'], 'name': ['ivan', 'petrov']})
    """
    if URL(url).is_absolute():
        return url, None
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    path = parsed.path

    return path, params


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
    ... lambda x: (x + 1, False) if isinstance(x, int) else (x, False))
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
        return SearchList(convert_values(x, fn) for x in data)
    if isinstance(data, dict):
        return AttrDict({key: convert_values(value, fn) for key, value in dict.items(data)})
    return data


def parse_path(path):
    """
    >>> parse_path(['path', 'to', 0, 'element'])
    ['path', 'to', 0, 'element']

    >>> parse_path('path.to.0.element')
    ['path', 'to', 0, 'element']
    """
    if isinstance(path, str):
        return [int(key) if key.isdigit() else key for key in path.split(".")]
    if isinstance(path, list):
        return path

    raise TypeError("Path must be or a dotted string or a list")


def get_by_path(data, path, default=None):
    """
    >>> get_by_path({'key': 'value'}, ['key'])
    'value'

    >>> get_by_path({'key': [{'nkey': 'nvalue'}]}, ['key', 0, 'nkey'])
    'nvalue'

    >>> get_by_path({
    ...     'key': [
    ...         {'test': 'test0', 'nkey': 'zero'},
    ...         {'test': 'test1', 'nkey': 'one'}
    ...     ]
    ... }, ['key', {'test': 'test1'}, 'nkey'])
    'one'

    >>> get_by_path({'a': 1}, ['b'], 0)
    0

    >>> get_by_path({'a': {'b': None}}, ['a', 'b'], 0) is None
    True

    >>> get_by_path({'a': {'b': None}}, ['a', 'b', 'c'], 0)
    0
    """
    assert isinstance(path, list), "Path must be a list"

    rv = data
    try:
        for key in path:
            if rv is None:
                return default

            if isinstance(rv, list):
                if isinstance(key, int):
                    rv = rv[key]
                elif isinstance(key, dict):
                    matched_index = -1
                    for index, item in enumerate(rv):
                        if all(item.get(k, None) == v for k, v in key.items()):
                            matched_index = index
                            break
                    rv = None if matched_index == -1 else rv[matched_index]
                else:
                    raise TypeError(
                        f"Can not lookup by {reprlib.repr(key)} in list. "
                        "Possible lookups are by int or by dict."
                    )
            else:
                rv = rv[key]

        return rv
    except (IndexError, KeyError, AttributeError):
        return default


def set_by_path(obj, path, value):
    cursor = obj
    last_part = path.pop()

    for index, part in enumerate(path):
        if isinstance(cursor, dict) and part not in cursor:
            nextpart = ([*path, last_part])[index + 1]
            try:
                nnextpart = ([*path, last_part])[index + 2]
            except IndexError:
                nnextpart = ""

            if isinstance(nextpart, int):
                cursor[part] = [[] if isinstance(nnextpart, int) else {}]
            else:
                cursor[part] = {}

        cursor = cursor[part]
    cursor[last_part] = value


def remove_prefix(s, prefix):
    return s[len(prefix) :] if s.startswith(prefix) else s
