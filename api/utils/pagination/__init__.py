from api.utils.pagination.filter import get_filter
from api.utils.pagination.paging import get_paging
from api.utils.pagination.sort import get_sort


def get_pagination(request, allowed_keys=None):
    # pagination = get_paging(request)
    limit = request.query_params.get("limit", 10)
    offset = request.query_params.get("offset", 0)
    try:
        limit = int(limit)
        offset = int(offset)
    except ValueError:
        raise ValueError("Limit and offset must be integers.")
    limit = max(1, min(limit, 1000))
    offset = max(0, offset)
    filters = get_filter(request, allowed_keys)
    sorts = get_sort(request)
    return {"limit": limit, "offset": offset}, filters, sorts
