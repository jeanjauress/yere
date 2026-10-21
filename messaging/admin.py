from django.contrib import admin

from .models import Block, Conversation


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    # Le contenu des messages reste privé : seules les métadonnées sont visibles.
    list_display = ("id", "buyer", "seller", "listing", "updated_at")
    raw_id_fields = ("buyer", "seller", "listing")


@admin.register(Block)
class BlockAdmin(admin.ModelAdmin):
    list_display = ("blocker", "blocked", "created_at")
