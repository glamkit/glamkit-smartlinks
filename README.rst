=================
DJANGO-SMARTLINKS
================

-----------------------------
by the Interaction Consortium
-----------------------------

DESCRIPTION
===========
Introduction to Smartlinks
Smartlinks are a way to allow content editors to create a ‘link’ to what is usually a django model instance, by typing some smartlink markup into content in the admin interface (or conceivably anywhere). They are inspired by the internal links syntax on wiki. One can think of them as wiki links on steroids - much more powerful and customisable. The link relies on an editor's understanding of the page to link to, rather than any particular knowledge of the underlying model or the site's URLconf. A typical example:

[title[Mad Max]] is transformed to <a href="/title/mad-max/">Mad Max</a>
but you could also use, depending on preference or circumstance:

[t[Mad Max]]
[title[Mad Max]1979]
[[Mad Max]]

The text in between the innermost square brackets is the linked text, by default, but most importantly it is used as the search text for the item to link to.

If no item can be found, then a <cite class="unresolved"> is returned by default, e.g. [t[Mad Megan]] becomes <cite class="unresolved">Mad Megan</cite>. When a Mad Megan item is created, the link starts working. This means that editors can put smartlinks in for items that do not exist yet.

If several items are found, then a <cite class="ambiguous"> is returned by default, e.g. [t[On Our Selection]] becomes <cite class="ambiguous">On Our Selection</cite>. Ambiguous items can be resolved by adding a disambiguator, either in the link text ([t[On Our Selection (1920)]]) or after the innermost brackets ([t[On Our Selection]1920]]).


INSTALLATION
============
To add smartlinks to your django project:
Getting started is easy:

1. Install the smartlinks app to your project.

2. Add the option SMARTLINKS to your settings file (the easiest way to do that would be copying smartlinks_conf.py_example to smartlinks_conf.py, modifying it up to your test, and importing it in the settings.py file)

3. to parse smartlinks within templates, use the 'smartlinks' filter:
    
(assuming the variable 'data' holds some smartlinkable text, like '[person[Stanley Kubrick]] had a close working relationship with [p[Peter Sellers]1989], one of the finest character actors in modern cinema.'

    {% load smartlinks %}

    {{ data | smartlinks }}
    
    
In this example, assuming Person.objects.get(name="Stanley Kubrick") exists, but Person.objects.get(name="Peter Sellers", birth_year=1989) does not (yet), this would produce

<a href="/person/stanley-kubrick/">Stanley Kubrick</a> had a close working relationship with <cite class="unresolved">Peter Sellers</cite>, one of the finest character actors in modern cinema.
Customising Smartlink Behaviour
Smartlinks have the form

[shortcut[link_text]link_suffix]

shortcut is used to find the model, as defined in the SMARTLINKS variable

link_text is used to find the model instance, and is (by default) the text of the hyperlink

link_suffix is normally used to disambiguate the model instance in a way that doesn't affect in the text of a hyperlink, as in [t[Mad Max]1979].

You can also choose to use link_text and suffix in a different way for each model, by writing a custom smartlinks resolver.

CONFIGURATION
=============

SMARTLINKS settings variable
----------------------------

Here is example of smartlinks configuration::

    from smartlinks.search_types import SearchField, SearchType

    SMARTLINKS = (
        (('m', 'Movie',), 'collection.Move', {}),
        (('v', 'venue',), 'whats_on.Venue', {"search_field": SearchField("name")}),
        (('x', 'exhibition',), "whats_on.Exhibition", {"search_field": SearchField("title"), "disambiguator": SearchField("start.year", SearchType.equals)}),
        (('',), "lumpypages.LumpyPage", {"search_field": SearchField("title"), "disambiguator": SearchField("url")}),
    )

The syntax for the rule is ((<tuple containing possible prefixes>), <path to the model, as in app_name.model_name>, <options>).
(We are making an assumption that each model defined in SMARTLINKS has a corresponding url, which is specified either through get_absolute_url() or through a custom smartlinks-specific hook)

Prefix defines which model will 'render' the smartlink. The order of models specified in SMARTLINKS matters - it specifies in which order models will try to render a smartlink (i.e. if first model finds no match, second one tries to render it, etc.). Also, if no prefix is specified in the smartlinks, all models get turns in trying to render it, in the specified order.


Smartlinks hooks
----------------
x 'get_from_smartlink' function in model manager - getting the instance. For example::
    
    def get_from_smartlink(self, link_text, disambiguator=None, arg=None):
        if disambiguator:
            # disambiguator has to be a number
            try:
                no = int(disambiguator)
            except ValueError:
                raise Person.DoesNotExist
            return self.model.objects.get(name__iexact=link_text, no=no)
        return self.model.objects.get(name__iexact=link_text)
        
x 'smartlink_fallback' function in model manager - what happens when no corresponding entity is found::
    
    def smartlink_fallback(self, link_text, disambiguator=None, arg=None):
        return '<cite class="unresolved">%s</cite>' % link_text

x 'smartlink' function in model definition - how smartlink should be rendered. In case if it's not specified, a link to the model (with url from get_absolute_url) and a text inside a smartlink is generated::
    
    def smartlink(self, search_term):
        return '<a href="/person/%s/">%s</a>' % (self.slug, search_term)


By default, smartlinks are resolved by a simple Person.objects.get(<default_field>=<link_text>, <suffix_field>=<suffix>)

If the model's manager has a get_from_smartlink method, then that is used instead. The parameters of get_from_smartlink are:

shortcut
link_text
link_suffix
context
Which are the components of the smartlink, plus the context of the template at the point of the {% smartlinks %} tag. This manager function can use these in whichever way it sees fit to return:

items, a queryset of matching items.
If items.count() is 0 (meaning item is null) or  items.count() > 1 the link normally fails, and a <cite> is returned.

Implementing a Custom Smartlinks Renderer
By default, smartlinks are parsed to:

'<a href="%s">%s</a>' % (items[0].get_absolute_url(), link_text)
or, if items.count == 0

'<cite class="unresolved">%s</cite>' % link_text
or, if items.count > 1

'<cite class="ambiguous">%s</cite>' % link_text
You can override the link behaviour by defining a smartlink(self, shortcut, link_text, suffix, context) function on the model, which returns a string (i.e. an HTML link).

You can override the fallback behaviour by defining the class method Model.smartlink_fallback(items, shortcut, link_text, suffix, context), which returns a string (i.e. a <cite>, or a search link, or a list of links to each item in items).

