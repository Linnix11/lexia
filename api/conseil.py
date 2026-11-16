"""Demandes de conseil personnel : les seules questions que Lexia refuse (D77).

Lexia explique le droit applicable a des faits, meme racontes a la premiere personne (« le fils de mes
voisins a tague mon garage, a qui puis-je reclamer ? ») : c'est la matiere du cas pratique. Elle refuse
seulement ce qui ne releve que du conseil : rediger un document a envoyer, predire l'issue d'un litige,
chiffrer la somme a obtenir, decider des demarches a la place de l'utilisateur.

La decision etait laissee au modele (regle 8 de prompts.SYSTEME) : sur la meme question, il refusait une
fois sur trois ou deux sur trois. Elle est prise ici, de facon stable, avant tout appel au modele.
"""

from __future__ import annotations

import re

from api.lexique import normaliser

_CONSEIL = re.compile(
    # rediger un document a envoyer
    r"\b(?:redige|redigez|ecris|ecrivez|prepare|preparez)[- ]?(?:moi|nous)\b"
    r"|\b(?:rediger|ecrire|preparer)\b.{0,40}\b(?:pour moi|a envoyer|que j.envoie)"
    # predire l'issue
    r"|\bvais-je (?:gagner|perdre|obtenir)|est-ce que je vais (?:gagner|perdre|obtenir)"
    r"|\b(?:ai-je|j.ai)\b.{0,15}\bchances?\b|quelles? sont mes chances"
    # chiffrer la somme
    r"|\bcombien\b(?! de (?:temps|jours|mois|semaines))(?! d.(?:annees|ans))(?! de fois).{0,60}\b(?:puis-je|pourrais-je|vais-je|dois-je|je peux|je pourrais|je vais|toucher|reclamer|obtenir)"
    # decider des demarches a la place de l'utilisateur
    r"|\b(?:que|quoi) (?:dois-je|devrais-je|je dois) faire\b"
    r"|\bquelles? demarches?\b.{0,60}\b(?:dois-je|devrais-je|pour moi|je dois)"
    r"|\b(?:dois-je|devrais-je|faut-il que je|est-ce que je dois|est-ce que je devrais)\b.{0,20}"
    r"\b(?:porte[rz]? plainte|saisir|saisisse|prendre un avocat|prenne un avocat|signer|signe|accepter|accepte"
    r"|refuser|refuse|attaquer|attaque|poursuivre|poursuive)\b"
    # rediger un document precis, a l'imperatif (« redigez une mise en demeure pour mon voisin ») : la
    # liste exclut fiche, plan, reponse, commentaire, dissertation, qui sont des exercices d'etude.
    r"|\b(?:redige|redigez|ecris|ecrivez|prepare|preparez)\b(?:[- ]?(?:moi|nous))?\s+"
    r"(?:un|une|la|le|ma|mon|mes|les|des|l')\s*(?:mise en demeure|lettre|courrier|mail|e-?mail|plainte"
    r"|contestation|reclamation|recours|requete|assignation|conclusions?|resiliation|declaration|attestation"
    r"|preavis|demission)\b"
)


def demande_de_conseil(question: str) -> bool:
    return bool(_CONSEIL.search(normaliser(question)))
