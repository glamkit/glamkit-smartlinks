DJANGO-SMARTLINKS
the Interaction Consortium

DESCRIPTION
-----------
Introduction to Smartlinks
Smartlinks are a way to allow content editors to create a ‘link’ to what is usually a django model instance, by typing some smartlink markup into content in the admin interface (or conceivably anywhere). They are somewhat inspired by the internal links syntax on wiki. The link relies on an editor's understanding of the page to link to, rather than any particular knowledge of the underlying model or the site's URLconf. A typical example:

[title[Mad Max]] is transformed to <a href="/title/mad-max/">Mad Max</a>
but you could also use, depending on preference or circumstance:

[t[Mad Max]]
[title[Mad Max]1979]
[[Mad Max]]

The text in between the innermost square brackets is the linked text, by default, but most importantly it is used as the search text for the item to link to.

If no item can be found, then a <cite class="unresolved"> is returned by default, e.g. [t[Mad Megan]] becomes <cite class="unresolved">Mad Megan</cite>. When a Mad Megan item is created, the link starts working. This means that editors can put smartlinks in for items that do not exist yet.

If several items are found, then a <cite class="ambiguous"> is returned by default, e.g. [t[On Our Selection]] becomes <cite class="ambiguous">On Our Selection</cite>. Ambiguous items can be resolved by adding a disambiguator, either in the link text ([t[On Our Selection (1920)]]) or after the innermost brackets ([t[On Our Selection]1920]]).


INSTALLATION
------------
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

shortcut is used to find the model, as defined in the @smartlinkable decorator.

link_text is used to find the model instance, and is (by default) the text of the hyperlink

link_suffix is normally used to disambiguate the model instance in a way that doesn't affect in the text of a hyperlink, as in [t[Mad Max]1979].

You can also choose to use link_text and suffix in a different way for each model, by writing a custom smartlinks resolver.

Implementing a Custom Smartlinks Resolver
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

