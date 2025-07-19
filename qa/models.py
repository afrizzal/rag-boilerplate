from django.db import models
from documents.models import DocumentChunk
import uuid

# Create your models here.

class Question(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    text = models.TextField()
    embedding = models.JSONField(null=True, blank=True)  # vector embedding
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Q: {self.text[:50]}..."

class Answer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    text = models.TextField()
    confidence_score = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"A: {self.text[:50]}..."

class RelevantChunk(models.Model):
    """Chunk yang relevan dengan pertanyaan"""
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    chunk = models.ForeignKey(DocumentChunk, on_delete=models.CASCADE)
    similarity_score = models.FloatField()  # cosine similarity score
    rank = models.IntegerField()  # ranking dalam hasil retrieval
    
    class Meta:
        unique_together = ['question', 'chunk']
        ordering = ['rank']
    
    def __str__(self):
        return f"Chunk for Q: {self.question.text[:30]}... (Score: {self.similarity_score:.2f})"
