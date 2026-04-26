from django.shortcuts import render
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from .serializers import CadastroSerializer

class CadastroView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = CadastroSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Usuário cadastrado com sucesso!"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

def hello_world(request):
    return HttpResponse("<h1>Psico+ Rodando!</h1>")

