import re

from django.db.models.loading import get_model
from django.utils.datastructures import SortedDict


def smartlinkable(cls, **smartlink_opts):
    cls_name = cls.__name__
    
    def complain(error_messages, specifier="", starter="should"):
        if len(error_messages) > 1:
            options = True
            options_grammar_1 = "either"
            options_grammar_2 = "has neither"
        else:
            options = False
            options_grammar_1 = ""
            options_grammar_2 = "does not have it."
        messages = "".join(error_messages)
        class_name = cls_name # trick in order to use locals()
        error = """
        Smartlinkable class %(specifier)s %(starter)s %(options_grammar_1)s
        %(messages)s. '%(class_name)s' %(options_grammar_2)s
        """ % locals()
        raise SmartLinkConfigurationError(error)
    
    def validate_search_field(search_type, smartlink_opts, fields):
        if not search_type in smartlink_opts:
            return
        def validate_field(fieldname):
            if "." in fieldname:
                # i can't think of a way to check for things past the dot
                fieldname = fieldname.split(".")[0]
            if not fieldname in fields:
                raise SmartLinkConfigurationError("Smartlinkable class '%s' does not have a field '%s' defined, though it is mentioned in '%s'" % (cls_name, fieldname, search_type))
        
        sf = smartlink_opts[search_type]
        validate_field(sf.field)
            
    fields = [f.name for f in cls._meta.fields]
    if "search_field" in smartlink_opts:
        validate_search_field("search_field", smartlink_opts, fields)
        validate_search_field("disambiguator", smartlink_opts, fields)
        
    else:
        if not smartlink_opts.get('fallback_to_pk', None) \
            and not hasattr(cls.objects, "get_from_smartlink") and not "slug" in fields:
                
            complain(("have a manager with get_from_smartlink method", ", or a field 'slug'", ", or an option 'fallback_to_pk enabled'", ))
    if not hasattr(cls, "get_absolute_url") and not hasattr(cls, "smartlink"):
        complain(("have 'smartlink' method", ", or a 'get_absolute_url' method", ))
        
    if "allowed_embeds" in smartlink_opts:
        if (not hasattr(cls.objects, "get_from_smartembed") and not "slug" in fields):
            complain(("have a manager with a 'get_from_smartembed' method", ", or a 'slug' field", ), "with 'allowed_embeds' option enabled")
        for method in smartlink_opts['allowed_embeds'].values():
            if not hasattr(cls, method):
                complain(("have a '%s' method defined" % method,), "with '%s' in 'allowed_embeds' option" % method)
            
    cls.smartlink_opts = smartlink_opts
    return cls
        
    
class SmartLinkConfigurationError(Exception):
    pass

def raise_import_error(addr):
    raise SmartLinkConfigurationError("Model '%s' specified in settings.SMARTLINKS can not be imported" % addr)

def smartlinksconf(args):
    """
    @accepts: sequence of tuples. elements in tuple correspond to
    - shortcuts used # note: they are case-insensitive
    - address to the model, <app_name>.<model_name>
    - options. Available options:
        x fallback_to_pk - bool, whether we should fall back to primary key 
            if slug is not specified; default - False
        x allowed_embeds - tuple of allowed embedded types
            i.e. ("video", "keyframe")
            
            if this option is specified the model should have 
                  # get_from_smartembed specified OR a slug field defined
                  # all methods specified in allowed_embeds.values() defined
        x search_field - SearchField instance, 
            field - fieldname
            possibly containing dots to specify complex lookups
            if this option is specified, get_from_smartlink is not looked at, and the lookup
            becomes <field>__<search_type>=<link_text>
            
            search_type - type of search, as defined in smartlinks/search_types.py, by default - iexact
            
            
            x disambiguator - can be specified only if search_field is defined. same syntax as search_field,
            defines a lookup field for a disambiguator. If not specified, disambiguator is ignored.
        
    @returns:
    dictionary: shortcut -> (updated & checked) model
    
    @throws:
    SmartLinkConfigurationError
    """
    sl_shortcuts = SortedDict()
    
    for descr in args:
        shortcuts, addr, opts = descr

        # import the appropriate class
        tokens = addr.split(".")
        if not len(tokens) == 2:
            raise_import_error(addr)
        model = get_model(tokens[0], tokens[1])
        if not model:
            raise_import_error(addr)
        smartlinkable_model = smartlinkable(model, **opts)
        for s in shortcuts:
            sl_shortcuts[s.lower()] = smartlinkable_model
    return sl_shortcuts
        
        
def words2num(s):
    """
    Converts strings to numbers (up to 999 999)
    @accepts: str
    @returns: int
    @throws: ValueError (can't figure out)
    
    four -> 4
    five -> 5
    thousand -> 1000
    five thousand and sixty seven > 5067
    
    numbers remain numbers:
    
    3456 -> 3456
    
    """
    primitives = dict(zip("one two three four five six seven eight nine".split(), range(1, 11)))
    teens = dict(zip("eleven twelve thirteen fourteen sixteen seventeen eighteen nineteen".split(), range(11, 20)))
    tens = dict(zip("ten twenty thirty fourty fifty sixty seventy eighty ninety".split(), range(10, 100, 10)))
    multiples = dict(zip("hundred thousand".split(), [1e2, 1e3]))
    
    def primitive(a):
        if a in primitives:
            return primitives[a]
        elif a in tens:
            return tens[a]
        elif a in teens:
            return teens[a]
        elif a in multiples:
            return multiples[a]
        raise ValueError
        
    def up2hundred(tokens):
        if len(tokens) == 2:
            return primitive(tokens[0]) + primitive(tokens[1])
        elif len(tokens) == 1:
            a = tokens[0]
            return primitive(a)
        raise ValueError
       
    def up2thousand(tokens):
        if "hundred" in tokens:
            i = tokens.index("hundred")
            return up2hundred(tokens[:i]) * 100 + up2hundred(tokens[i+1:])
        else:
            return up2hundred(tokens)
        raise ValueError
            
    def up2million(tokens):
        if "thousand" in tokens:
            i = tokens.index("thousand")
            return up2thousand(tokens[:i]) * 1000 + up2thousand(tokens[i+1:])
        return up2thousand(tokens)
        
    try:
        return int(s)
    except ValueError:
        s = s.replace("-", " ")
        tokens = [t for t in s.split() if not t in ("and", " ")]
        
        return up2million(tokens)
        
        
    