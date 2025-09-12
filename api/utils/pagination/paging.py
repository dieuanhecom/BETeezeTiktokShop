def get_paging(request, allowed_keys=None):
    if allowed_keys is None:
        allowed_keys = ["offset", "limit"]
    paging = {}
    for key in allowed_keys:
        if key in request.query_params:
            if key == "limit":
                paging[key] = min(int(request.query_params.get(key)), 10)
            elif key == "offset":
                paging[key] = max(int(request.query_params.get(key)), 0)
    return paging
