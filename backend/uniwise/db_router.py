from django.conf import settings


def _parse_university_db_map():
    mapping = {}
    raw = getattr(settings, "UNIVERSITY_DB_ALIAS_MAP", "") or ""
    for token in raw.split(","):
        item = token.strip()
        if not item or ":" not in item:
            continue
        university_id, alias = item.split(":", 1)
        university_id = university_id.strip()
        alias = alias.strip()
        if not university_id.isdigit() or not alias:
            continue
        mapping[int(university_id)] = alias
    return mapping


class UniversityDatabaseRouter:
    """
    Optional multi-database router for future hard tenancy.
    Activate by defining UNIVERSITY_DB_ALIAS_MAP, e.g.:
      UNIVERSITY_DB_ALIAS_MAP=1:uni_1,2:uni_2
    """

    def __init__(self):
        self._map = _parse_university_db_map()

    def _resolve_db_alias(self, hints):
        university_id = hints.get("university_id")
        if isinstance(university_id, str) and university_id.isdigit():
            university_id = int(university_id)
        if isinstance(university_id, int):
            return self._map.get(university_id)
        return None

    def db_for_read(self, model, **hints):
        return self._resolve_db_alias(hints)

    def db_for_write(self, model, **hints):
        return self._resolve_db_alias(hints)

    def allow_relation(self, obj1, obj2, **hints):
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        return True
