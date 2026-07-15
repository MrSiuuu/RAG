# Résultats de l'évaluation — RAG Dyneff

Golden set : **40 questions** (32 avec réponse, 8 trous de corpus)
Config : modèle `gpt-5.6-terra` · TOP_K=25 · TOP_N=5 · CHUNK_SIZE=800

| Métrique | Score | Ce qu'elle mesure |
|---|---|---|
| **Recall@5** | **97 %** | Le bon passage est-il récupéré ? (retrieval) |
| **Correctness** | **97 %** | La réponse est-elle juste ? (génération) |
| **Faithfulness** | **100 %** | Zéro invention ? (hallucination) |
| **Trous correctement refusés** | **100 %** | Sait-il dire « je ne sais pas » ? (prudence) |
| Taux de refus global | 20 % | Part de « je ne sais pas » sur tout le set |
| Latence moyenne | 5.0 s | Temps de réponse |
| Coût génération / question | 0.0066 € | Coût du modèle par question |

## Détail par question

| id | type | recall | correct | fidèle | refus | latence |
|---|---|:---:|:---:|:---:|:---:|---:|
| a001 | réponse | ✅ | ✅ | ✅ | non | 7.6 s |
| a002 | réponse | ✅ | ✅ | ✅ | non | 5.6 s |
| a003 | réponse | ✅ | ✅ | ✅ | non | 4.4 s |
| a004 | réponse | ✅ | ✅ | ✅ | non | 4.2 s |
| a005 | réponse | ✅ | ✅ | ✅ | non | 6.3 s |
| a006 | réponse | ✅ | ✅ | ✅ | non | 5.3 s |
| a007 | réponse | ✅ | ✅ | ✅ | non | 5.6 s |
| a008 | réponse | ✅ | ✅ | ✅ | non | 4.9 s |
| a009 | réponse | ❌ | ✅ | ✅ | non | 6.5 s |
| a010 | réponse | ✅ | ✅ | ✅ | non | 4.7 s |
| a011 | réponse | ✅ | ✅ | ✅ | non | 3.7 s |
| a012 | réponse | ✅ | ✅ | ✅ | non | 6.1 s |
| a013 | réponse | ✅ | ✅ | ✅ | non | 3.7 s |
| a014 | réponse | ✅ | ✅ | ✅ | non | 5.3 s |
| a015 | réponse | ✅ | ✅ | ✅ | non | 3.7 s |
| a016 | réponse | ✅ | ✅ | ✅ | non | 4.7 s |
| a017 | réponse | ✅ | ✅ | ✅ | non | 6.0 s |
| a018 | réponse | ✅ | ✅ | ✅ | non | 2.5 s |
| a019 | réponse | ✅ | ✅ | ✅ | non | 4.6 s |
| a020 | réponse | ✅ | ✅ | ✅ | non | 2.9 s |
| a021 | réponse | ✅ | ✅ | ✅ | non | 2.5 s |
| a022 | réponse | ✅ | ✅ | ✅ | non | 4.6 s |
| a023 | réponse | ✅ | ✅ | ✅ | non | 6.6 s |
| a024 | réponse | ✅ | ✅ | ✅ | non | 4.8 s |
| a025 | réponse | ✅ | ❌ | ✅ | non | 5.9 s |
| a026 | réponse | ✅ | ✅ | ✅ | non | 4.9 s |
| a027 | réponse | ✅ | ✅ | ✅ | non | 4.3 s |
| a028 | réponse | ✅ | ✅ | ✅ | non | 4.9 s |
| a029 | réponse | ✅ | ✅ | ✅ | non | 4.2 s |
| a030 | réponse | ✅ | ✅ | ✅ | non | 5.0 s |
| a031 | réponse | ✅ | ✅ | ✅ | non | 5.0 s |
| a032 | réponse | ✅ | ✅ | ✅ | non | 4.2 s |
| g001 | trou | — | ✅ | ✅ | oui | 4.6 s |
| g002 | trou | — | ✅ | ✅ | oui | 6.2 s |
| g003 | trou | — | ✅ | ✅ | oui | 3.0 s |
| g004 | trou | — | ✅ | ✅ | oui | 5.2 s |
| g005 | trou | — | ✅ | ✅ | oui | 3.6 s |
| g006 | trou | — | ✅ | ✅ | oui | 5.7 s |
| g007 | trou | — | ✅ | ✅ | oui | 10.3 s |
| g008 | trou | — | ✅ | ✅ | oui | 6.9 s |
