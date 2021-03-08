from django.db import models


class Organization(models.Model):
	ein = models.CharField(max_length=9, null=True)
	name = models.CharField(max_length=255)
	address_line_1 = models.CharField(max_length=255)
	city = models.CharField(max_length=100)
	state = models.CharField(max_length=2, db_index=True)
	zipcode = models.CharField(max_length=10)


class Award(models.Model):
	filer = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='awards_given')
	recipient = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='awards_received')
	purpose = models.TextField()
	amount_dollars = models.PositiveIntegerField()
	filing_url = models.URLField()
