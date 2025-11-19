from django.db import models

# Create your models here.
class ProjectVector(models.Model):
    """
    Minimal storage:
    - page_content: the text we embedded
    - embedding: the vector
    - row_index: position in original CSV (optional but handy)
    """
    row_index = models.IntegerField(unique=True)
    page_content = models.TextField()
    embedding = models.JSONField()  # list[float]

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"ProjectVector #{self.row_index}"