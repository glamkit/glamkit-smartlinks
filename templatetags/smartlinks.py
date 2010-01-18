import re
import types

from django.template.defaultfilters import slugify
from django.conf import settings
from django import template
from django.utils.safestring import mark_safe
from django.core.urlresolvers import reverse

from ..smartlinks.utils import smartlinksconf

register = template.Library()

smartlinked_models = smartlinksconf(settings.SMARTLINKS)

smartlink_finder = re.compile(r"""
                    (?<![\\])                                        # do NOT match things preceded by a slash
                    \[
                        ((?P<ModelName>\w+))?                        # Object name
                        ((?P<OptionalSpace>\s+))?                      # optional space
                            \[
                                \s* (?P<SearchTerm>[-\w\'\"<>:\s\(\)]+) \s*   # query string
                            \] \s*
                        ((?P<Disambiguator>[\w\. /]+))?                    # disambiguator
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
                        ((?P<Disambiguator>\w+))?
                        \s*
                    \}
                    """,
                    re.VERBOSE)

class SmartLinksParser(object):
    def __init__(self, arg):
        self.arg = arg
        
    def _return_identity(self):
        return self.match.group()
        
    def _return_cite(self, cls=""):
        return "<cite %s>%s</cite>" % (cls, self.search_term)
        
    def _return_unresolved(self):
        return self._return_cite('class="unresolved"')
        
    def _return_ambigous(self):
        return self._return_cite('class="ambiguous"')

    def _handle_object(self, obj):
        """
        @returns 
        link corresponding to the object obj
        """
        if hasattr(obj, "smartlink"):
            return obj.smartlink(self.search_term)
        else:
            url = obj.get_absolute_url() # should never raise attribute error
            return '<a href="%s">%s</a>' % (url, self.search_term)
            
    def _get_object(self, model):
        """
        x try to get an obect corresponding to the search
        term & disambiguator and a current model
        
        @returns
        object
        
        @throws
        model.DoesNotExist
        model.MultipleObjectsReturned
        """
        fields = [f.name for f in model._meta.fields]
        if "search_field" in model.smartlink_opts:
            qs = {}
            sf = model.smartlink_opts["search_field"]
            qs[sf.generate()] = self.search_term
            if "disambiguator" in model.smartlink_opts and self.disambiguator:
                dmb = model.smartlink_opts["disambiguator"]
                qs[dmb.generate()] = self.disambiguator
            return model.objects.get(**qs) # let's pray that wouldn't raise a FieldError...
                 
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
                return self._return_ambigous()
        if obj:
            return self._handle_object(obj) 
        return self._return_unresolved()
        
    def _parse_smartlink(self):
        # very-very-ugly hardcoded bit
        # to be removed, hopefuly soon
        # (and better integration with mongo
        # needs to be introduced) 
        if self.model_name == "c":
            return "<a href='%s'>%s</a>" % (reverse("collection_item", args=[slugify(self.disambiguator)]), self.search_term)
        
        # back to pretty code:
        try:
            model = smartlinked_models[self.model_name]
        except KeyError:
            return self._return_identity()
        try:
            obj = self._get_object(model)
        except (model.MultipleObjectsReturned):
            return self._return_ambigous()            
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
        self.disambiguator = match.group("Disambiguator")
        self.optional_space = match.group("OptionalSpace")

        self.is_dumb = self.model_name is None and not "" in smartlinked_models
        self.model_name = self.model_name.lower() if self.model_name else '' # convert None to ''
        
        if self.is_dumb:
            return self._parse_dumblink()
        return self._parse_smartlink()
        
class SmartEmbedsParser(SmartLinksParser):
    def _fail(self):
        return u""
        
    def _get_object(self, model):
       return model.objects.get_from_smartembed(slug=self.slug, disambiguator=self.disambiguator, arg=self.arg)
        
    def _handle_object(self, obj):
       return getattr(obj, obj.smartlink_opts["allowed_embeds"][self.embed_type])()
        
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
        self.disambiguator = match.group("Disambiguator")
        
        return self._parse_smartembed()
        
@register.filter
def smartlinks(value, arg=None):
    value = smartlink_finder.sub(SmartLinksParser(arg).parse_link, value)
    value = smartembed_finder.sub(SmartEmbedsParser(arg).parse_embed, value)
    return mark_safe(value)
