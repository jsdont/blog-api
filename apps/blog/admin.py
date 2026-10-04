from django.contrib import admin

from apps.blog.models import Category, Comment, Post, Tag

admin.site.register((Category, Tag, Post, Comment))
