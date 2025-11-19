import os
import csv
from django.conf import settings
from django.core.management.base import BaseCommand

from langchain_openai import OpenAIEmbeddings
from ...models import ProjectVector  # adjust path

CSV_FILE_PATH = settings.BASE_DIR / "active_projects_2025-11-12_15-24-13.csv"


class Command(BaseCommand):
    help = "Create embeddings from CSV projects and store only vectors in DB."

    def handle(self, *args, **options):
        if not os.path.exists(CSV_FILE_PATH):
            self.stderr.write(self.style.ERROR(f"CSV not found: {CSV_FILE_PATH}"))
            return

        with open(CSV_FILE_PATH, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        if not rows:
            self.stdout.write(self.style.WARNING("No rows found in CSV"))
            return

        texts = []

        for idx, row in enumerate(rows):
            project_url = (
                row.get("Project_URL")
                or row.get("ProjectUrl")
                or row.get("URL")
                or row.get("project_url")
                or row.get("\ufeffProject_URL")
                or "Unknown URL"
            )

            priority_raw = row.get("Priority", "") or ""
            try:
                priority = int(priority_raw)
            except (ValueError, TypeError):
                priority = 0

            categories = row.get("Categories", "N/A")
            technology = row.get("Technology", "N/A")
            title = row.get("Title") or row.get("ProjectName") or row.get("Name") or ""
            description = row.get("Description") or row.get("Notes") or ""

            # Same text you used before for embeddings
            page_content = " | ".join(
                x for x in [
                    title.strip(),
                    description.strip(),
                    f"Categories: {categories}",
                    f"Technology: {technology}",
                    f"URL: {project_url}",
                    f"Priority: {priority}",
                ] if x
            )

            texts.append((idx, page_content))

        self.stdout.write("Generating embeddings...")
        embeddings_model = OpenAIEmbeddings()
        # list[str] → list[list[float]]
        vectors = embeddings_model.embed_documents([t[1] for t in texts])

        ProjectVector.objects.all().delete()  # optional: clean slate

        objs = []
        for (row_index, page_content), emb in zip(texts, vectors):
            objs.append(ProjectVector(
                row_index=row_index,
                page_content=page_content,
                embedding=emb,
            ))

        ProjectVector.objects.bulk_create(objs, batch_size=100)
        self.stdout.write(self.style.SUCCESS(f"Stored {len(objs)} vectors in DB"))
