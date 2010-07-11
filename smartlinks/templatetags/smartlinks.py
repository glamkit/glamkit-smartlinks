import re
import types

from django.template.defaultfilters import slugify
from django.conf import settings
from django import template
from django.utils.safestring import mark_safe
from django.core.urlresolvers import reverse
from django.utils.encoding import smart_str

from ..smartlinks.utils import smartlinksconf

register = template.Library()

smartlinked_models = None
def configure():
    global smartlinked_models
    smartlinked_models = smartlinksconf(settings.SMARTLINKS)
configure()

smartlink_finder = re.compile(r"""
                    (?<![\\])                                        # do NOT match things preceded by a slash
                    \[
                        ((?P<ModelName>\w+))?                        # Object name
                        (\:(?P<KeyTerm>[^\[]+)?)?                        # value to search in key_field
                        ((?P<OptionalSpace>\s+))?                      # optional space
                            \[
                                \s* (?P<SearchTerm>[-\w\'\"<>:\s\(\)]+) \s*   # query string
                            \] \s*
                        ((?P<Options>[\w\. /\\|\(\)=]+))?                    # options
                    \]
                    """,
                    re.VERBOSE)
               
smartembed_finder = re.compile(r"""
                    \{
                    (?P<ModelName>\w+) \. (?P<EmbedType>\w+) \s*
                        \{
                            (?P<Slug>[\w-]+)
                        \}
                        \s*
                        ((?P<Options>[\w\. /\\|\(\)=]+))?
                        \s*
                    \}
                    """,
                    re.VERBOSE)

class SmartLinksParser(object):
    def __init__(self, arg):
        self.arg = arg
        
    def _return_identity(self):
        return self.match.group()
        
    def _return_span(self, cls=""):
        return "<span %s>%s</span>" % (cls, self.search_term)
        
    def _return_unresolved(self):
        return self._return_span('class="smartlinks-unresolved"')
        
    def _return_ambiguous(self):
        return self._return_span('class="smartlinks-ambiguous"')

    def _handle_object(self, obj):
        """
        @returns 
        link corresponding to the object obj
        """
        if hasattr(obj, "smartlink"):
            return obj.smartlink(self.search_term, *self.args, **self.kwargs)
        else:
            url = obj.get_absolute_url() # should never raise attribute error
            return '<a href="%s">%s</a>' % (url, self.search_term)
            
    def _get_object(self, model):
        """
        x try to get an object corresponding to the search
        term & disambiguator and a current model
        
        @returns
        object
        
        @throws
        model.DoesNotExist
        model.MultipleObjectsReturned
        """
        fields = [f.name for f in model._meta.fields]
        qs = {}

        key_field = model.smartlink_opts.get('key_field')
        search_field = model.smartlink_opts.get('search_field')

        if key_field or search_field:
            if key_field and self.key_term:
                qs[key_field.generate()] = self.key_term
                try:
                    return model.objects.get(**qs) # let's pray that wouldn't raise a FieldError...
                except model.MultipleObjectsReturned:
                    pass
                except model.DoesNotExist:
                    qs = {} # reset it (so we can try search_field)

            if search_field:
                qs[search_field.generate()] = self.search_term
                try:
                    return model.objects.get(**qs) # let's pray that wouldn't raise a FieldError...
                except model.MultipleObjectsReturned:
                    if "disambiguator" in model.smartlink_opts and self.disambiguator:
                        dmb = model.smartlink_opts["disambiguator"]
                        qs[dmb.generate()] = self.disambiguator
                        return model.objects.get(**qs) # try again, it just might give us a single result!
                    else:
                        raise
        else:
            if hasattr(model.objects, "get_from_smartlink"):
                obj = model.objects.get_from_smartlink(self.search_term, disambiguator=self.disambiguator, arg=self.arg)
            else:
                if "slug" in fields:
                    obj = model.objects.get(slug=slugify(self.search_term)) # what if model does not have an attribute 'slug'?
                elif model.smartlink_opts.get("fallback_to_pk", None):
                    obj = model.objects.get(pk=slugify(self.search_term))
                # we should never get to the else statement. ever.
            return obj
        
    def _parse_dumblink(self):
        if not self.optional_space in ("", None):
            return self._return_identity()
        obj = None
        for model in smartlinked_models.values(): # dictionary used _is_ ordered
            try:
                obj = self._get_object(model)
                break
            except (model.DoesNotExist):
                continue
            except (model.MultipleObjectsReturned):
                return self._return_ambiguous()
        if obj:
            return self._handle_object(obj) 
        return self._return_unresolved()
        
    def _parse_smartlink(self):
        try:
            model = smartlinked_models[self.model_name]
        except KeyError:
            return self._return_identity()
        try:
            obj = self._get_object(model)
        except (model.MultipleObjectsReturned):
            return self._return_ambiguous()            
        except (model.DoesNotExist):
            if hasattr(model.objects, "smartlink_fallback"):
                return model.objects.smartlink_fallback(self.search_term, disambiguator=self.disambiguator, arg=self.arg)
            return self._return_unresolved()
        return self._handle_object(obj)
        
    def parse_link(self, match):
        """
        @accepts: regexp match
        @returns: html for the smartlink
        
        """
        self.match = match
        
        self.search_term = match.group("SearchTerm").strip()
        self.model_name = match.group("ModelName")
        self.key_term = match.group("KeyTerm")
        if self.key_term:
            self.key_term = self.key_term.strip()
        self.optional_space = match.group("OptionalSpace")
        self.args, self.kwargs = self._parse_options(match.group("Options"))
        self.disambiguator = None
        if self.args:
            self.disambiguator = self.args.pop(0)

        self.is_dumb = self.model_name is None and not "" in smartlinked_models
        self.model_name = self.model_name.lower() if self.model_name else '' # convert None to ''
        
        if self.is_dumb:
            return self._parse_dumblink()
        return self._parse_smartlink()
        


    def _parse_options(self, value):
        args = []
        kwargs = {}
        if value:
            kvpairs = value.split("|")
            for kv in kvpairs:
                kv = kv.strip()

                if '=' not in kv:
                    args.append(kv)
                else:
                    k, v = kv.split("=")
                    k = k.strip()
                    v = v.strip()
                    kwargs.update([(smart_str(k),v)])
        return args, kwargs


class SmartEmbedsParser(SmartLinksParser):
    def _fail(self):
        return u""
        
    def _get_object(self, model):
       return model.objects.get_from_smartembed(slug=self.slug, disambiguator=self.disambiguator, arg=self.arg)
        
    def _handle_object(self, obj):
       return getattr(obj, obj.smartlink_opts["allowed_embeds"][self.embed_type])(*self.args, **self.kwargs)
        
    def _parse_smartembed(self):
        try:
            model = smartlinked_models[self.model_name.lower()]
        except KeyError:
            return self._fail()
            
        if not "allowed_embeds" in model.smartlink_opts:
            return self._fail()
        if not self.embed_type in model.smartlink_opts["allowed_embeds"]:
            return self._fail()
            
        try:
            obj = self._get_object(model)
        except (model.MultipleObjectsReturned, model.DoesNotExist):
            return self._fail()
        return self._handle_object(obj)
    
    def parse_embed(self, match):
        self.match = match
        
        self.model_name = match.group("ModelName")
        self.embed_type = match.group("EmbedType")
        self.slug = match.group("Slug").strip()
        self.args, self.kwargs = self._parse_options(match.group("Options"))
        self.disambiguator = None
        if self.args:
            self.disambiguator = self.args.pop(0)
        
        return self._parse_smartembed()
        
@register.filter
def smartlinks(value, arg=None):
    value = smartlink_finder.sub(SmartLinksParser(arg).parse_link, value)
    value = smartembed_finder.sub(SmartEmbedsParser(arg).parse_embed, value)
    return mark_safe(value)
