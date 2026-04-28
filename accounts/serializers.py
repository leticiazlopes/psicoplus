from rest_framework import serializers
from django.db import transaction
from .models import Usuario, Psicologo
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer



class CadastroPsicologoSerializer(serializers.Serializer):
    nome = serializers.CharField(max_length=255)
    email = serializers.EmailField()
    senha = serializers.CharField(write_only=True, min_length=8)
    crp = serializers.CharField(max_length=20)
    telefone = serializers.CharField(max_length=20, required=False, allow_blank=True)

    def validate_email(self, value):
        if Usuario.objects.filter(email=value).exists():
            raise serializers.ValidationError("Já existe um usuário com este e-mail.")
        return value

    def validate_crp(self, value):
        if Psicologo.objects.filter(crp=value).exists():
            raise serializers.ValidationError("Já existe um psicólogo com este CRP.")
        return value

    @transaction.atomic
    def create(self, validated_data):
        senha = validated_data.pop("senha")
        crp = validated_data.pop("crp")
        telefone = validated_data.pop("telefone", "")

        usuario = Usuario.objects.create_user(
            email=validated_data["email"],
            username=validated_data["email"],
            nome=validated_data["nome"],
            perfil=Usuario.Perfil.PSICOLOGO,
            password=senha,
        )

        Psicologo.objects.create(
            usuario=usuario,
            crp=crp,
            telefone=telefone,
        )

        return usuario

class LoginSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        token["id"] = str(user.id)
        token["nome"] = user.nome
        token["email"] = user.email
        token["perfil"] = user.perfil

        return token

    def validate(self, attrs):
        data = super().validate(attrs)

        data["usuario"] = {
            "id": str(self.user.id),
            "nome": self.user.nome,
            "email": self.user.email,
            "perfil": self.user.perfil,
        }

        return data