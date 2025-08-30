from django.contrib import admin
from .models import Source, Tag, Quote, ModerationLog


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "status", "created_by", "created_at", "approved_by", "approved_at", "merged_into")
    list_filter = ("status",)
    search_fields = ("name", "name_normalized")


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    search_fields = ("name",)


@admin.register(Quote)
class QuoteAdmin(admin.ModelAdmin):
    list_display = ("id", "short_text", "source", "weight", "status", "likes", "views", "author", "created_at")
    list_filter = ("status", "source")
    search_fields = ("text",)
    autocomplete_fields = ("source", "tags")

    def short_text(self, obj):
        return (obj.text[:80] + "…") if len(obj.text) > 80 else obj.text


@admin.register(ModerationLog)
class ModerationLogAdmin(admin.ModelAdmin):
    list_display = ("id", "quote", "moderator", "action", "created_at")
    list_filter = ("action",)
