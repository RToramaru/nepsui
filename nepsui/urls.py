from django.urls import path

from app_nepsui import views

urlpatterns = [
    # rota, view responsavel, nome de referencia
    path('', views.index, name='index'),
    path('visualizar/', views.visualizar, name='visualizar'),
    path('obter_datas_min_max/', views.obter_datas_min_max, name='obter_datas_min_max'),
    path('visualizar_grafico/', views.visualizar_grafico, name='visualizar_grafico'),
]
