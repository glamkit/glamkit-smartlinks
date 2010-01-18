from django.contrib import admin

from myapp.models import *

class PersonOptions(admin.ModelAdmin):
    pass

class TitleOptions(admin.ModelAdmin):
    pass

class ClipOptions(admin.ModelAdmin):
    pass

class PostOptions(admin.ModelAdmin):
    list_display = ("content", "posted", "importance", )

admin.site.register(Person, PersonOptions)
admin.site.register(Title, TitleOptions)
admin.site.register(Clip, ClipOptions)
admin.site.register(Post, PostOptions)