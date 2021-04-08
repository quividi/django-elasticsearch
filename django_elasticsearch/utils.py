from collections.abc import Iterable, Mapping


def nested_update(d, u):
    for k, v in u.items():
        if isinstance(v, Mapping):
            r = nested_update(d.get(k, {}), v)
            d[k] = r
        elif isinstance(v, Iterable):
            try:
                d[k].extend(u[k])
            except KeyError:
                d[k] = u[k]
        else:
            d[k] = u[k]
    return d


def dict_depth(d, depth=0):
    if not isinstance(d, dict) or not d:
        return depth
    return max(dict_depth(v, depth + 1)
               for k, v in d.items())
