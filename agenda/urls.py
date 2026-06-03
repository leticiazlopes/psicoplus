from django.urls import path

from . import views

urlpatterns = [
    path("agenda/", views.agendamentos_view, name="agenda_lista"),
    path("agenda/editar/<uuid:sessao_id>/", views.editar_sessao_view, name="editar_sessao"),
    path("agenda/cancelar/<uuid:sessao_id>/", views.cancelar_sessao_view, name="cancelar_sessao"),
    path(
        "agenda/atualizar-status/<uuid:sessao_id>/", 
        views.atualizar_status_sessao, 
        name="atualizar_status_sessao"
    ),
    path('confirmar/<uuid:token>/', views.DetalheConfirmacaoPublicaView.as_view(), name='visualizar_confirmacao_publica'),
    path('sessao/<uuid:sessao_id>/confirmar/', views.confirmar_sessao_psicologo, name='confirmar_sessao_psicologo'),    path('api/sessoes/confirmar/<uuid:token>/', views.api_publica_confirmar, name='api_publica_confirmar'),
    path('agenda/enviar-confirmacao-email/<uuid:sessao_id>/', views.enviar_confirmacao_email, name='enviar_confirmacao_email'),
    path('agenda/api/status-sessoes/', views.api_status_sessoes, name='api_status_sessoes'),
    
]

