from rest_framework import serializers
from .models import Question, Answer


class AskSerializer(serializers.Serializer):
    question = serializers.CharField(min_length=3, max_length=2000)


class AnswerSerializer(serializers.ModelSerializer):
    question_text = serializers.CharField(source='question.text', read_only=True)

    class Meta:
        model = Answer
        fields = ['id', 'question_text', 'text', 'confidence_score', 'created_at']


class QuestionHistorySerializer(serializers.ModelSerializer):
    answers = AnswerSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = ['id', 'text', 'created_at', 'answers']
