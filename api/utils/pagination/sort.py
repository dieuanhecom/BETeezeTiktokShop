from urllib.parse import parse_qs
from api.utils.constants.pagination import allowed_sort_operations


def get_sort(request):
    query_params = parse_qs(request.META["QUERY_STRING"])
    sort_params = {}
    for key, values in query_params.items():
        if key.startswith("sort."):
            modified_key = key[5:]
            sort_order_str = values[-1]
            if sort_order_str in allowed_sort_operations:
                sort_order = 1 if sort_order_str == "asc" else -1
                sort_params[modified_key] = sort_order
    return sort_params
