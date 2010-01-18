from django.template import Template, Context

template = Template("{% load smartlinks %}{{ text|smartlinks }}")

def render_smartlink(text):
    return template.render(Context(locals()))
    