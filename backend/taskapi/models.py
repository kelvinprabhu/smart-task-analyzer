from django.db import models

# Create your models here.
class Task(models.Model):
    title = models.CharField(max_length=255)
    due_date = models.DateField(null=True, blank=True)
    estimated_hours = models.FloatField(default=1)
    importance = models.IntegerField(default=1)
    dependencies = models.ManyToManyField("self", blank=True, symmetrical=False)

    def __str__(self):
        return self.title