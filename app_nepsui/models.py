from django.db import models

class ArquivoExcel(models.Model):
    arquivo = models.FileField(upload_to='uploads/')