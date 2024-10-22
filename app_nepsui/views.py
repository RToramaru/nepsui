from django.shortcuts import render
import pandas as pd
from django.http import JsonResponse
import numpy as np
import base64
from io import BytesIO
from django.conf import settings
import os


def index(request):
    return render(request, 'index.html')


def visualizar(request):
    if request.method == 'POST' and request.FILES['fileInput']:
        arquivo_enviado = request.FILES['fileInput']

        # Usando BytesIO para ler o arquivo em memória
        with BytesIO(arquivo_enviado.read()) as excel_io:
            excel_file = pd.ExcelFile(excel_io)
            nomes_das_abas = excel_file.sheet_names

            # Convertendo para base64 antes de armazenar na sessão
            excel_data_base64 = base64.b64encode(excel_io.getvalue()).decode('utf-8')
            request.session['excel_data'] = excel_data_base64

        return render(request, 'visualizar.html', {'nomes_das_abas': nomes_das_abas, 'excel_file': excel_file})


def obter_datas_min_max(request):
    if request.method == 'POST':
        aba_selecionada = request.POST.get('aba')

        # Recuperando e decodificando o conteúdo do arquivo da sessão
        arquivo_data_base64 = request.session.get('excel_data')

        if arquivo_data_base64:
            arquivo_data = base64.b64decode(arquivo_data_base64)
            with BytesIO(arquivo_data) as arquivo_io:
                excel_file = pd.ExcelFile(arquivo_io)
                aba = excel_file.parse(sheet_name=aba_selecionada)
                aba = aba.dropna()

                aba['data-servico'] = pd.to_datetime(aba.iloc[:, 0], dayfirst=True).dt.strftime('%Y-%m-%d')

                menor_data = aba['data-servico'].min()
                maior_data = aba['data-servico'].max()

                return JsonResponse({'min_data': menor_data, 'max_data': maior_data})

    return JsonResponse({'Error': "Erro"})


def visualizar_grafico(request):
    if request.method == 'POST':
        data_inicio = request.POST.get('dataInicio')
        data_fim = request.POST.get('dataFim')
        data_parto = request.POST.get('dataParto')  # Data em que pariu
        quantidade_de_leitoes = int(request.POST.get('quantidadeLeitoes'))
        gerar_planilha = request.POST.get('gerarPlanilha') == 'true'
        aba_selecionada = request.POST.get('aba')

        # Conversão das datas para objetos datetime
        data_inicio_dt = pd.to_datetime(data_inicio)
        data_fim_dt = pd.to_datetime(data_fim)
        data_parto_dt = pd.to_datetime(data_parto)

        # Recuperando e decodificando o conteúdo do arquivo Excel armazenado na sessão
        arquivo_data_base64 = request.session.get('excel_data')

        if not arquivo_data_base64:
            return JsonResponse({'Error': "Arquivo Excel não encontrado na sessão"}, status=400)

        arquivo_data = base64.b64decode(arquivo_data_base64)

        with BytesIO(arquivo_data) as arquivo_io:
            excel_file = pd.ExcelFile(arquivo_io)
            aba = excel_file.parse(sheet_name=aba_selecionada)
            aba = aba.dropna()

            # Convertendo as datas e horas
            aba['data-servico'] = pd.to_datetime(aba.iloc[:, 0], dayfirst=True).dt.strftime('%Y-%m-%d')
            aba['hora-servico'] = aba.iloc[:, 1].astype(str)
            aba['horario-servico'] = pd.to_datetime(aba['data-servico'].astype(str) + ' ' + aba['hora-servico'],
                                                    format='%Y-%m-%d %H:%M:%S')

            # Filtrando por intervalo de datas
            aba_filtrada = aba[(aba['horario-servico'] >= data_inicio) & (aba['horario-servico'] <= data_fim)]

            # Dividindo os dados em antes e depois da data de parto
            aba_before_parto = aba_filtrada[aba_filtrada['horario-servico'] < data_parto_dt]
            aba_after_parto = aba_filtrada[aba_filtrada['horario-servico'] >= data_parto_dt]

            # Ajuste para agrupamento por hora ou dia
            if data_fim_dt - data_inicio_dt <= pd.Timedelta(days=1):
                aba_filtrada['horario-servico'] = aba_filtrada['horario-servico'].dt.floor('H')
                aba_before_parto['horario-servico'] = aba_before_parto['horario-servico'].dt.floor('H')
                aba_after_parto['horario-servico'] = aba_after_parto['horario-servico'].dt.floor('H')
            else:
                aba_filtrada['horario-servico'] = aba_filtrada['horario-servico'].dt.date
                aba_before_parto['horario-servico'] = aba_before_parto['horario-servico'].dt.date
                aba_after_parto['horario-servico'] = aba_after_parto['horario-servico'].dt.date

            # Cálculo dos quartis e filtragem apenas para dados após o parto
            if not aba_after_parto.empty:
                primeiro_quartil = aba_after_parto.iloc[:, 2].quantile(0.25)
                terceiro_quartil = aba_after_parto.iloc[:, 2].quantile(0.60)
                limite_inferior = primeiro_quartil - 1.5 * (terceiro_quartil - primeiro_quartil)
                limite_superior = terceiro_quartil + 1.5 * (terceiro_quartil - primeiro_quartil)

                aba_after_parto = aba_after_parto[
                    (aba_after_parto.iloc[:, 2] >= limite_inferior) & (aba_after_parto.iloc[:, 2] <= limite_superior)]
            else:
                # Se não houver dados após o parto, define limites que não filtram nada
                limite_inferior = -np.inf
                limite_superior = np.inf

            # Agrupamento dos dados filtrados
            dados_agrupados_before = aba_before_parto.groupby('horario-servico')
            dados_agrupados_after = aba_after_parto.groupby('horario-servico')

            todas_as_datas = pd.date_range(start=data_inicio, end=data_fim).to_list()

            peso_porca = []
            peso_leitoes = []
            peso_total = []

            for data in todas_as_datas:
                # Para consistência, converte 'data' para a mesma granularidade do agrupamento
                if data_fim_dt - data_inicio_dt <= pd.Timedelta(days=1):
                    data_key = data.floor('H')
                else:
                    data_key = data.date()

                # Inicializa os pesos
                porca = 0
                leitoes = 0
                total = 0

                # Processa dados antes do parto
                if data < data_parto_dt:
                    if data_key in dados_agrupados_before.groups:
                        dados_do_grupo = dados_agrupados_before.get_group(data_key)
                        if len(dados_do_grupo) > 0:
                            porca = int(dados_do_grupo.iloc[:, 2].mean())  # Média do peso da porca
                else:
                    # Processa dados após o parto
                    if data_key in dados_agrupados_after.groups:
                        dados_do_grupo = dados_agrupados_after.get_group(data_key)
                        if len(dados_do_grupo) > quantidade_de_leitoes + 1:
                            pesos = dados_do_grupo.iloc[:, 2].values
                            histograma, beans = np.histogram(pesos, bins=quantidade_de_leitoes + 1)

                            idx_porca = next((i for i, v in enumerate(beans) if v > 0), 0)
                            porca = int(beans[idx_porca])

                            if idx_porca < len(beans) - 1:
                                leitoes = int(beans[-1] - beans[idx_porca])
                            else:
                                leitoes = 0

                            total = int(beans[-1])
                        elif len(dados_do_grupo) > 0:
                            # Se houver dados, mas não suficientes para calcular histograma
                            porca = int(dados_do_grupo.iloc[:, 2].mean())
                            leitoes = 0
                            total = 0

                peso_porca.append(porca)
                peso_leitoes.append(leitoes)
                peso_total.append(total)

            # Dados de resposta
            response_data = {
                'pesoTotal': peso_total,
                'pesoPorca': peso_porca,
                'pesoLeitoes': peso_leitoes,
                'dataInicio': data_inicio,
                'dataFim': data_fim
            }

            # Geração da planilha Excel, se solicitado
            if gerar_planilha:
                output = BytesIO()
                writer = pd.ExcelWriter(output, engine='xlsxwriter')

                df = pd.DataFrame({
                    'Data': [data.strftime('%Y-%m-%d') for data in todas_as_datas],
                    'Peso da Porca': peso_porca,
                    'Peso dos Leitões': peso_leitoes,
                    'Peso Total': peso_total,
                })

                df.to_excel(writer, index=False)
                writer.close()
                output.seek(0)

                # Salvando o arquivo Excel no sistema de arquivos
                planilha_filename = f'dados_{data_inicio}_{data_fim}.xlsx'
                planilha_path = os.path.join(settings.MEDIA_ROOT, planilha_filename)
                with open(planilha_path, 'wb') as f:
                    f.write(output.getvalue())

                response_data['planilha_download_url'] = settings.MEDIA_URL + planilha_filename

            return JsonResponse(response_data)

    return JsonResponse({'Error': "Erro ao processar a solicitação"}, status=400)