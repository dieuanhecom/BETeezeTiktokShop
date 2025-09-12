from urllib.parse import parse_qs

from api.utils.constants.pagination import allowed_filter_operations


def get_filter(request, allowed_keys):
    filters = {}
    query_params = parse_qs(request.META["QUERY_STRING"])
    for key, values in query_params.items():
        if key.startswith("filter."):
            modified_key = key[7:]
            if modified_key in allowed_keys:
                if modified_key not in filters:
                    filters[modified_key] = {}
                for value in values:
                    if ":" in value:
                        operation, op_value = value.split(":", 1)
                        if operation in allowed_filter_operations:
                            filters[modified_key][operation] = op_value
    return filters
