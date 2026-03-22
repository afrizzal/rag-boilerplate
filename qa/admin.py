from django.contrib import admin
from .models import Question, Answer, RelevantChunk


class AnswerInline(admin.TabularInline):
    model = Answer
    fields = ['text', 'confidence_score', 'created_at']
    readonly_fields = ['text', 'confidence_score', 'created_at']
    extra = 0
    can_delete = False


class RelevantChunkInline(admin.TabularInline):
    model = RelevantChunk
    fields = ['chunk', 'similarity_score', 'rank']
    readonly_fields = ['chunk', 'similarity_score', 'rank']
    extra = 0
    can_delete = False


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['text_preview', 'created_at']
    search_fields = ['text']
    readonly_fields = ['id', 'created_at']
    inlines = [AnswerInline, RelevantChunkInline]

    def text_preview(self, obj):
        return obj.text[:80] + '...' if len(obj.text) > 80 else obj.text
    text_preview.short_description = 'Pertanyaan'


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ['question', 'text_preview', 'confidence_score', 'created_at']
    list_filter = ['created_at']
    readonly_fields = ['id', 'created_at']

    def text_preview(self, obj):
        return obj.text[:80] + '...' if len(obj.text) > 80 else obj.text
    text_preview.short_description = 'Jawaban'
