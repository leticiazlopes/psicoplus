from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import CadastroPsicologoSerializer, LoginSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken

class CadastroPsicologoView(APIView):
    permission_classes = []

    def post(self, request):
        serializer = CadastroPsicologoSerializer(data=request.data)

        if serializer.is_valid():
            usuario = serializer.save()
            return Response(
                {
                    "message": "Psicólogo cadastrado com sucesso.",
                    "usuario": {
                        "id": str(usuario.id),
                        "nome": usuario.nome,
                        "email": usuario.email,
                        "perfil": usuario.perfil,
                    },
                },
                status=status.HTTP_201_CREATED,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        return Response({
            "id": str(user.id),
            "nome": user.nome,
            "email": user.email,
            "perfil": user.perfil,
        })
    
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")

        if not refresh_token:
            return Response(
                {"detail": "Refresh token não enviado."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()

            return Response(
                {"message": "Logout realizado com sucesso."},
                status=status.HTTP_200_OK
            )

        except Exception:
            return Response(
                {"detail": "Token inválido ou já expirado."},
                status=status.HTTP_400_BAD_REQUEST
            )