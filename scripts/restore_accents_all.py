# -*- coding: utf-8 -*-
"""
Restore French accents across all lots.

Invariant: fold_to_ascii(new) == fold_to_ascii(old) for every change.
Uses word-boundary replaces for short stems so «etre» does not hit «mettre».
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from game_paths import ROOT
from text_render import fold_to_ascii

LOTS = [
    ROOT / "work" / "lots" / "p0_menus.json",
    ROOT / "work" / "lots" / "p1_pc.json",
    ROOT / "work" / "lots" / "p2_story.json",
    ROOT / "work" / "lots" / "p3_dll.json",
]

# Exact substring phrases (may include punctuation / spaces). Longest first at apply.
PHRASES: list[tuple[str, str]] = [
    ("Piece d'identite", "Pièce d'identité"),
    ("PIECE D'IDENTITE", "PIÈCE D'IDENTITÉ"),
    ("Mode fenetre:", "Mode fenêtre:"),
    ("MODE FENETRE:", "MODE FENÊTRE:"),
    ("Recherche sociale instantanee", "Recherche sociale instantanée"),
    ("Crack RootKit instantane", "Crack RootKit instantané"),
    ("Cracks RootKit instantanes", "Cracks RootKit instantanés"),
    ("Quota coucher anticipe", "Quota coucher anticipé"),
    ("Connexion reseau", "Connexion réseau"),
    ("Rapports rejetes", "Rapports rejetés"),
    ("MODE DETECTIVE:", "MODE DÉTECTIVE:"),
    ("SCENARISTES PRINCIPAUX", "SCÉNARISTES PRINCIPAUX"),
    ("Scenaristes principaux", "Scénaristes principaux"),
    ("Merci d'avoir joue", "Merci d'avoir joué"),
    ("A suivre", "À suivre"),
    ("etre en prison", "être en prison"),
    ("ou le tueur", "où le tueur"),
    ("jeter un oeil a ", "jeter un œil à "),
    ("jeter un oeil à ", "jeter un œil à "),
    ("un oeil a ", "un œil à "),
    ("s'eteignent", "s'éteignent"),
    ("arriere-salle", "arrière-salle"),
    ("a fureter", "à fureter"),
    ("regler ca", "régler ça"),
    ("regler ça", "régler ça"),
    ("a ces B.O.L.O", "à ces B.O.L.O"),
    ("encore lache,", "encore lâché,"),
    ("a encore lache", "a encore lâché"),
    ("recommande a ", "recommande à "),
    ("fabriquait a ", "fabriquait à "),
    ("premier creneau", "premier créneau"),
    ("Premier creneau", "Premier créneau"),
    ("Une fois repere", "Une fois repéré"),
    ("j'ai aussitot verifie", "j'ai aussitôt vérifié"),
    ("m'a semble", "m'a semblé"),
    ("homme recherche par", "homme recherché par"),
    ("lumiere de ma camera allumee", "lumière de ma caméra allumée"),
    ("lumiere de la camera", "lumière de la caméra"),
    ("Pas de mort definitive", "Pas de mort définitive"),
    ("Mort definitive", "Mort définitive"),
    ("experience tranquille", "expérience tranquille"),
    ("juste resoudre", "juste résoudre"),
    ("Reserve aux joueurs", "Réservé aux joueurs"),
    ("un vrai defi", "un vrai défi"),
    ("Desactive-les", "Désactive-les"),
    ("Passee", "Passée"),
    ("nuit passee", "nuit passée"),
    # --- long PC prose (pass 2) ---
    ("signale ce jour a l'agence", "signalé ce jour à l'agence"),
    ("pensons implique dans", "pensons impliqué dans"),
    ("Nos soupcons reposent", "Nos soupçons reposent"),
    ("le temoignage de", "le témoignage de"),
    ("s'echapper", "s'échapper"),
    ("homme opere seul", "homme opère seul"),
    ("exclusivement a des femmes", "exclusivement à des femmes"),
    ("par ailleurs ete rapporte", "par ailleurs été rapporté"),
    ("des economies", "des économies"),
    ("signalements designent", "signalements désignent"),
    ("fenêtre defectueux", "fenêtre défectueux"),
    ("lumières allumees", "lumières allumées"),
    ("j'ai allume la lumière", "j'ai allumé la lumière"),
    ("tenir informee", "tenir informée"),
    ("Je suis déborde ces", "Je suis débordé ces"),
    ("Je suis deborde ces", "Je suis débordé ces"),
    ("d'affilee", "d'affilée"),
    ("mal serre a l'origine", "mal serré à l'origine"),
    ("limitez-vous a de", "limitez-vous à de"),
    ("une hypothese", "une hypothèse"),
    ("au debut du mois", "au début du mois"),
    ("tu as termine ", "tu as terminé "),
    ("Tu es pret ", "Tu es prêt "),
]

# Whole-word only (Unicode letter boundaries).
WORDS: list[tuple[str, str]] = [
    ("PARAMETRES", "PARAMÈTRES"),
    ("Parametres", "Paramètres"),
    ("parametres", "paramètres"),
    ("SENSIBILITE", "SENSIBILITÉ"),
    ("Sensibilite", "Sensibilité"),
    ("sensibilite", "sensibilité"),
    ("RESOLUTION", "RÉSOLUTION"),
    ("Resolution", "Résolution"),
    ("resolution", "résolution"),
    ("QUALITE", "QUALITÉ"),
    ("Qualite", "Qualité"),
    ("qualite", "qualité"),
    ("ELEVEE", "ÉLEVÉE"),
    ("Elevee", "Élevée"),
    ("elevee", "élevée"),
    ("ILLIMITE", "ILLIMITÉ"),
    ("Illimite", "Illimité"),
    ("illimite", "illimité"),
    ("DETENTE", "DÉTENTE"),
    ("Detente", "Détente"),
    ("detente", "détente"),
    ("FENETRE", "FENÊTRE"),
    ("Fenetre", "Fenêtre"),
    ("fenetre", "fenêtre"),
    ("ECRAN", "ÉCRAN"),
    ("Ecran", "Écran"),
    ("ecran", "écran"),
    ("RESULTATS", "RÉSULTATS"),
    ("Resultats", "Résultats"),
    ("resultats", "résultats"),
    ("AMELIORATIONS", "AMÉLIORATIONS"),
    ("Ameliorations", "Améliorations"),
    ("ameliorations", "améliorations"),
    ("DEPENSE", "DÉPENSE"),
    ("Depense", "Dépense"),
    ("depense", "dépense"),
    ("IDENTITE", "IDENTITÉ"),
    ("Identite", "Identité"),
    ("identite", "identité"),
    ("PIECE", "PIÈCE"),
    ("Piece", "Pièce"),
    ("SCENARISTES", "SCÉNARISTES"),
    ("Scenaristes", "Scénaristes"),
    ("scenaristes", "scénaristes"),
    ("DEVELOPPEUR", "DÉVELOPPEUR"),
    ("Developpeur", "Développeur"),
    ("developpeur", "développeur"),
    ("DETECTIVE", "DÉTECTIVE"),
    ("Detective", "Détective"),
    ("AGE", "ÂGE"),
    ("Age", "Âge"),
    ("Lumieres", "Lumières"),
    ("lumieres", "lumières"),
    ("lumiere", "lumière"),
    ("Lumiere", "Lumière"),
    ("cameras", "caméras"),
    ("camera", "caméra"),
    ("Cameras", "Caméras"),
    ("Camera", "Caméra"),
    ("instantanee", "instantanée"),
    ("Instantanee", "Instantanée"),
    ("instantanes", "instantanés"),
    ("instantane", "instantané"),
    ("Instantane", "Instantané"),
    ("reseau", "réseau"),
    ("Reseau", "Réseau"),
    ("anticipe", "anticipé"),
    ("rejetes", "rejetés"),
    ("recentes", "récentes"),
    ("Recentes", "Récentes"),
    ("deborde", "déborde"),
    ("Deborde", "Déborde"),
    ("reponses", "réponses"),
    ("Reponses", "Réponses"),
    ("reponse", "réponse"),
    ("Reponse", "Réponse"),
    ("desactive", "désactive"),
    ("Desactive", "Désactive"),
    ("definitive", "définitive"),
    ("experience", "expérience"),
    ("resoudre", "résoudre"),
    ("Reserve", "Réservé"),
    ("defi", "défi"),
    ("derniere", "dernière"),
    ("Derniere", "Dernière"),
    ("aussitot", "aussitôt"),
    ("verifie", "vérifié"),
    ("etrange", "étrange"),
    ("Etrange", "Étrange"),
    ("roder", "rôder"),
    ("repere", "repéré"),
    ("communaute", "communauté"),
    ("eteignent", "éteignent"),
    ("eteindre", "éteindre"),
    ("allumee", "allumée"),
    ("creneau", "créneau"),
    ("oeil", "œil"),
    ("lache", "lâché"),
    ("reinitialiser", "réinitialiser"),
    ("arriere", "arrière"),
    ("rearmer", "réarmer"),
    ("passee", "passée"),
    ("etre", "être"),
    ("Etre", "Être"),
    ("ETRE", "ÊTRE"),
    ("deja", "déjà"),
    ("Deja", "Déjà"),
    ("voila", "voilà"),
    ("Voila", "Voilà"),
    ("proteger", "protéger"),
    ("Protegere", "Protéger"),
    ("apres", "après"),
    ("Apres", "Après"),
    ("tres", "très"),
    ("Tres", "Très"),
    ("meme", "même"),
    ("Meme", "Même"),
    ("grace", "grâce"),
    ("Grace", "Grâce"),
    ("facon", "façon"),
    ("Facon", "Façon"),
    ("controle", "contrôle"),
    ("Controle", "Contrôle"),
    ("numero", "numéro"),
    ("Numero", "Numéro"),
    ("role", "rôle"),
    ("Role", "Rôle"),
    ("evenement", "événement"),
    ("Evenement", "Événement"),
    ("premiere", "première"),
    ("Premiere", "Première"),
    ("verite", "vérité"),
    ("Verite", "Vérité"),
    ("securite", "sécurité"),
    ("Securite", "Sécurité"),
    ("necessaire", "nécessaire"),
    ("Necessaire", "Nécessaire"),
    ("ecoute", "écoute"),
    ("Ecoute", "Écoute"),
    ("ecrit", "écrit"),
    ("Ecrit", "Écrit"),
    ("equipe", "équipe"),
    ("Equipe", "Équipe"),
    ("interet", "intérêt"),
    ("Interet", "Intérêt"),
    ("liberte", "liberté"),
    ("Liberte", "Liberté"),
    ("maitre", "maître"),
    ("Maitre", "Maître"),
    ("matiere", "matière"),
    ("Matiere", "Matière"),
    ("memoire", "mémoire"),
    ("Memoire", "Mémoire"),
    ("metier", "métier"),
    ("Metier", "Métier"),
    ("modele", "modèle"),
    ("Modele", "Modèle"),
    ("probleme", "problème"),
    ("Probleme", "Problème"),
    ("systeme", "système"),
    ("Systeme", "Système"),
    ("societe", "société"),
    ("Societe", "Société"),
    ("serie", "série"),
    ("Serie", "Série"),
    ("serieux", "sérieux"),
    ("Serieux", "Sérieux"),
    ("special", "spécial"),
    ("Special", "Spécial"),
    ("scene", "scène"),
    ("Scene", "Scène"),
    ("seance", "séance"),
    ("Seance", "Séance"),
    ("succes", "succès"),
    ("Succes", "Succès"),
    ("temoin", "témoin"),
    ("Temoin", "Témoin"),
    ("telephone", "téléphone"),
    ("Telephone", "Téléphone"),
    ("vehicule", "véhicule"),
    ("Vehicule", "Véhicule"),
    ("video", "vidéo"),
    ("Video", "Vidéo"),
    ("annee", "année"),
    ("Annee", "Année"),
    ("annees", "années"),
    ("Annees", "Années"),
    ("eviter", "éviter"),
    ("Eviter", "Éviter"),
    ("desole", "désolé"),
    ("Desole", "Désolé"),
    ("enquete", "enquête"),
    ("Enquete", "Enquête"),
    ("enleve", "enlevé"),
    ("Enleve", "Enlevé"),
    ("hopital", "hôpital"),
    ("Hopital", "Hôpital"),
    ("peut-etre", "peut-être"),
    ("Peut-etre", "Peut-être"),
    ("recu", "reçu"),
    ("Recu", "Reçu"),
    ("editeur", "éditeur"),
    ("Editeur", "Éditeur"),
    ("gerer", "gérer"),
    ("Gerer", "Gérer"),
    ("leger", "léger"),
    ("Leger", "Léger"),
    ("legal", "légal"),
    ("Legal", "Légal"),
    ("regle", "règle"),
    ("Regle", "Règle"),
    ("releve", "relève"),
    ("Releve", "Relève"),
    ("procede", "procédé"),
    ("Procede", "Procédé"),
    ("reduit", "réduit"),
    ("Reduit", "Réduit"),
    ("reussi", "réussi"),
    ("Reussi", "Réussi"),
    ("resume", "résumé"),
    ("Resume", "Résumé"),
    ("reve", "rêve"),
    ("Reve", "Rêve"),
    ("etait", "était"),
    ("Etait", "Était"),
    ("etes", "êtes"),
    ("Etes", "Êtes"),
    ("joue", "joué"),
    ("Joue", "Joué"),
    ("ca", "ça"),
    ("Ca", "Ça"),
]

# "a" / "A" / "ou" are too ambiguous for global word replace — phrase list only.
# Email field labels:
LABELS: list[tuple[str, str]] = [
    ("A:", "À:"),
]


def _word_replace(text: str, src: str, dst: str) -> str:
    return re.sub(rf"(?<!\w){re.escape(src)}(?!\w)", dst, text)


def accentuate(text: str) -> str:
    out = text
    for src, dst in sorted(PHRASES, key=lambda kv: -len(kv[0])):
        if src in out:
            out = out.replace(src, dst)
    for src, dst in LABELS:
        if src in out:
            out = out.replace(src, dst)
    for src, dst in sorted(WORDS, key=lambda kv: -len(kv[0])):
        out = _word_replace(out, src, dst)
    return out


LEFTOVER = re.compile(
    r"(?i)\b("
    r"desactive|definitive|experience|resoudre|reserve|defi|"
    r"derniere|aussitot|verifie|cameras|etrange|roder|lumiere|"
    r"repere|communaute|eteignent|allumee|creneau|regler|"
    r"reseau|anticipe|instantane|oeil|lache|reinitialiser|"
    r"arriere|rearmer|resultats|rejetes|developpeur|scenaristes|"
    r"detectiv|passee|parametres|sensibilite|resolution|qualite|"
    r"fenetre|ecran|identite|ameliorations|depense|elevee|illimite|"
    r"detente|etre|etait|deja|proteger"
    r")\b"
)


def main() -> None:
    changed_entries = 0
    changed_files = 0
    failed: list = []
    leftovers: list = []

    for path in LOTS:
        lot = json.loads(path.read_text(encoding="utf-8"))
        dirty = False
        for e in lot.get("entries", []):
            old = e["fr"]
            new = accentuate(old)
            if new != old:
                if fold_to_ascii(new) != fold_to_ascii(old):
                    failed.append((path.name, old[:70], new[:70], fold_to_ascii(new)[:70]))
                    continue
                e["fr"] = new
                changed_entries += 1
                dirty = True
            hits = LEFTOVER.findall(e["fr"])
            if hits:
                leftovers.append((path.name, hits, e["fr"][:100]))
        if dirty:
            path.write_text(
                json.dumps(lot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            changed_files += 1
            print(f"{path.name}: maj")

    print(f"{changed_entries} entrees modifiees dans {changed_files} lots")
    if failed:
        print(f"\n{len(failed)} refus invariant:")
        for row in failed[:25]:
            print(" ", row)
        raise SystemExit(1)
    if leftovers:
        print(f"\n{len(leftovers)} restes:")
        for row in leftovers:
            print(" ", row[0], row[1], "|", row[2])
    else:
        print("Aucun reste heuristique.")


if __name__ == "__main__":
    main()
