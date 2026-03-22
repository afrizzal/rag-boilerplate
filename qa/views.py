from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import Question
from .serializers import AskSerializer, QuestionHistorySerializer
from .services import ask_question


class AskView(APIView):
    """POST /api/qa/ask/ — ajukan pertanyaan ke chatbot RAG"""

    def post(self, request):
        serializer = AskSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        question_text = serializer.validated_data['question']

        try:
            result = ask_question(question_text)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {'error': f'Gagal memproses pertanyaan: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response(result, status=status.HTTP_200_OK)


class QuestionHistoryView(APIView):
    """GET /api/qa/history/ — riwayat pertanyaan dan jawaban"""

    def get(self, request):
        questions = Question.objects.prefetch_related('answer_set').order_by('-created_at')[:50]
        serializer = QuestionHistorySerializer(questions, many=True)
        return Response(serializer.data)
