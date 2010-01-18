search_types = {"equals": 1, "icontains": 2, "iexact": 3}
search_types_lookup = dict([(value, key) for key, value in search_types.items()])

SearchType = type("SearchType", (object,), search_types)

class SearchField:
    def __init__(self, search_field, search_type=SearchType.iexact):
        self.field = search_field
        self.search_type = search_types_lookup[search_type]
        
    def generate(self):
        sf = self.field.replace(".", "__")
        if not self.search_type == "equals":
            sf += "__%s" % self.search_type
        return sf