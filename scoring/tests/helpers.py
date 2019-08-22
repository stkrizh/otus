import functools


def cases(cases):
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args):
            for c in cases:
                new_args = args + (c if isinstance(c, tuple) else (c,))
                try:
                    f(*new_args)
                except Exception as exc:
                    params_msg = ", ".join(map(str, new_args[1:]))
                    if exc.args and exc.args[0]:
                        msg = exc.args[0]
                        exc.args = (str(msg) + " : " + params_msg,)
                    else:
                        exc.args = (params_msg,)
                    raise

        return wrapper

    return decorator
