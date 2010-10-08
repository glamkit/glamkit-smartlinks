Smartlinks
==========

Smartlinks bring easy, but powerful wiki-style internal links to Django websites. Smartlinks encourage separation of content and structure, and reduce unsightly link-rot.

.. rubric:: This is part of the GLAMkit Project. For more information, please visit http://glamkit.org.

Use case
--------

Most large institutional websites have two distinct types of content:

1. **database-driven content**: typically this content will be entered into the admin as raw, semantically-structured data. The Django URLconf, views, and templating system converts this data into human-readable, navigable pages. Examples from a typical GLAM site would be - event information, collection information, staff listings etc. Links between pages are usually generated and managed programmatically.
2. **page-based content**: this content is managed on a page-by-page basis. It is much more organic, and less structured. The navigational structure is generally managed by the content editors. Content is typically entered as blocks of text. Sometimes these text blocks need to contain inline links to other pages on the site. Because these links are normally hard-coded in the database, they can become difficult to maintain if the site structure changes. **This is where smartlinks can help.**

Smartlinks give content editors a way to make quick, easy links to other pages, which will continue to work even if the target page moves, and will degrade gracefully if the target page disappears. With smartlinks, it is even possible to create conditional links to content that doesn't yet exist, but may one day exist - when the target content is published, the link automatically activates!

How do they work?
-----------------

Smartlinks can be configured to work with any of your Django models. Once smartlinks have been defined on a model, and the smartlinks templatetag has been added to the relevant templates, content editors can mark up text with double square-brackets to create links to pages corresponding to instances of that model.

.. highlight:: html

To give a simple example - with correctly configured smartlinks, the following marked-up text::

    Their next production was a humorous film about the search for [[The Holy Grail]].

could render with an automated link to an already existing page with the title "The Holy Grail", like so::

    Their next production was a humorous film about the search for <a href="/collection-items/grail/">The Holy Grail</a>.

Conversely, if the Holy Grail page does not exist, or has not been published yet, the markup would render as::

    Their next production was a humorous film about the search for The Holy Grail.
    
Handling different target models
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Often, smartlinks also include a prefix with specifies the type of object to link to. For example::
    
    [film[Jabberwocky]], the film, had only a tenuous thematic connection with [poem[Jabberwocky]], the poem.
    
could be configured to render as::

    <a href="/films/monty-python/jabberwocky/">Jabberwocky</a>, the film, had only a tenuous thematic connection with <a href="/poems/carroll/jabberwocky/">Jabberwocky</a>, the poem.
    
In common usage, prefixes also have a shortcut form, so that::

    [f[Jabberwocky]], the film, had only a tenuous thematic connection with [p[Jabberwocky]], the poem.
    
would produce the same results.

The importance of thoughtful configuration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To make smartlinks easy and intuitive for content editors to use, developers need to take care with the configuration stage (see :ref:`smartlinks-config`). The syntax for smartlinks should rely on an editor's understanding of the content on the page they are linking to, rather than any particular knowledge of the underlying model or the site's URLconf.

Smartlinks syntax
-----------------

Smartlinks are built out of the following components::

    [prefix:key[linktext]disambiguator|options]
    
Of these, only linktext and prefix are mandatory (although "" - an empty string, is a perfectly valid prefix). By default, both are case-insensitive.

* **linktext** as the name suggests, denotes the text to appear in the link. It usually also acts as a search string to match a field on the targeted model. By default it is case insensitive.
* **prefix**  is used to denote a model to search against. By default it is case insensitive.
* **disambiguator** is an optional component which can be used to resolve multiple responses, it is normally handled with an additional search against a model field. Generally it is ignored if the linktext has already matched a single object
* **options** additional options in the form of simple strings or key-value pairs may be specified after the disambiguator, separated by the 'pipe' character (|).
* **key** when this component is present it overrides the linktext and disambiguator for the purposes of searching the model. Once again this is linked to a specific field on the model - usually something immutable, such as a ``slug`` or ``id``.

While these behaviours are typical and implicit (if you use the most simple configuration approach), they can be over-ridden using :ref:`smartlinks-hooks`

.. _smartlinks-simple-examples:

Some simple examples
^^^^^^^^^^^^^^^^^^^^

.. highlight:: python

Given the following model::

    class Film(models.Model):
        title = models.CharField(max_length=100)
        slug = models.SlugField()
        year = models.IntegerField()
    
you could configure a simple smartlinks syntax that connects the ``title`` field with the linktext component, uses the ``year`` field as a disambiguator, and set the strings 'f', and 'film' as the prefix for this model (see :ref:`smartlinks-config` to learn how to do this).

Now, let's create a ``Film`` object, and try to reference it with samrtlinks::

    >>> f1 = Film(title="The Wicker Man", slug="wicker-man", year=1973)
    >>> f1.save()

.. highlight:: html

The following are examples of smartlinks based on this content:

=================================  ================================================================  ========================================================
Smartlink                          HTML     
=================================  ================================================================  ========================================================
``[film[The Wicker Man]]``         ``<a href="/films/wicker-man/">The Wicker Man</a>``
``[f[The Wicker Man]]``            ``<a href="/films/wicker-man/">The Wicker Man</a>``               Prefixes work just the same in their abbreviated form
``[FILM[The Wicker Man]]``         ``<a href="/films/wicker-man/">The Wicker Man</a>``               Prefixes are not case sensitive
``[f[ the Wicker Man ]]``          ``<a href="/films/wicker-man/"> the Wicker Man </a>``             Linktext is not case sensitive. Leading and trailing whitespace are ignored,
``[f[The Wicker Basket]]``         ``<span class="smartlinks-unresolved">The Wicker Basket</span>``  This smartlink fails to find a match, and uses the default "fallback" markup.
=================================  ================================================================  ========================================================

Please note the last example above, where the smartlink attempts to fail 'gracefully'. Unless you have specifically referred to the link in your text, very few readers will notice anything is missing. By adding a span with a distinctive class, you have the option to distinctively style these smartlinks. A common design pattern is to have a ``debug.css`` file which is only invoked in development mode.

Now let's add the crappy remake of this film to our database:

    >>> f2 = Film(title="The Wicker Man", slug="wicker-man-remake", year=2006)
    >>> f2.save()

Now we have two items which would match the smartlinks given above. In every case, the default HTML output would be::

    <span class="smartlinks-ambiguous">The Wicker Man</span>
    
In order to resolve this smartlink, you would need to add a disambiguator::

    [f[The Wicker Man]1973]]
    
would resolve to the original 1973 version::

    <a href="/films/wicker-man/">the Wicker Man</a>
    
while::

    [f[The Wicker Man]2006]]
    
returns a link to the crappy remake::

    <a href="/films/wicker-man-remake/">the Wicker Man</a>

As you can see, the disambiguator is generally not rendered in the output.

Now if we add another film::

    >>> f3 = Film(title="The Wicker Basket", slug="wicker-basket", year=2010)
    >>> f3.save()
    
Now our earlier markup: ``[f[The Wicker Basket]]`` will resolve to::

    <a href="/films/wicker-basket/">The Wicker Basket</a>
    
In this way, content editors can create "speculative" links to content which may be published at some future time.
    
More complex examples
^^^^^^^^^^^^^^^^^^^^^

By tweaking the configuration, we can create a smartlink that makes use of *options*. Options can be used in whatever way the model author sees fit::

    [f[The Wicker Man]2006|title=Read more about this awful film|class=crappy]
    
could render as::

    <a href="/films/wicker-man-remake/" title="Read more about this awful film" class="crappy">The Wicker Man</a>

Keyed smartlinks
^^^^^^^^^^^^^^^^

This is useful if you want to specify arbitrary linktext, or you are concerned that the contents of the matchfield might change at some future point in time - making the link unresolved. If a ``key`` is present in the smartlink, the linktext and disambiguator are not used for searching. The key is generally linked to an immutable field (commonly ``slug`` or even ``id``. For example::

    [f[The Wicker Man]1973], and its 2006 [f:wicker-man-remake[remake]] are both available on DVD.
    
would render as::

    <a href="/films/wicker-man/">The Wicker Man</a>, and its 2006 <a href="/films/wicker-man-remake/">remake</a> are both available on DVD.

.. highlight:: python

Installation
------------

To add smartlinks to your Django project:

Put the smartlinks app on your pythonpath
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Use your method of choice to install smartlinks. We recommend using `pip <http://pypi.python.org/pypi/pip>`_ with `virtualenv <http://pypi.python.org/pypi/virtualenv>`_::

    pip install glamkit-smartlinks

Add smartlinks to your INSTALLED_APPS
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

As with most Django applications, you should add 'smartlinks' to the INSTALLED_APPS within your settings file (usually settings.py).

Add a SMARTLINKS setting to your settings file
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The SMARTLINKS setting is a tuple of smartlinks definitions for each of the Django models you'd like to configure to work with smartlinks. If you're not yet ready to start configuring smartlinks, you can set SMARTLINKS to an empty tuple to avoid throwing an error::

    SMARTLINKS = ()


.. _smartlinks-config:

Configuration
-------------

Smartlinks settings variables
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

There are two methods to configure smartlinks. The simplest method involves adding a ``SMARTLINKS`` setting to your project. To get going quickly, you can copy smartlinks_conf.py_example to smartlinks_conf.py, modify it to meet your needs, then import it into your settings.py file.

This is what smartlinks_conf.py_example looks like out of the box::

    from smartlinks.search_types import SearchField, SearchType
    
    SMARTLINKS = (
        (('f', 'film',), 'collection.Film', {"search_field": SearchField("name"), "disambiguator": SearchField("year", SearchType.equals), 'key_field': SearchField("slug", SearchType.equals)}),
        (('v', 'venue',), 'locations.Venue', {"search_field": SearchField("name")}),
        (('', 'p', 'page'), "page.page", {"search_field": SearchField("title"), "disambiguator": SearchField("parent.title"), 'key_field': SearchField('id')}),
    )

The SMARTLINKS setting is a tuple of smartlinks rules. The syntax for each rule is ``((<tuple containing possible prefixes>), <path to the model, as in app_name.model_name>, <options>)``.

Observant readers will note that the first rule in the above config matches our description of the ``Film`` as described in :ref:`smartlinks-simple-examples` above.

This configuration method assumes that each model defined in SMARTLINKS has a corresponding url, which is specified either through ``get_absolute_url()``, or through a custom :ref:`smartlinks-hooks`.

Prefix defines which model will 'render' the smartlink. Prefixes can be repeated in multiple rules. This enables you to define more complex composite rules without resorting to hooks.

For example::

    SMARTLINKS = (
        (('', 'p', 'page'), "page.page", {"search_field": SearchField("title"), "disambiguator": SearchField("parent.title"), 'key_field': SearchField('id')}),
        (('', 'p', 'page'), "flatpages.FlatPage", {"search_field": SearchField("title"), "disambiguator": SearchField("slug"), 'key_field': SearchField('id')}),
    )

is a perfectly valid config.

The order of models specified in SMARTLINKS matters - it specifies in which order models will try to render a smartlink (i.e. if first model finds no match, second one tries to render it, etc.). This can be a way of defining a smartlinks scheme that does not require prefixes - simply specify multiple rules for the '' prefix, like so::

    SMARTLINKS = (
        (('',), "animals.Dog", {"search_field": SearchField("name")}),
        (('',), "animals.Cat", {"search_field": SearchField("name")}),
        (('',), "animals.Rabbit", {"search_field": SearchField("name")}),
    )

would allow you the link to dogs, cats and rabbits by name. If there is a dog named "Tibbles" and a cat with the same name, a link to Tibbles the dog would be returned, as this model will be searched first.

Options syntax
^^^^^^^^^^^^^^

Options are written as a dictionary containing the following self-explanatory attributes (all optional):

* "search_field"
* "disambiguator"
* "key_field"

Each attribute should be an instance of ``SearchField``, which takes two parameters - the field name, and the SearchType. There are three SearchTypes currently defined:

* SearchType.equals (the default)
* SearchType.icontains
* SearchType.iexact

.. _smartlinks-hooks:

Smartlinks hooks
^^^^^^^^^^^^^^^^

For more advanced configuration, you can add the following hooks to your models.

* 'get_from_smartlink' function in model manager - getting the instance. For example::
    
    def get_from_smartlink(self, link_text, disambiguator=None, key_term=None, arg=None):
        if key_term:
            return self.model.objects.get(pk=key_term)
        try:
            return self.model.objects.get(Q(title__iexact=link_text) | Q(_main_heading__iexact=link_text) | Q(_menu_name__iexact=link_text))
        except self.model.MultipleObjectsReturned:
            return self.model.objects.get(Q(title__iexact=link_text) | Q(_main_heading__iexact=link_text) | Q(_menu_name__iexact=link_text), Q(pk=disambiguator))
        
* 'smartlink_fallback' function in model manager - what happens when no corresponding entity is found::
    
    def smartlink_fallback(self, link_text, disambiguator=None, key_term=None, arg=None):
        return '<cite class="unresolved">%s</cite>' % link_text

* 'smartlink' function in model definition - how smartlink should be rendered. Options in the smartlink are passed as "args" and "kwargs". In case if it's not specified, a link to the model (with url from get_absolute_url) and a text inside a smartlink is generated::
    
    def smartlink(self, search_term, *args, **kwargs):
        return '<a href="/person/%s/">%s</a>' % (self.slug, search_term)
        
.. highlight:: html+django

The Templatetag
---------------

To render smartlinks within templates, use the 'smartlinks' filter:
    
(assuming the variable 'page.content' holds some smartlinkable text, like ``[person[Stanley Kubrick]] had a close working relationship with [p[Peter Sellers]1989], one of the finest character actors in modern cinema.``)::

    {% load smartlinks %}

    {{ page.content|smartlinks }}
    
In this example, assuming Person.objects.get(name="Stanley Kubrick") exists, but Person.objects.get(name="Peter Sellers", birth_year=1989) does not yet, this would produce::

    <a href="/person/stanley-kubrick/">Stanley Kubrick</a> had a close working relationship with <span class="smartlinks-unresolved">Peter Sellers</span>, one of the finest character actors in modern cinema.
    
As other markup systems (eg. Textile, MarkDown) tend to interfere with smartlinks markup, we advise placing the smartlinks filter before other markup filters::

    {{ page.content|smartlinks|textile }}

