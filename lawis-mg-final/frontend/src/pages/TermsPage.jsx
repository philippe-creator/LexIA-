import React from "react";
import { Link } from "react-router-dom";

export default function TermsPage() {
  return (
    <div className="page-container legal-page">
      <div className="page-header">
        <h1>Conditions générales d'utilisation</h1>
        <p>Dernière mise à jour : {new Date().toLocaleDateString("fr-MA", { year: "numeric", month: "long" })}</p>
      </div>

      <section>
        <h2>1. Objet</h2>
        <p>
          LexIA Maroc est une plateforme d'assistance juridique dédiée au droit marocain, fondée sur une
          architecture de recherche augmentée par génération (RAG) : elle recherche des passages pertinents
          dans un corpus de textes officiels indexés, puis rédige une réponse à partir de ces passages en
          citant leurs sources. Les présentes CGU encadrent l'utilisation de la plateforme par tout utilisateur
          inscrit.
        </p>
      </section>

      <section>
        <h2>2. Nature du service — avertissement important</h2>
        <p>
          <strong>Les réponses fournies par LexIA Maroc sont informatives et ne constituent en aucun cas un
          avis juridique professionnel.</strong> Elles sont générées à partir de textes officiels indexés mais
          peuvent être incomplètes, ne pas couvrir une évolution récente de la législation, ou ne pas s'appliquer
          à votre situation particulière. Pour toute décision engageant vos droits ou obligations, consultez un
          professionnel du droit habilité (avocat, notaire, juriste).
        </p>
      </section>

      <section>
        <h2>3. Compte utilisateur</h2>
        <p>
          L'inscription nécessite un email valide et un mot de passe respectant les règles de sécurité minimales
          affichées à l'inscription. Vous êtes responsable de la confidentialité de vos identifiants et de toute
          activité effectuée depuis votre compte. Vous pouvez demander la suppression de votre compte à tout moment.
        </p>
      </section>

      <section>
        <h2>4. Usage autorisé</h2>
        <p>
          Le service est destiné à un usage personnel ou professionnel raisonnable. Sont interdits : toute
          tentative de contournement des limites techniques (quotas, limitation de débit), toute utilisation
          automatisée non autorisée, et l'import de documents dont vous n'avez pas le droit d'usage.
        </p>
      </section>

      <section>
        <h2>5. Documents importés</h2>
        <p>
          Les documents que vous importez pour les interroger via le chat restent strictement privés : ils ne
          sont jamais partagés avec d'autres utilisateurs ni utilisés pour enrichir la base de connaissances
          générale de la plateforme.
        </p>
      </section>

      <section>
        <h2>6. Disponibilité et évolutions</h2>
        <p>
          Le service est fourni "en l'état", dans le cadre d'un projet de fin d'études. Aucune garantie de
          disponibilité continue n'est assurée. Les fonctionnalités peuvent évoluer sans préavis.
        </p>
      </section>

      <section>
        <h2>7. Résiliation</h2>
        <p>
          Vous pouvez cesser d'utiliser le service et demander la suppression de votre compte à tout moment.
          L'éditeur se réserve le droit de suspendre un compte en cas d'usage abusif manifeste des présentes CGU.
        </p>
      </section>

      <section>
        <h2>8. Contact</h2>
        <p>Pour toute question relative aux présentes CGU : ndjinilanguemawen@gmail.com</p>
      </section>

      <p className="legal-back"><Link to="/">← Retour à l'accueil</Link></p>
    </div>
  );
}
