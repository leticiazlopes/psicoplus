from rest_framework import serializers
from .models import Usuario

class CadastroSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = Usuario
        fields = ['id', 'nome', 'email', 'crp', 'perfil', 'password']

    def create(self, validated_data):
        user = Usuario.objects.create_user(
            username=validated_data['email'], 
            email=validated_data['email'],
            password=validated_data['password'],
            nome=validated_data['nome'],
            crp=validated_data.get('crp'), 
            perfil=validated_data['perfil']
        )
        return user