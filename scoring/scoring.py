import hashlib


def build_score_key(
    first_name=None,
    last_name=None,
    email=None,
    phone=None,
    gender=None,
    birthday=None,
):
    key_parts = [
        first_name or "",
        last_name or "",
        email or "",
        phone or "",
        str(gender) if gender is not None else "",
        birthday.strftime("%Y%m%d") if birthday is not None else "",
    ]
    key = "uid:" + hashlib.md5("".join(key_parts)).hexdigest()
    return key


def get_score(
    store,
    phone,
    email,
    birthday=None,
    gender=None,
    first_name=None,
    last_name=None,
):
    key = build_score_key(
        first_name, last_name, email, phone, gender, birthday
    )

    # try get from cache,
    # fallback to heavy calculation in case of cache miss

    score = store.cache_get(key) or 0
    if score:
        return score
    if phone:
        score += 1.5
    if email:
        score += 1.5
    if birthday and gender:
        score += 1.5
    if first_name and last_name:
        score += 0.5

    # cache for 60 minutes
    store.cache_set(key, score, 60 * 60)
    return score


def get_interests(store, cid):
    r = store.get("i:%s" % cid)
    return r
