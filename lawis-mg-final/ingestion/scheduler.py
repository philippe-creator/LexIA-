"""
Scheduler — déclenchement périodique du cycle de veille
Utilise APScheduler pour une exécution planifiée (toutes les N heures).
"""
import os
import time
from loguru import logger
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

from ingestion.watcher import run_watch_cycle, backfill_sgg_cycle

INTERVAL_HOURS = int(os.getenv("WATCH_INTERVAL_HOURS", "24"))

# Rattrapage historique du Bulletin Officiel (~4891 numéros depuis 1912) :
# job séparé du cycle de veille normal, désactivé par défaut. Coûte du calcul
# continu (embedding) tant que l'archive n'est pas rattrapée — à activer
# volontairement une fois déployé sur un serveur dimensionné pour, jamais par
# défaut en local ni au premier déploiement.
SGG_BACKFILL_ENABLED = os.getenv("SGG_BACKFILL_ENABLED", "false").lower() == "true"
SGG_BACKFILL_BATCH_SIZE = int(os.getenv("SGG_BACKFILL_BATCH_SIZE", "5"))
SGG_BACKFILL_INTERVAL_HOURS = int(os.getenv("SGG_BACKFILL_INTERVAL_HOURS", "2"))


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

    if SGG_BACKFILL_ENABLED:
        logger.info(
            f"Rattrapage SGG activé — lot de {SGG_BACKFILL_BATCH_SIZE} numéro(s) "
            f"toutes les {SGG_BACKFILL_INTERVAL_HOURS}h."
        )
        scheduler.add_job(
            func=lambda: backfill_sgg_cycle(SGG_BACKFILL_BATCH_SIZE),
            trigger=IntervalTrigger(hours=SGG_BACKFILL_INTERVAL_HOURS),
            id="sgg_backfill",
            name="Rattrapage archive Bulletin Officiel",
            replace_existing=True,
            max_instances=1,
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
