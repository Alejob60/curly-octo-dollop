import hashlib
import re
from datetime import datetime, timezone
from typing import Dict, List
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from google.cloud import storage
from loguru import logger

from app.core.config import settings
from app.workers.dispatcher import historical_dispatcher


class HistoricalPqrsCrawler:
    def __init__(self):
        self.source_url = settings.HISTORICAL_PQRS_SOURCE_URL
        self.project_id = settings.GCP_PROJECT_ID
        self.raw_bucket_name = settings.GCP_RAW_PDF_BUCKET
        self._storage_client = None

        try:
            if self.project_id:
                self._storage_client = storage.Client(project=self.project_id)
            else:
                self._storage_client = storage.Client()
        except Exception as exc:
            logger.warning(f"No fue posible iniciar cliente GCS en crawler: {exc}")
            self._storage_client = None

    async def discover_pdf_links(self) -> List[str]:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(self.source_url)
            response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        links = []
        for anchor in soup.select("a[href]"):
            href = anchor.get("href", "").strip()
            if not href:
                continue
            if ".pdf" not in href.lower():
                continue
            links.append(urljoin(self.source_url, href))

        # Deduplicate preserving order
        unique_links = list(dict.fromkeys(links))
        logger.info(f"Crawler detecto {len(unique_links)} PDFs historicos.")
        return unique_links

    async def run_once(self, limit: int | None = None) -> Dict[str, int]:
        pdf_links = await self.discover_pdf_links()
        if limit:
            pdf_links = pdf_links[:limit]

        jobs = []
        uploaded_count = 0
        skipped_count = 0

        for link in pdf_links:
            upload_result = await self._upload_pdf_to_raw_bucket(link)
            if not upload_result:
                skipped_count += 1
                continue

            uploaded_count += 1
            jobs.append(
                {
                    "source_pdf_url": link,
                    "blob_name": upload_result["blob_name"],
                    "bucket_name": self.raw_bucket_name,
                    "idempotency_key": upload_result["idempotency_key"],
                    "ingested_at": datetime.now(timezone.utc).isoformat(),
                }
            )

        dispatch_result = await historical_dispatcher.publish_pdf_jobs(jobs)

        return {
            "detected": len(pdf_links),
            "uploaded": uploaded_count,
            "skipped": skipped_count,
            **dispatch_result,
        }

    async def _upload_pdf_to_raw_bucket(self, pdf_url: str) -> Dict[str, str] | None:
        if not self._storage_client:
            logger.warning("Crawler sin cliente GCS; no se subira PDF.")
            return None

        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.get(pdf_url)
            response.raise_for_status()
            pdf_bytes = response.content

        digest = hashlib.sha256(pdf_bytes).hexdigest()
        idempotency_key = digest[:24]

        file_name = pdf_url.rsplit("/", 1)[-1]
        sanitized_name = re.sub(r"[^a-zA-Z0-9._-]", "_", file_name)
        blob_name = f"historical-pqrs/{datetime.now(timezone.utc).strftime('%Y/%m')}/{idempotency_key}_{sanitized_name}"

        bucket = self._storage_client.bucket(self.raw_bucket_name)
        blob = bucket.blob(blob_name)

        if blob.exists():
            return {
                "blob_name": blob_name,
                "idempotency_key": idempotency_key,
            }

        blob.metadata = {
            "source_pdf_url": pdf_url,
            "sha256": digest,
        }
        blob.upload_from_string(pdf_bytes, content_type="application/pdf")

        return {
            "blob_name": blob_name,
            "idempotency_key": idempotency_key,
        }


historical_crawler = HistoricalPqrsCrawler()
