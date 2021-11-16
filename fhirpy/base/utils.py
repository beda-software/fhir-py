import reprlib
from urllib.parse import urlencode, quote, parse_qs, urlparse
from yarl import URL


class AttrDict(dict):
    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self

    def get_by_path(self, path, default=None):
        keys = parse_path(path)
        return get_by_path(self, keys, default)


class SearchList(list):
    def get_by_path(self, path, default=None):
        keys = parse_path(path)
        return get_by_path(self, keys, default)


def chunks(l, n):
    """
    Yield successive n-sized chunks from l

    >>> list(chunks([1, 2, 3, 4], 2))
    [[1, 2], [3, 4]]
    """
    for i in range(0, len(l), n):
        yield l[i : i + n]


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
        {
            k: unique_everseen(v) if isinstance(v, list) else [v]
            for k, v in params.items()
        },
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
        return AttrDict({key: convert_values(value, fn) for key, value in data.items()})
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
    elif isinstance(path, list):
        return path
    else:  # pragma: no cover
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
                        if all([item.get(k, None) == v for k, v in key.items()]):
                            matched_index = index
                            break
                    if matched_index == -1:
                        rv = None
                    else:
                        rv = rv[matched_index]
                else:  # pragma: no cover
                    raise TypeError(
                        "Can not lookup by {0} in list. "
                        "Possible lookups are by int or by dict.".format(
                            reprlib.repr(key)
                        )
                    )
            else:
                rv = rv[key]

        return rv
    except (IndexError, KeyError, AttributeError):
        return default


def remove_prefix(s, prefix):
    return s[len(prefix) :] if s.startswith(prefix) else s
