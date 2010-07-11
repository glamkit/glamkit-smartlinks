import unittest

from django.template import Template, Context, TemplateSyntaxError
from django.core.management import call_command
from django.db.models.loading import load_app

from smartlinks.search_types import SearchField, SearchType
from django.conf import settings

class SmartLinksTest(unittest.TestCase):
    def setUp(self):
        global smartlink, Person, Title, Clip, Dog, Cat
        
        self.old_INSTALLED_APPS = settings.INSTALLED_APPS
        settings.INSTALLED_APPS += ['smartlinks.tests.testapp']
        load_app('smartlinks.tests.testapp')
        
        call_command('flush', verbosity=0, interactive=False)
        call_command('syncdb', verbosity=0, interactive=False)
        
        from testapp.models import Person, Title, Clip, Dog, Cat
        
        settings.SMARTLINKS = (
            (('t', 'title',), "testapp.Title", {}),
            (('p', 'person',), "testapp.Person", {}),
            (('c', 'clip',), "testapp.Clip", {"allowed_embeds": {"keyframe": "get_keyframe", "video": "get_video"}}),
            (('d', 'dog',), "testapp.Dog", {'search_field': SearchField('name'),
                                            'disambiguator': SearchField('breed'),
                                            'key_field': SearchField('id')}),
            (('cat',), "testapp.Cat", {'search_field': SearchField('personality'),
                                            'disambiguator': SearchField('id'),
                                            'key_field': SearchField('name')}),
        )

        from smartlinks.templatetags.smartlinks import configure
        configure()

        template = Template("{% load smartlinks %}{{ dat|smartlinks }}")
        template_arg = Template("{% load smartlinks %}{{ dat|smartlinks:arg }}")

        def smartlink(text, obj=None):
            c = {"dat": text}
            if obj:
                c['arg'] = obj
                return template_arg.render(Context(c))
            return template.render(Context(c))
        
        p1 = Person.objects.create(name='Chips Rafferty')
        p2 = Person.objects.create(name='George Miller')
        p3 = Person.objects.create(name='George Miller')
        p4 = Person.objects.create(name='Sol Ipsist')

        t1 = Title.objects.create(name="Mad Max", year=1979, director=p2)
        t2 = Title.objects.create(name="On Our Selection", year=1920, director=p1)
        t3 = Title.objects.create(name="On Our Selection", year=1930, director=p3)
        t4 = Title.objects.create(name="Sol Ipsist", year=2009, director=p4)
        t5 = Title.objects.create(name="Far from home", year=1999, director=p4)


        d1 = Dog.objects.create(name="Spotty", breed='Dalmatian')
        d2 = Dog.objects.create(name="Fluffy", breed='Papillon')
        d2 = Dog.objects.create(name="Fluffy", breed='Pomeranian')
        d3 = Dog.objects.create(name="Stripy", breed='french bulldog')

        cat1 = Cat.objects.create(name='Ginger', personality='grouchy')
        cat2 = Cat.objects.create(name='Roamalot', personality='grumpy')
        cat3 = Cat.objects.create(name='Dane', personality='grumpy')
        cat4 = Cat.objects.create(name='Howard', personality='grouchy')

        Clip.objects.create(film=t1, number=1)
        Clip.objects.create(film=t1, number=2)
        Clip.objects.create(film=t3, number=1, keyframe='/media/img/img1.jpg')
        Clip.objects.create(film=t5, number=1, video='/media/video/video1.flv')
        Clip.objects.create(film=t1, number=437)
        
        self.ae = self.assertEquals # screw those javarians

    def tearDown(self):
        [c.delete() for c in Clip.objects.all()]
        [c.delete() for c in Title.objects.all()]
        [c.delete() for c in Person.objects.all()]
        settings.INSTALLED_APPS = self.old_INSTALLED_APPS
        from smartlinks.templatetags.smartlinks import configure
        configure()

    def testDumblinks(self):
        #No model = dumblink, and will search through models in some (what?) order. Where should this be defined?
        #Title
        self.ae(smartlink('[[Mad Max]]'), '<a href="/title/mad-max-1979/">Mad Max</a>')
        #Person
        self.ae(smartlink('[[Chips Rafferty]]'), '<a href="/person/chips-rafferty-1/" title="">Chips Rafferty</a>')
        #Ambiguous searches - is the best thing (for dumb users) to link to a search?
        self.ae(smartlink('[[On Our Selection]]'), '<span class="smartlinks-ambiguous">On Our Selection</span>')
        
        
        #Unambiguous Title
        self.ae(smartlink('[[On Our Selection]1920]'), '<a href="/title/on-our-selection-1920/">On Our Selection</a>')
        
        #Title trumps person. Strictly this should be ambiguous because there is both a film and a person. But that would involve quering on every model for each dumbtag... is it really necessary?
        self.ae(smartlink('[[Sol Ipsist]]'), '<a href="/title/sol-ipsist-2009/">Sol Ipsist</a>')
        
        
    def testDisambiguators(self):
        #Specify unambiguous title. Alternative model selector
        self.ae(smartlink('[title[Mad Max]]'), '<a href="/title/mad-max-1979/">Mad Max</a>')

        # unambiguous dog
        self.ae(smartlink('[d[Spotty]]'), '<a href="/dog/Spotty/">Spotty</a>')
        #disambiguator should be ignored
        self.ae(smartlink('[d[Spotty]doesnotmatter]'), '<a href="/dog/Spotty/">Spotty</a>')
        #disambiguator should NOT be ignored (wrong disambiguator, so result is unresolved)
        self.ae(smartlink('[d[Fluffy]thismatters]'), '<span class="smartlinks-unresolved">Fluffy</span>')
        #correct disambiguator
        self.ae(smartlink('[d[Fluffy]papillon]'), '<a href="/dog/Fluffy/">Fluffy</a>')
        
        """
        so we are allowing spaces inside ~smart~ links and disallowing them inside dumblinks? 
        that's quite counter-intuitive
        #Optional disambiguator. Trailing spaces in model choice and spaces on both sides of suffix are trimmed.
        """
        self.ae(smartlink('[t    [Mad Max]   1979     ]'), '<a href="/title/mad-max-1979/">Mad Max</a>')
    
        #Incorrect disambiguator/year - unresolved
        self.ae(smartlink('[t[Mad Max]1949]'), '<span class="smartlinks-unresolved">Mad Max</span>')

        #Ambiguous Title
        self.ae(smartlink('[t[On Our Selection]]'), '<span class="smartlinks-ambiguous">On Our Selection</span>')
        #Disambiguator
        self.ae(smartlink('[t[On Our Selection]1920]'), '<a href="/title/on-our-selection-1920/">On Our Selection</a>') #not sure how ASO does disambiguation in URLs, but it can be defined in the actual Title.smartlink function
        
        #Other disambiguator
        self.ae(smartlink('[t[On Our Selection]1930]'), '<a href="/title/on-our-selection-1930/">On Our Selection</a>')
        
    def testSmartness(self):
        
        #Other disambiguator in link text
        self.ae(smartlink('[t[On Our Selection (1930)]]'), '<a href="/title/on-our-selection-1930/">On Our Selection (1930)</a>')
        self.ae(smartlink('[t[Mad Max (1949)]]'), '<span class="smartlinks-unresolved">Mad Max (1949)</span>')
        #Can't do this (only because it's not set up to happen with Persons)
        self.ae(smartlink('[p[George Miller (1)]]'), '<span class="smartlinks-unresolved">George Miller (1)</span>')
        
        #But spaces at the edge are NOT significant
        self.ae(smartlink('[t[ Mad Max (1979)]]'), '<a href="/title/mad-max-1979/">Mad Max (1979)</a>')
        self.ae(smartlink('[t[Mad Max (1979) ]]'), '<a href="/title/mad-max-1979/">Mad Max (1979)</a>')
        self.ae(smartlink('[t[    Mad Max (1979)    ]]'), '<a href="/title/mad-max-1979/">Mad Max (1979)</a>')
        #Optional year - works like disambiguator, but appears in link text
        self.ae(smartlink('[t[Mad Max (1979)]]'), '<a href="/title/mad-max-1979/">Mad Max (1979)</a>')
        self.ae(smartlink('[[On Our Selection (1920)]]'), '<a href="/title/on-our-selection-1920/">On Our Selection (1920)</a>')
        
    def testCaseInsensitivity(self):
        #Person. Case insensitive.
        self.ae(smartlink('[pErSoN[cHiPs RaFfErTy]]'), '<a href="/person/chips-rafferty-1/" title="">cHiPs RaFfErTy</a>') 

        #Specifying the wrong model fails.
        self.ae(smartlink('[t[Chips Rafferty]]'), '<span class="smartlinks-unresolved">Chips Rafferty</span>')
        
        
        #Specifying a model that doesn't exist returns identity - in case the user is doing something else.
        self.ae(smartlink('[x[Chips Rafferty]]'), "[x[Chips Rafferty]]")

        #(Probably redundant) Check that appropriate link is returned
        self.ae(smartlink('[p[Sol Ipsist]]'), '<a href="/person/sol-ipsist-1/" title="">Sol Ipsist</a>')
        self.ae(smartlink('[t[Sol Ipsist]]'), '<a href="/title/sol-ipsist-2009/">Sol Ipsist</a>')

        #Searches that don't match anything are unresolved
        self.ae(smartlink('[t[Foo]]'), '<span class="smartlinks-unresolved">Foo</span>')
        self.ae(smartlink('[t[Foo]Bar]'), '<span class="smartlinks-unresolved">Foo</span>')

        #Searches that match more than one thing are ambiguous
        self.ae(smartlink('[p[George Miller]]'), '<span class="smartlinks-ambiguous">George Miller</span>')

        #Options are ignored when result is ambiguous
        self.ae(smartlink('[p[George Miller]|the man]'), '<span class="smartlinks-ambiguous">George Miller</span>')

        #Unambiguous person
        self.ae(smartlink('[p[George Miller]1]'), '<a href="/person/george-miller-1/" title="">George Miller</a>')
        
        #Disambiguated, with options
        self.ae(smartlink('[p[George Miller]1|the man]'), '<a href="/person/george-miller-1/" title="the man">George Miller</a>')
        self.ae(smartlink('[p[George Miller]1|the man|class=vip]'), '<a href="/person/george-miller-1/" title="the man" class="vip">George Miller</a>')
        self.ae(smartlink('[p[George Miller]1|title=the man|class=vip]'), '<a href="/person/george-miller-1/" title="the man" class="vip">George Miller</a>')

        #Person.smartlink declares kwargs and ignores anything it doesn't know about
        self.ae(smartlink('[p[George Miller]1|title=the man|class=vip|extraneous=foo]'), '<a href="/person/george-miller-1/" title="the man" class="vip">George Miller</a>')


        #specify clip number. can use 'from' or 'of'
        self.ae(smartlink('[clip[Clip 1 from Mad Max]]'), '<a href="/title/mad-max-1979/clip/1/">Clip 1 from Mad Max</a>')
        self.ae(smartlink('[cLiP[Clip 2 of Mad Max]]'), '<a href="/title/mad-max-1979/clip/2/">Clip 2 of Mad Max</a>')

        #can spell numbers
        self.ae(smartlink('[c[Clip one from Mad Max]]'), '<a href="/title/mad-max-1979/clip/1/">Clip one from Mad Max</a>')
        #really? (don't worry, it's irrelevant for the generic smartlinks API)
        self.ae(smartlink('[c[Clip four hundred and thirty seven from Mad Max]]'), '<a href="/title/mad-max-1979/clip/437/">Clip four hundred and thirty seven from Mad Max</a>')
        self.ae(smartlink('[c[Clip four hundred thirty-seven from Mad Max]]'), '<a href="/title/mad-max-1979/clip/437/">Clip four hundred thirty-seven from Mad Max</a>')

        # Clip.smartlink doesn't define *args and **kwargs, so we should get an error if options are specified
        try:
            smartlink('[c[Clip four hundred thirty-seven from Mad Max]|resolution=low]')
            self.ae(1, 0, "expecting exception but none caught")
        except TemplateSyntaxError, e:
            # this is how django's template system formats its exception message (subject to change!)
            self.ae(str(e), "Caught TypeError while rendering: smartlink() got an unexpected keyword argument 'resolution'",
                    "wrong exception caught? e.message = %s" % str(e))


    def testFailing(self):
        #these should fail silently
        self.ae(smartlink('[c[Clip 9 from Mad Max]]'), '<cite class="unresolved">Clip 9 from Mad Max</cite>')
        self.ae(smartlink('[c[Clip one dozen of Mad Max]]'), '<cite class="unresolved">Clip one dozen of Mad Max</cite>')
        self.ae(smartlink('[c[Clip 2 dozen and 8 from Mad Max]]'), '<cite class="unresolved">Clip 2 dozen and 8 from Mad Max</cite>')
        self.ae(smartlink('[c[Clip round the ear from Mad Max]]'), '<cite class="unresolved">Clip round the ear from Mad Max</cite>')

        # invalid titles fail silently
        self.ae(smartlink('[c[Clip 1 from Foo]]'), '<cite class="unresolved">Clip 1 from Foo</cite>')

        # ambiguous titles fail silently (but gets a span instead of cite because we don't have a callback for rendering ambiguous links)
        self.ae(smartlink('[c[Clip 1 from On Our Selection]]'), '<span class="smartlinks-ambiguous">Clip 1 from On Our Selection</span>')
        # unambiguous titles do not fail
        self.ae(smartlink('[c[Clip 1 from On Our Selection (1930)]]'), '<a href="/title/on-our-selection-1930/clip/1/">Clip 1 from On Our Selection (1930)</a>')
        self.ae(smartlink('[c[Clip 1 from On Our Selection]1930]'), '<a href="/title/on-our-selection-1930/clip/1/">Clip 1 from On Our Selection</a>') #necessary?
        # unless the disambiguator is incorrect
        self.ae(smartlink('[c[Clip 1 from On Our Selection]1929]'), '<cite class="unresolved">Clip 1 from On Our Selection</cite>')

        # 'from/of' in movie titles are OK.
        self.ae(smartlink('[c[Clip 1 from Far from home]]'), '<a href="/title/far-from-home-1999/clip/1/">Clip 1 from Far from home</a>')

    def testContext(self):
        #Links can vary with context (how to implement?)
        self.ae(smartlink('[c[clip one]]', obj=Title.objects.get_from_smartlink("mad max")), '<a href="/title/mad-max-1979/clip/1/">clip one</a>') #in /title/mad-max/
        self.ae(smartlink('[c[clip one]]', obj=Title.objects.get_from_smartlink("far from home")), '<a href="/title/far-from-home-1999/clip/1/">clip one</a>') #in /title/far-from-home/
        self.ae(smartlink('[c[clip one]]', obj=Person.objects.get_from_smartlink("george miller", disambiguator=1)), '<cite class="unresolved">clip one</cite>') #in /person/george-miller-1/


        

    def testEscaping(self):
        #it is possible to put smartlinks inside square brackets

        self.ae(smartlink('[[t[Mad Max]]]'), '[<a href="/title/mad-max-1979/">Mad Max</a>]')
        
        # smartlinks can be escaped by specifying a slash in front of the
        # link
        self.ae(smartlink('\[[Mad Max]]'), r'\[[Mad Max]]')
        
        #These are not smartlinks, and shouldn't reach the link parser.
        #mismatched brackets
        self.ae(smartlink('[[Mad Max]'), '[[Mad Max]')
        self.ae(smartlink('[Mad Max]]'), '[Mad Max]]')
        self.ae(smartlink('[t[Mad Max]') , '[t[Mad Max]')
        
        #no spaces allowed in opening brackets
        self.ae(smartlink('[ [Mad Max]]'), '[ [Mad Max]]')
        self.ae(smartlink('[ t[Mad Max]]'), '[ t[Mad Max]]')
        self.ae(smartlink('[ t [Mad Max]]'), '[ t [Mad Max]]')
        self.ae(smartlink('[t t[Mad Max]]'), '[t t[Mad Max]]')

        #but what about spaces in suffix?
        self.ae(smartlink('[t [Mad Max]]'), '<a href="/title/mad-max-1979/">Mad Max</a>')
        self.ae(smartlink('[t [Mad Max] 1979]'), '<a href="/title/mad-max-1979/">Mad Max</a>')
        self.ae(smartlink('[t [Mad Max] 1979 ]'), '<a href="/title/mad-max-1979/">Mad Max</a>')
        self.ae(smartlink('[t [Mad Max]   1979   ]'), '<a href="/title/mad-max-1979/">Mad Max</a>')


    def testKeyField(self):
        global Dog, Cat
        spotty = Dog.objects.get(name='Spotty')
        roamalot = Cat.objects.get(name='Roamalot')

        # spotty can be linked
        self.ae(smartlink('[d[Spotty]]'), '<a href="/dog/Spotty/">Spotty</a>')
        self.ae(smartlink('[d:%d[Spotty]]' % spotty.id), '<a href="/dog/Spotty/">Spotty</a>')
        #self.ae(smartlink('[d1:Spotty[Spotty]]'), '<a href="/dog/Spotty/">Spotty</a>')

        # empty key term, as if it didn't exist
        self.ae(smartlink('[d:[Spotty]]'), '<a href="/dog/Spotty/">Spotty</a>')

        # space not allowed before ":"
        self.ae(smartlink('[d :[Spotty]]'), '[d :[Spotty]]')
        self.ae(smartlink('[d:   %d[Spotty]]' % spotty.id), '<a href="/dog/Spotty/">Spotty</a>')
        self.ae(smartlink('[d:   %d    [Spotty]]' % spotty.id), '<a href="/dog/Spotty/">Spotty</a>')

        # change name temporarily
        spotty.name = 'Spottified'
        spotty.save()

        # cannot be linked anymore (without key_field)
        self.ae(smartlink('[d[Spotty]]'), '<span class="smartlinks-unresolved">Spotty</span>')

        # with key_field, still works (with url changed)
        self.ae(smartlink('[d:%d[Spotty]]' % spotty.id), '<a href="/dog/Spottified/">Spotty</a>')

        # revert
        spotty.name = 'Spotty'
        spotty.save()

        # found again
        self.ae(smartlink('[d[Spotty]]'), '<a href="/dog/Spotty/">Spotty</a>')
        # url back to /dog/Spotty
        self.ae(smartlink('[d:%d[Spotty]]' % spotty.id), '<a href="/dog/Spotty/">Spotty</a>')


        # try with cats
        self.ae(smartlink('[cat[grumpy]]'), '<span class="smartlinks-ambiguous">grumpy</span>')
        # how do I zoom in on a cat? well, there's the traditional disambiguator
        self.ae(smartlink('[cat[grumpy]%d]' % roamalot.id), '<a href="/cat/grumpy-Roamalot/">grumpy</a>')
        ### what if I wanted to change the link text?

        # oops! does not work with disambiguator
        self.ae(smartlink('[cat[one grumpy cat]%d]' % roamalot.id), '<span class="smartlinks-unresolved">one grumpy cat</span>')
        # you need the key_field
        self.ae(smartlink('[cat:roamalot[one grumpy cat]]'), '<a href="/cat/grumpy-Roamalot/">one grumpy cat</a>')
        # once key_field is set and found, the search_field is used for link text, and disambiguator is ignored
        self.ae(smartlink('[cat:roamalot[grumpy cat]dummy]'), '<a href="/cat/grumpy-Roamalot/">grumpy cat</a>')
        # but if key_field is not found, behave as if key_field was not there
        self.ae(smartlink('[cat:nosuchcat[grumpy cat]dummy]'), '<span class="smartlinks-unresolved">grumpy cat</span>')
        self.ae(smartlink('[cat:nosuchcat[grumpy]dummy]'), '<span class="smartlinks-unresolved">grumpy</span>')
        self.ae(smartlink('[cat:nosuchcat[grumpy]]'), '<span class="smartlinks-ambiguous">grumpy</span>')
        self.ae(smartlink('[cat:nosuchcat[grumpy]%d]' % roamalot.id), '<a href="/cat/grumpy-Roamalot/">grumpy</a>')

        self.ae(smartlink('[cat:roamalot[one grumpy cat]]'), '<a href="/cat/grumpy-Roamalot/">one grumpy cat</a>')

        self.ae(smartlink('[cat:ginger[my cat]]'), '<a href="/cat/grouchy-Ginger/">my cat</a>')



    def testSpaces(self):
        #Spaces inside link text ARE significant (by default)
        self.ae(smartlink('[t[Mad Max(1979)]]'), '<a href="/title/mad-max-1979/">Mad Max(1979)</a>')
        self.ae(smartlink('[t[Mad Max (1979 )]]'), '<a href="/title/mad-max-1979/">Mad Max (1979 )</a>')
        self.ae(smartlink('[t[Mad Max  (1979)]]'), '<a href="/title/mad-max-1979/">Mad Max  (1979)</a>')
        self.ae(smartlink('[t[Mad  Max (1979)]]'), '<span class="smartlinks-unresolved">Mad  Max (1979)</span>')
        
        #this doesn't resolve, but would if '19 30' was a disambiguator.
        self.ae(smartlink('[c[Clip 1 from On Our Selection]19 30 ]'), '<cite class="unresolved">Clip 1 from On Our Selection</cite>')

        #too many interior brackets
        # [[t[dfgdfg]]] - is it a dumblink with a context "[t[dfgdfg]]" or a smartlink surrounded by square brackets?
        # Don't know, so return original.
        self.ae(smartlink('[t[[Mad Max]]]'), '[t<a href="/title/mad-max-1979/">Mad Max</a>]')
    
    def testNotSmartlinks(self):
        #Specifying nothing returns identity (or doesn't reach the parser).
        self.ae(smartlink('[[]]'), "[[]]")
        self.ae(smartlink('[title[]]'), "[title[]]")
        self.ae(smartlink('[t[]1920]'), "[t[]1920]")
        
    def testSmartEmbeds(self):
        self.ae(smartlink('{c.keyframe{on-our-selection-1930}1}'), '<img src="/media/img/img1.jpg" alt="" />')
        self.ae(smartlink('{c.keyframe{on-our-selection-1930}1|alt=On Our Selection (1930)}'),
                          '<img src="/media/img/img1.jpg" alt="On Our Selection (1930)" />')
        self.ae(smartlink('{c.keyframe     {on-our-selection-1930}1}'), '<img src="/media/img/img1.jpg" alt="" />')
        self.ae(smartlink('{c.video{far-from-home-1999}1}'), '<embed type="video">/media/video/video1.flv</embed>')
        self.ae(smartlink('{c.keyframe{mad-max-1979}100}'), '')
