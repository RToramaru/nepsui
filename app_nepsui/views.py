from django.shortcuts import render
import pandas as pd
from django.http import JsonResponse
import numpy as np
from app_nepsui.models import ArquivoExcel


def index(request):
    return render(request, 'index.html')


def visualizar(request):
    if request.method == 'POST' and request.FILES['fileInput']:
        arquivo_enviado = request.FILES['fileInput']
        obj, created = ArquivoExcel.objects.get_or_create(id=1)
        if not created and obj.arquivo:
            obj.arquivo.delete()
        obj.arquivo.save(arquivo_enviado.name, arquivo_enviado, save=True)

        excel_file = pd.ExcelFile(arquivo_enviado)
        nomes_das_abas = excel_file.sheet_names

        return render(request, 'visualizar.html', {'nomes_das_abas': nomes_das_abas, 'excel_file': excel_file})


def obter_datas_min_max(request):
    if request.method == 'POST':
        obj = ArquivoExcel.objects.get(id=1)
        excel_file = pd.ExcelFile(obj.arquivo)
        aba_selecionada = request.POST.get('aba')

        aba = excel_file.parse(sheet_name=aba_selecionada)
        aba = aba.dropna()
        aba['Horário'] = pd.to_datetime(aba['Horário']).dt.strftime('%Y-%m-%d')

        menor_data = aba['Horário'].min()
        maior_data = aba['Horário'].max()

        return JsonResponse({'min_data': menor_data, 'max_data': maior_data})
    return JsonResponse({'Error': "Erro"})
       

def visualizar_grafico(request):
    if request.method == 'POST':
        data_inicio = request.POST.get('dataInicio')
        data_fim = request.POST.get('dataFim')

        quantidade_de_leitoes = int(request.POST.get('quantidadeLeitoes'))

        obj = ArquivoExcel.objects.get(id=1)
        excel_file = pd.ExcelFile(obj.arquivo)
        aba_selecionada = request.POST.get('aba')

        aba = excel_file.parse(sheet_name=aba_selecionada)
        aba = aba.dropna()
        aba['Horário'] = pd.to_datetime(aba['Horário']).dt.strftime('%Y-%m-%d')

        aba_filtrada = aba[(aba['Horário'] >= data_inicio) & (aba['Horário'] <= data_fim)]
        
        primeiro_quartil = aba_filtrada['Peso'].quantile(0.25)
        terceiro_quartil = aba_filtrada['Peso'].quantile(0.75)

        limite_inferior = primeiro_quartil - 1.5 * (terceiro_quartil - primeiro_quartil)
        limite_superior = terceiro_quartil + 1.5 * (terceiro_quartil - primeiro_quartil)

        aba_filtrada = aba_filtrada[(aba_filtrada['Peso'] >= limite_inferior) & (aba_filtrada['Peso'] <= limite_superior)]

        dados_agrupados = aba_filtrada.groupby('Horário')
        
        peso_porca = []
        peso_leitoes = []
        for grupo, dados_do_grupo in dados_agrupados:
            if len(dados_do_grupo) > quantidade_de_leitoes + 1:
                pesos = dados_do_grupo['Peso'].values
                histograma, beans = np.histogram(pesos, bins=quantidade_de_leitoes + 1)
                peso_porca.append(beans[0])
                peso_leitoes.append(beans[-1] - beans[0])
    peso_porca_int = [int(x) for x in peso_porca]
    peso_leitoes_int = [int(x) for x in peso_leitoes]

    return JsonResponse({'pesoPorca': peso_porca_int, 'pesoLeitoes': peso_leitoes_int, 'dataInicio': data_inicio, 'dataFim': data_fim})