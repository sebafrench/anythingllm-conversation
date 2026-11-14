# AnythingLLM Conversation — 1.0.0

Intégration personnalisée Home Assistant, domaine `anythingllm`. Elle transmet le texte d’Assist à AnythingLLM et rend sa réponse à Assist. Les documents, les embeddings, le modèle et les paramètres RAG restent gérés par votre workspace. La pipeline existante conserve ses composants de transcription et de synthèse vocale.

**Cible de validation : Home Assistant Core 2025.3.4, Python 3.13.** Cette version précise sert de référence reproductible ; ce n’est pas une recommandation de rétrograder Home Assistant. Les versions ultérieures ne sont pas certifiées par ces tests. Avant un déploiement sur une autre version, exécuter les tests avec ses dépendances et tester la pipeline. AnythingLLM doit respecter le contrat décrit dans `docs/API.md`. Aucun accès à votre serveur n’a été effectué.

## Architecture

| Fichier | Responsabilité |
|---|---|
| `config_flow.py` | Connexion, clé masquée, liste des workspaces, options, reconfiguration et réauthentification |
| `api.py` | HTTP asynchrone avec session Home Assistant, validation des réponses, erreurs publiques |
| `session.py` | Association conversation → thread ou session API, isolation, délais, annulation et dédoublonnage |
| `conversation.py` | Entité sélectionnable dans Assist, réponses `IntentResponse` et cycle de vie de l’agent |
| `__init__.py` | Chargement, déchargement, rechargement et validation du workspace |

Aucun polling, aucune dépendance externe supplémentaire à installer par l’intégration, aucune clé OpenAI. `aiohttp`, `voluptuous` et les API HA sont déjà fournis par Home Assistant. Le client ne ferme pas la session HTTP partagée.

## 1. Préparer AnythingLLM et sa clé

1. Ouvrir AnythingLLM avec un compte autorisé à gérer les clés API. Dans les paramètres, chercher **API Keys / Clés API / Developer API**, selon la version et la langue.
2. Créer une clé dédiée à Home Assistant, puis la copier dans le formulaire de l’intégration. Une clé existante valide fonctionne aussi. Ne pas la publier, ni la placer dans le code ou dans une capture envoyée pour diagnostic.
3. Vérifier les opérations disponibles dans `http://ADRESSE_DU_SERVEUR:3001/api/docs`. Cette URL de documentation ne doit pas être saisie comme URL de connexion.
4. Choisir un workspace existant, vérifier que son fournisseur de modèle fonctionne et que ses documents ont bien été intégrés à la base vectorielle. Un fichier simplement téléversé mais non intégré au workspace ne suffit pas.
5. Dans le prompt système du workspace, conserver vos instructions et ajouter, si nécessaire : **« Réponds en français, de manière claire et adaptée à une lecture vocale. »** L’intégration ne remplace pas ce prompt. Un modèle reste susceptible d’ignorer une consigne : l’intégration ne traduit pas sa réponse par un second appel.
6. Utiliser un workspace conversationnel sans outils domotiques. Le mode `automatic` et les messages contenant `@agent` ne sont pas proposés. Les fonctionnalités ou mémoires globales que vous activez côté serveur restent sous votre responsabilité ; les threads isolent l’historique de chat, pas les documents partagés du workspace.

## 2. Trouver l’adresse accessible depuis Home Assistant

L’URL doit désigner le serveur **depuis l’environnement réseau de Home Assistant**. Exemple uniquement : `http://192.168.1.50:3001`. Remplacer cette adresse par celle de votre machine ; ce projet n’en suppose aucune.

**`localhost` dans Home Assistant désigne son propre environnement**, souvent son conteneur. Ce n’est pas nécessairement l’ordinateur qui exécute AnythingLLM. Deux conteneurs ont chacun leur loopback. Utiliser un nom DNS joignable, une adresse LAN ou un réseau Docker commun correctement configuré. Le fait que votre navigateur puisse ouvrir le serveur ne prouve pas que Home Assistant le peut.

La racine du serveur, un préfixe reverse proxy, `/api` et `/api/v1` sont acceptés. Les suffixes API sont normalisés. Les URL avec identifiants, query string, fragment ou `/api/docs` sont refusées. Les redirections ne sont pas suivies : saisir directement l’URL finale. Les certificats HTTPS sont vérifiés ; aucun bouton « ignorer TLS » n’est fourni. Pour HTTP, le transport n’est pas chiffré : le réserver à votre réseau de confiance.

**Docker :** service serveur, accès navigateur et multi-utilisateur possibles. Publier le port réellement configuré et vérifier le pare-feu. `3001` est l’exemple habituel, pas une détection automatique.

**Desktop :** l’API développeur existe aussi, mais l’application doit être ouverte et son backend accessible. La documentation actuelle décrit *Settings → Admin → General → Enable network discovery*, puis un redémarrage complet, pour passer d’une écoute loopback à une écoute réseau. Cette option peut ne pas exister dans une ancienne version. Desktop n’est pas une installation multi-utilisateur, et un 404 à sa racine ne démontre pas que son API est absente. Vérifier le port et `/api/docs` de la version installée ; ne pas présumer que Desktop utilise le port de votre installation Docker.

## 3. Installation manuelle

1. Décompresser l’archive sur votre ordinateur.
2. Copier **le dossier `custom_components/anythingllm`** dans le répertoire de configuration HA, afin d’obtenir `/config/custom_components/anythingllm/manifest.json`. Ne pas intercaler le nom du dossier du projet.
3. Ne pas copier l’environnement de test dans Home Assistant et ne pas installer `requirements-test.txt` dans son environnement.
4. Redémarrer Home Assistant. En cas d’absence de l’intégration dans la recherche, actualiser complètement le navigateur.
5. Dans **Paramètres → Appareils et services → Ajouter une intégration**, chercher **AnythingLLM Conversation**.
6. Saisir l’URL et la clé. La configuration vérifie l’authentification puis récupère les workspaces. Sélectionner le workspace.

Le premier appel conversationnel crée son thread ; l’ajout de l’intégration ne consomme pas une génération de modèle pour tester le chat. Un serveur peut donc valider la connexion tout en refusant ensuite un endpoint de chat incompatible.

## 4. Installation par dépôt personnalisé HACS

Les fichiers `hacs.json`, `manifest.json`, `README.md` et `custom_components/anythingllm/` sont fournis. Il n’existe pas de dépôt GitHub publié pour ce livrable et aucune adresse de dépôt fictive n’est fournie.

Pour distribuer le projet, publier le contenu de la racine de cette archive dans un dépôt GitHub que vous possédez, avec `custom_components` à sa racine. Créer une version GitHub `v1.0.0` pour identifier cette distribution. Dans HACS, ouvrir les dépôts personnalisés, ajouter **l’URL réelle de ce dépôt**, catégorie **Intégration**, puis télécharger et redémarrer HA. La procédure d’ajout de l’intégration reste identique.

Le manifeste utilise une URL officielle de documentation AnythingLLM et une liste de mainteneurs vide, puisqu’aucune identité GitHub n’a été fournie. Lors de la publication, vous pouvez renseigner votre véritable compte dans `codeowners`, et remplacer `documentation` par le README de votre dépôt réel. Ce ne sont pas des paramètres requis pour l’installation manuelle. L’acceptation dans le catalogue HACS par défaut et ses contrôles de publication n’ont pas été testés ; il s’agit d’une structure de dépôt personnalisé.

## 5. Sélectionner l’agent dans Assist

Dans **Paramètres → Assistants vocaux**, modifier l’assistant/la pipeline voulue et sélectionner l’entité **AnythingLLM — nom du workspace** comme agent de conversation. Choisir le français. Conserver les composants STT et TTS existants. Les intitulés exacts varient avec le frontend HA.

Si l’assistant est configuré pour traiter prioritairement les commandes localement, une commande peut être prise en charge par l’agent natif avant d’atteindre AnythingLLM. Désactiver cette priorité pendant les tests si nécessaire. Ce projet n’implémente pas lui-même de contrôle d’équipement.

Dans les options de l’intégration :

| Option | Valeur initiale | Effet |
|---|---|---|
| Délai maximal | 120 secondes | Budget total pour création du thread et génération ; réglable de 10 à 600 secondes |
| Mode | `chat` | Connaissances du modèle et RAG, avec historique roulant côté serveur |
| Mode alternatif | `query` | Réponses centrées sur les documents ; ne pas compter sur la continuité du contexte |
| Conservation du contexte | `threads` | Un thread distant propre à chaque conversation |
| Repli explicite | `session` | Chat du workspace avec un `sessionId` unique ; à activer uniquement si documenté localement |

Un timeout de la pipeline, du proxy ou du fournisseur de modèle peut être plus court que celui de l’intégration. Augmenter uniquement l’option HA ne corrige pas ces autres délais.

Enregistrer les options recharge l’entrée et réinitialise ses correspondances locales. **Reconfigurer** permet de changer URL, clé et workspace. Une clé refusée au chargement ou pendant un échange déclenche le mécanisme HA de réauthentification. Chaque entrée possède son propre agent ; plusieurs entrées, même vers le même workspace, restent indépendantes.

## 6. Tester une question puis le RAG

- Question simple : « Réponds en français : quelle est la capitale de l’Espagne ? »
- Question documentaire : ajouter au workspace un petit document avec une information distinctive, par exemple « Le code de démonstration du projet Orchidée est ORC-742 ». Après son intégration vectorielle, demander « D’après mon document, quel est le code du projet Orchidée ? »
- Comparer avec une question inconnue et vérifier que le modèle ne prétend pas avoir trouvé une information absente. Le choix des sources et la fiabilité factuelle restent des propriétés du modèle et du RAG.

L’API peut renvoyer des sources structurées ; cette version restitue le texte seulement, pour la voix. Elle n’ajoute pas les extraits documentaires à la réponse ni aux logs.

## 7. Continuité, isolation et réinitialisation

Avec le mode **chat**, dans une conversation A : « Retient mon code temporaire : 347. » Puis, sans commencer une nouvelle conversation : « Quel est mon code temporaire ? » Le client Assist doit réutiliser le `conversation_id` reçu et conserver le même contexte utilisateur/appareil.

Ouvrir une conversation B, puis poser seulement « Quel est mon code temporaire ? ». Elle ne doit pas recevoir l’historique de A. Vérifier également avec deux comptes HA et avec deux appareils. Pour un test déterministe, utiliser l’action `conversation.process`, sélectionner l’entité réelle dans l’interface, conserver le `conversation_id` de la première réponse pour la deuxième, puis omettre cet identifiant pour ouvrir une nouvelle conversation. Une sortie de modèle correcte seule ne prouve pas l’isolation : vérifier les threads distincts dans AnythingLLM et les tests automatisés.

L’association locale inclut utilisateur HA, appareil, identifiant aléatoire de conversation et instance de l’intégration. Un identifiant inconnu ou appartenant à une autre portée crée un nouveau contexte et un nouvel identifiant de retour. Aucun identifiant utilisateur HA n’est transmis comme `userId` AnythingLLM. Deux personnes parlant au même satellite anonyme ne sont pas distinguées par reconnaissance vocale : elles doivent ouvrir des conversations distinctes.

Le serveur conserve les messages ; HA conserve en mémoire uniquement les correspondances et le dernier résultat de chaque conversation pour dédoublonnage. Maximum 128 conversations locales, expiration après une heure d’inactivité, vérifiée à la requête suivante. Redémarrer/recharger l’entrée réinitialise toutes ses correspondances. **Cela n’efface pas les chats distants.** Les threads sont conservés dans AnythingLLM pour consultation/suppression manuelle ; aucun nettoyage destructif n’est lancé automatiquement.

Après une erreur API ou une annulation pendant une requête, la correspondance est abandonnée. La requête suivante ouvre un nouveau contexte : c’est volontaire, car le serveur a peut-être déjà enregistré le précédent message. Aucun renvoi automatique du message, aucune garantie d’« exactement une fois » après une panne réseau. Une même requête HA identifiée par le même `Context.id` est dédoublonnée si son résultat est encore le dernier de cette conversation ; un nouvel événement utilisateur est une nouvelle requête. Un deuxième appel simultané dans le même contexte est refusé comme occupé.

**Sans threads :** le choix par défaut échoue explicitement. Si votre Swagger confirme `sessionId` et sa fonction d’isolation, choisir **Session API** dans les options. Le serveur reçoit un identifiant opaque unique réutilisé uniquement dans cette conversation. L’implémentation officielle vérifiée filtre l’historique sur cet identifiant. Si votre version n’offre ni threads ni partition d’historique confirmée, cette intégration ne fournit pas de repli sûr sur cette version : ne pas activer Session API et mettre AnythingLLM à niveau. Elle ne partage jamais intentionnellement le chat global sans identifiant et ne reconstruit pas un faux historique dans le texte utilisateur.

L’isolation des conversations n’est pas une gestion des permissions documentaires : tous les utilisateurs autorisés à cet agent peuvent interroger le workspace configuré. Les administrateurs AnythingLLM ou détenteurs d’une clé API peuvent avoir un accès étendu aux données. Un workspace commun, ses documents et d’éventuelles fonctions de mémoire globale restent communs.

## 8. Diagnostic

| Erreur | Vérification |
|---|---|
| Connexion impossible | Tester DNS, IP, port, pare-feu et accès depuis HA ; vérifier que Desktop reste ouvert |
| Authentification refusée | Renouveler la clé AnythingLLM, vérifier les droits et que le proxy conserve `Authorization` ; 403 peut aussi signifier un accès interdit |
| Timeout | Vérifier le temps de réponse du modèle, le proxy et la pipeline ; aucun message n’est renvoyé automatiquement |
| Workspace absent | Reconfigurer et sélectionner un workspace encore accessible |
| Endpoint/thread absent | Comparer `/api/docs` avec `docs/API.md` ; vérifier le préfixe du proxy et la version ; ouvrir une nouvelle conversation |
| HTTP 429 | Attendre ; pas de nouvelle tentative automatique |
| HTTP 5xx | Vérifier les logs serveur et le fournisseur du modèle |
| JSON invalide | Un proxy renvoie peut-être une page HTML de connexion ou d’erreur |
| Réponse vide/abort | Tester le même workspace dans AnythingLLM et vérifier ses documents et son modèle |
| Trop de conversations | Attendre l’expiration ou recharger l’entrée ; cela réinitialise le contexte local |

L’intégration n’écrit ni clé ni conversation dans ses journaux et ne fournit pas de diagnostic exportant la configuration. Les messages d’erreur exposés sont constants et n’incluent jamais le corps reçu du serveur. Home Assistant peut conserver ses propres traces Assist, et AnythingLLM ses chats/logs : cette intégration ne désactive pas leurs mécanismes de stockage. La clé saisie de façon masquée est conservée par le stockage de configuration HA ; ce n’est pas un coffre chiffré distinct. Protéger les sauvegardes HA.

## 9. Contrôle domotique : non implémenté

La capacité `CONTROL` n’est pas déclarée. Aucune réponse libre n’est analysée comme une commande. Aucun appel de service, `eval`, Python généré, shell ou exécution de contenu RAG n’existe dans ce projet.

Une future extension nécessiterait : obtenir les outils de l’API LLM Assist officielle avec le contexte HA de l’utilisateur ; transmettre leurs schémas à un modèle ; récupérer des appels structurés avec identifiants et arguments ; les faire valider/exécuter par l’API HA ; renvoyer les résultats au modèle. Les entités exposées et les permissions devraient être appliquées à chaque appel.

Les endpoints de chat utilisés ici renvoient une réponse finale et ne fournissent pas le protocole client nécessaire pour cette boucle complète. Le fait qu’AnythingLLM ait ses propres agents, outils ou connecteurs MCP ne prouve pas qu’ils héritent du contexte et des autorisations de chaque utilisateur Assist. Aucune délégation de contrôle n’a donc été développée. Les instructions présentes dans les documents restent du contenu, jamais une autorisation.

## 10. Tests et limites de validation

Voir `docs/VALIDATION.md` pour les résultats réellement exécutés. Pour reproduire sur une machine de développement avec Python 3.13 :

```sh
python3.13 -m venv .venv
.venv/bin/python -m pip install -r requirements-test.txt
.venv/bin/python -m pytest -q
.venv/bin/ruff check .
.venv/bin/ruff format --check .
```

Les dépendances épinglées servent uniquement au laboratoire de test historique. Notamment `aiohttp==3.11.13`, imposé par HA 2025.3.4, a été retiré de la sélection automatique PyPI pour une régression ; le pin explicite permet de reproduire ce laboratoire. Ne pas remplacer les dépendances de votre Home Assistant de production par celles de ce fichier.

Il reste à valider sur votre installation : version HA réelle, contrat Swagger local, accès réseau, certificats, génération LLM, rappel RAG, isolation distante effective et expérience vocale STT/TTS. La CI fournie exécute les tests, pas un serveur AnythingLLM ni une pipeline vocale.

## Références

- [API AnythingLLM et clés](https://docs.anythingllm.com/features/api)
- [Desktop et différences Docker](https://docs.anythingllm.com/installation-desktop/overview)
- [Entité de conversation HA — source ciblée](https://github.com/home-assistant/core/blob/2025.3.4/homeassistant/components/conversation/entity.py)
- [API LLM Home Assistant](https://developers.home-assistant.io/docs/core/llm/)
- [Schéma AnythingLLM vérifié](https://github.com/Mintplex-Labs/anything-llm/blob/4d09fa5f730698d39f1d783e47316744b260a700/server/swagger/openapi.json)

Les contrats détaillés, les liens vers le code des routes et les éléments à fournir pour vérifier votre instance figurent dans `docs/API.md`.
