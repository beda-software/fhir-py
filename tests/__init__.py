class Chat(models.Model):
    title = models.CharField()
    subject = models.ForeignKey('Patient')

