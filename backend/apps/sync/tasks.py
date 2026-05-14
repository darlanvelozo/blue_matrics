"""Tasks Celery para sync."""
from __future__ import annotations

import logging

from celery import shared_task

from .orchestrator import sync_tenant

logger = logging.getLogger(__name__)


@shared_task(name="sync.sync_tenant", bind=True, max_retries=2, default_retry_delay=60)
def sync_tenant_task(self, tenant_id: int, *, full: bool = False) -> int:  # type: ignore[no-untyped-def]
    """Executa sync completo para 1 tenant. Retorna o id do SyncLog master."""
    try:
        log = sync_tenant(tenant_id, full=full)
        return log.id
    except Exception as e:
        logger.exception("sync_tenant_task falhou: %s", e)
        raise self.retry(exc=e) from e
