from django.db import models

# Create your models here.

class Patient(models.Model):
    name = models.CharField(max_length=200)
    identity_number = models.CharField(max_length=200)
    date_of_birth = models.DateField()

    def __str__(self):
        return self.name

class Virus(models.Model):
    name = models.CharField(max_length=200, primary_key=True)
    common_name = models.CharField(max_length=200)
    max_infectious_period = models.IntegerField()

    class Meta:
        verbose_name_plural = "Viruses"

    def __str__(self):
        return self.name

class Location(models.Model):
    name = models.CharField(max_length=200)
    address = models.CharField(max_length=200)
    x_coord = models.FloatField()
    y_coord = models.FloatField()

    def __str__(self):
        return self.name

class Case(models.Model):
    #
    num = models.CharField(max_length=20)
    #
    confirmed_date = models.DateField()
    is_local = models.BooleanField()
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    virus = models.ForeignKey(Virus, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        #return str(self.pk)
        return str(self.num)

class Visit(models.Model):
    date_from = models.DateField()
    date_to = models.DateField()
    case = models.ForeignKey(Case, on_delete=models.CASCADE)
    location = models.ForeignKey(Location, on_delete=models.CASCADE)
    category = models.CharField(max_length=200)

    def __str__(self):
        return str(self.case.num) + "-" + str(self.pk)
