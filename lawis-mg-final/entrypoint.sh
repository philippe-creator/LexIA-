#!/bin/sh
# Démarre en root pour pouvoir corriger les permissions des volumes montés
# depuis l'hôte (./data, ./logs), puis abandonne les privilèges vers l'utilisateur
# non-root avant de lancer la commande réelle (API ou watcher).
set -e
mkdir -p data/raw data/processed data/uploads data/vector_stores logs
chown -R lexia:lexia data logs
exec gosu lexia "$@"
