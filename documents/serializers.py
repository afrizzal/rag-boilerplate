from rest_framework import serializers
from .models import Document, DocumentChunk


class DocumentChunkSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentChunk
        fields = ['id', 'chunk_index', 'content', 'created_at']


class DocumentSerializer(serializers.ModelSerializer):
    chunk_count = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            'id', 'title', 'file_type', 'file_size',
            'is_processed', 'uploaded_at', 'processed_at', 'chunk_count'
        ]

    def get_chunk_count(self, obj):
        return obj.chunks.count()


class DocumentUploadSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255, required=False)
    file = serializers.FileField()

    def validate_file(self, value):
        allowed_types = ['pdf', 'txt', 'docx', 'doc']
        ext = value.name.split('.')[-1].lower()
        if ext not in allowed_types:
            raise serializers.ValidationError(
                f"Format file tidak didukung. Gunakan: {', '.join(allowed_types)}"
            )
        return value
