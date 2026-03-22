from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import Document
from .serializers import DocumentSerializer, DocumentUploadSerializer
from .services import process_document


class DocumentListView(APIView):
    """GET /api/documents/ — daftar semua dokumen"""

    def get(self, request):
        documents = Document.objects.all().order_by('-uploaded_at')
        serializer = DocumentSerializer(documents, many=True)
        return Response(serializer.data)


class DocumentUploadView(APIView):
    """POST /api/documents/upload/ — upload dan proses dokumen baru"""

    def post(self, request):
        serializer = DocumentUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        file = serializer.validated_data['file']
        file_type = file.name.split('.')[-1].lower()
        title = serializer.validated_data.get('title') or file.name

        document = Document.objects.create(
            title=title,
            content='',
            file_type=file_type,
            file_size=file.size,
        )

        try:
            process_document(document, file)
        except ValueError as e:
            document.delete()
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            document.delete()
            return Response(
                {'error': f'Gagal memproses dokumen: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response(
            {
                'message': 'Dokumen berhasil diupload dan diproses.',
                'document': DocumentSerializer(document).data,
            },
            status=status.HTTP_201_CREATED
        )


class DocumentDetailView(APIView):
    """GET /api/documents/<id>/ — detail dokumen"""

    def get(self, request, pk):
        try:
            document = Document.objects.get(pk=pk)
        except Document.DoesNotExist:
            return Response({'error': 'Dokumen tidak ditemukan.'}, status=status.HTTP_404_NOT_FOUND)

        return Response(DocumentSerializer(document).data)

    def delete(self, request, pk):
        try:
            document = Document.objects.get(pk=pk)
        except Document.DoesNotExist:
            return Response({'error': 'Dokumen tidak ditemukan.'}, status=status.HTTP_404_NOT_FOUND)

        document.delete()
        return Response({'message': 'Dokumen berhasil dihapus.'}, status=status.HTTP_200_OK)
