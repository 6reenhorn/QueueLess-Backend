TRUTHY_BOOLEAN_VALUES = {"1", "true", "t", "yes", "y", "on"}
FALSY_BOOLEAN_VALUES = {"0", "false", "f", "no", "n", "off"}
INVALID_BOOLEAN_QUERY_VALUE = object()


def parse_bool_query_param(value, default: bool = False) -> bool:
    if value is None:
        return default

    normalized_value = str(value).strip().lower()
    if normalized_value in TRUTHY_BOOLEAN_VALUES:
        return True
    if normalized_value in FALSY_BOOLEAN_VALUES:
        return False
    return default


def parse_bool_query_param_strict(value):
    if value is None:
        return None

    normalized_value = str(value).strip().lower()
    if normalized_value in TRUTHY_BOOLEAN_VALUES:
        return True
    if normalized_value in FALSY_BOOLEAN_VALUES:
        return False
    return INVALID_BOOLEAN_QUERY_VALUE
