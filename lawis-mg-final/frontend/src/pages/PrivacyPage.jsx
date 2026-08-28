import React from "react";
import { Link } from "react-router-dom";
import { resetConsent } from "../services/analytics";

export default function PrivacyPage() {
  return (
    <div className="page-container legal-page">
      <div className="page-header">
        <h1>Politique de confidentialité</h1>
        <p>Dernière mise à jour : {new Date().toLocaleDateString("fr-MA", { year: "numeric", month: "long" })}</p>
      </div>

      <section>
        <h2>1. Qui traite vos données</h2>
        <p>
          LexIA Maroc est une plateforme d'assistance juridique développée dans le cadre d'un projet
          de fin d'études (stage à Zenithsoft, Rabat). Le responsable du traitement des données décrites
          ci-dessous est l'éditeur de la plateforme, joignable à l'adresse indiquée en fin de page.
        </p>
      </section>

      <section>
        <h2>2. Données collectées</h2>
        <ul>
          <li><strong>Compte</strong> : email, nom d'utilisateur, nom complet (facultatif), profil (étudiant, particulier, juriste, avocat, entreprise), mot de passe (stocké haché, jamais en clair).</li>
          <li><strong>Utilisation</strong> : historique de vos conversations avec l'assistant, questions posées, documents que vous importez volontairement.</li>
          <li><strong>Technique</strong> : adresse IP (limitation de débit, sécurité), horodatages de connexion.</li>
        </ul>
      </section>

      <section>
        <h2>3. Finalité du traitement</h2>
        <p>
          Ces données sont utilisées exclusivement pour : fournir le service (authentification, historique
          de vos échanges, personnalisation des réponses selon votre profil), assurer la sécurité de la
          plateforme (limitation des abus, journal d'audit) et, si vous y consentez, vous envoyer un email
          de réinitialisation de mot de passe ou une notification liée à votre compte.
        </p>
      </section>

      <section>
        <h2>4. Base légale et conservation</h2>
        <p>
          Le traitement repose sur l'exécution du service que vous avez demandé en créant un compte, conformément
          à la loi n°09-08 relative à la protection des personnes physiques à l'égard du traitement des données à
          caractère personnel. Vos données sont conservées tant que votre compte est actif ; les documents que vous
          importez restent visibles par vous seul et ne sont jamais partagés avec d'autres utilisateurs.
        </p>
      </section>

      <section>
        <h2>5. Vos droits</h2>
        <p>
          Conformément à la loi 09-08, vous disposez d'un droit d'accès, de rectification et d'opposition sur vos
          données personnelles. Vous pouvez à tout moment modifier votre profil depuis votre compte, ou demander
          la suppression de votre compte et de vos données en nous contactant à l'adresse ci-dessous.
        </p>
      </section>

      <section>
        <h2>6. Cookies</h2>
        <p>
          LexIA Maroc dépose un cookie strictement nécessaire au fonctionnement du service (maintien de votre
          session, protégé et inaccessible en JavaScript). Ce cookie ne demande pas de consentement : sans lui,
          vous ne pourriez pas rester connecté.
        </p>
        <p>
          Avec votre accord, un cookie de mesure d'audience (Google Analytics) peut également être déposé pour
          nous aider à comprendre l'usage du site (pages consultées, provenance des visites) — jamais avant que
          vous n'ayez cliqué "J'accepte" sur le bandeau, et jamais à des fins publicitaires.
        </p>
        <p>
          <button type="button" className="text-btn" style={{padding:"6px 0"}} onClick={resetConsent}>
            Gérer mes préférences cookies
          </button>
        </p>
      </section>

      <section>
        <h2>7. Sécurité</h2>
        <p>
          Les mots de passe sont hachés (bcrypt), les sessions reposent sur des jetons signés à durée limitée,
          et les échanges avec l'assistant transitent par des fournisseurs d'intelligence artificielle tiers
          (utilisés uniquement pour générer les réponses, sans conservation par LexIA Maroc au-delà de votre
          historique de conversation).
        </p>
      </section>

      <section>
        <h2>8. Contact</h2>
        <p>Pour toute question relative à vos données ou pour exercer vos droits : ndjinilanguemawen@gmail.com</p>
      </section>

      <p className="legal-back"><Link to="/">← Retour à l'accueil</Link></p>
    </div>
  );
}
