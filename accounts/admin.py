from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario

class UsuarioAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Informações profissionais', {'fields': ('nome', 'crp', 'perfil')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Informações profissionais', {'fields': ('nome', 'crp', 'perfil')}),
    )
    list_display = ('email', 'nome', 'perfil', 'is_staff')
    
admin.site.register(Usuario, UsuarioAdmin)

