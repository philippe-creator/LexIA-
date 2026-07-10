"""
Scheduler — déclenchement périodique du cycle de veille
Utilise APScheduler pour une exécution planifiée (toutes les N heures).
"""
import os
import time
from loguru import logger
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

from ingestion.watcher import run_watch_cycle

INTERVAL_HOURS = int(os.getenv("WATCH_INTERVAL_HOURS", "24"))


def main():
    logger.info(f"Démarrage du scheduler — intervalle : {INTERVAL_HOURS}h")

    scheduler = BlockingScheduler(timezone="Africa/Casablanca")

    scheduler.add_job(
        func=run_watch_cycle,
        trigger=IntervalTrigger(hours=INTERVAL_HOURS),
        id="watch_cycle",
        name="Cycle de veille juridique",
        replace_existing=True,
        max_instances=1,      # éviter les exécutions parallèles
    )

    # Lancer un premier cycle immédiatement au démarrage
    logger.info("Premier cycle immédiat au démarrage...")
    run_watch_cycle()

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler arrêté.")


if __name__ == "__main__":
    main()
