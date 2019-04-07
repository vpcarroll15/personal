from django.db import models


class Musician(models.Model):
    """Represents one musician or band."""
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(db_index=True,
                                      auto_now=True,  # Updates each time save() is called
                                      )

    name = models.CharField(max_length=100, unique=True)
    tags = models.ManyToManyField('Tag')

    def __str__(self):
        return self.name


class Music(models.Model):
    """Represents one album or piece of music."""
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(db_index=True,
                                      auto_now=True,  # Updates each time save() is called
                                      )

    name = models.CharField(max_length=200)
    musician = models.ForeignKey(Musician, on_delete=models.CASCADE)
    rating = models.SmallIntegerField()

    def __str__(self):
        return str(self.musician) + ": " + str(self.name)


class Tag(models.Model):
    """Encapsulates a tag that can be applied to musicians to classify their work."""
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name
