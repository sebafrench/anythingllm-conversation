"""Constantes et messages publics, sans données du serveur."""

DOMAIN = "anythingllm"
DEFAULT_TIMEOUT = 120
DEFAULT_MODE = "chat"
ERRORS = {
    "invalid_url": "URL invalide : indiquez http(s)://serveur:port, sans identifiants ni paramètres.",
    "invalid_auth": "Clé API refusée ou accès interdit. Réauthentifiez l’intégration.",
    "cannot_connect": "Impossible de joindre AnythingLLM. Vérifiez réseau, adresse et certificat TLS.",
    "timeout": "Délai dépassé. Le serveur a peut-être traité le message. Aucun renvoi automatique ; recommencez dans une nouvelle conversation.",
    "workspace_missing": "Le workspace sélectionné n’existe plus ou n’est plus accessible. Reconfigurez l’intégration.",
    "not_found": "Endpoint ou thread absent. Vérifiez la version et /api/docs ; ouvrez une nouvelle conversation.",
    "threads_required": "Cette version nécessite les endpoints de threads AnythingLLM. Aucun chat global n’a été utilisé.",
    "rate_limited": "AnythingLLM limite les requêtes. Patientez avant de recommencer.",
    "server_error": "AnythingLLM a rencontré une erreur serveur.",
    "invalid_response": "Réponse AnythingLLM malformée ou JSON invalide.",
    "empty_response": "AnythingLLM a renvoyé une réponse vide.",
    "request_failed": "AnythingLLM a refusé ou interrompu la requête.",
    "busy": "Une réponse est déjà en cours pour cette conversation.",
    "capacity": "Trop de conversations actives. Patientez ou rechargez l’intégration.",
    "closed": "L’intégration est en cours de rechargement.",
    "agent_disabled": "Les commandes @agent ne sont pas prises en charge par cet agent conversationnel.",
}
