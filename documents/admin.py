from django.contrib import admin
from .models import Document, DocumentChunk


class DocumentChunkInline(admin.TabularInline):
    model = DocumentChunk
    fields = ['chunk_index', 'content', 'created_at']
    readonly_fields = ['chunk_index', 'content', 'created_at']
    extra = 0
    max_num = 10
    can_delete = False


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ['title', 'file_type', 'file_size', 'is_processed', 'chunk_count', 'uploaded_at']
    list_filter = ['is_processed', 'file_type']
    search_fields = ['title']
    readonly_fields = ['id', 'uploaded_at', 'processed_at']
    inlines = [DocumentChunkInline]

    def chunk_count(self, obj):
        return obj.chunks.count()
    chunk_count.short_description = 'Jumlah Chunk'


@admin.register(DocumentChunk)
class DocumentChunkAdmin(admin.ModelAdmin):
    list_display = ['document', 'chunk_index', 'content_preview', 'created_at']
    list_filter = ['document']
    search_fields = ['content', 'document__title']
    readonly_fields = ['id', 'created_at']

    def content_preview(self, obj):
        return obj.content[:80] + '...' if len(obj.content) > 80 else obj.content
    content_preview.short_description = 'Preview Konten'
