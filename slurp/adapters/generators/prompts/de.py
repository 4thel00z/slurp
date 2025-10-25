from textwrap import dedent


EASY_PROMPT = dedent(
    """Du erstellst Evaluierungsfragen für ein konversationelles RAG-System (Retrieval-Augmented Generation).

WICHTIGER KONTEXT: Die von dir generierten Fragen werden verwendet, um ein RAG-System zu testen, bei dem dieses Dokument in einer Vektordatenbank gespeichert ist. Nutzer:innen stellen Fragen, OHNE das Dokument zu sehen – vermeide daher vage Bezüge wie „dieses Dokument“, „dieses Team“, „diese Richtlinie“, „obenstehend“ usw. Verwende stattdessen konkrete Namen, Begriffe und Details aus dem Dokument.

Dokumenttitel: {title}

Dokumentinhalt:
{content}

Erstelle EINE einfache Frage, die ein:e Nutzer:in auf natürliche Weise stellen könnte, wenn sie Informationen benötigen, die typischerweise in diesem Dokument enthalten sind. Die Frage sollte:

MERKMALE:
- Durch direktes Text-Matching oder einfache Stichwortsuche beantwortbar sein
- Sich auf explizite Fakten, Definitionen oder grundlegende Details im Dokument beziehen
- In natürlicher, gesprächsnaher Sprache formuliert sein (als würde jemand einen Chatbot fragen)
- Konkret genug sein, um eine klare, sachliche Antwort zu ermöglichen

MÖGLICHE FRAGETYPEN:
- „Was ist [konkreter Begriff/Konzept]?“
- „Wie viel[e] [konkretes Detail]?“
- „Wann fand [konkretes Ereignis] statt?“
- „Wer ist verantwortlich für [konkrete Sache]?“
- „Wo befindet sich [konkreter Ort/Gegenstand]?“

BEISPIELE FÜR GUTE EINFACHE FRAGEN:
- „Was ist das Hauptziel des DevOps-Teams?“ (konkreter Teamname)
- „Wie viele Schritte umfasst der Software-Installationsprozess?“ (konkreter Prozess)
- „Welche Telefonnummer soll ich für den technischen Support anrufen?“ (konkreter Support-Typ)

VERMEIDE VAGE BEZÜGE:
- „Was ist das Ziel dieses Teams?“ (stattdessen konkreten Teamnamen verwenden)
- „Wie funktioniert dieser Prozess?“ (spezifiziere den Prozess)
- „Was steht in diesem Dokument über...?“ (direkt auf konkrete Themen verweisen)

WICHTIG: Verwende verschiedene Frageanfänge. Vermeide sich wiederholende Muster wie „Kannst du mir mehr über... erzählen?“ oder „Was kannst du mir über... sagen?“. Variiere die Fragetypen und -formate.

Erstelle EINE gesprächsnahe Frage, die grundlegendes faktisches Abrufen testet."""
)

MEDIUM_PROMPT = dedent(
    """Du erstellst Evaluierungsfragen für ein konversationelles RAG-System (Retrieval-Augmented Generation).

WICHTIGER KONTEXT: Die von dir generierten Fragen werden verwendet, um ein RAG-System zu testen, bei dem dieses Dokument in einer Vektordatenbank gespeichert ist. Nutzer:innen stellen Fragen, OHNE das Dokument zu sehen – vermeide daher vage Bezüge wie „dieses Dokument“, „diese Richtlinie“, „diese Anforderungen“, „obenstehend“ usw. Verwende stattdessen konkrete Namen, Begriffe und Details aus dem Dokument.

Dokumenttitel: {title}

Dokumentinhalt:
{content}

Erstelle EINE Frage mittleren Schwierigkeitsgrads, die ein:e Nutzer:in auf natürliche Weise stellen könnte, wenn sie Informationen suchen, die typischerweise in diesem Dokument enthalten sind. Die Frage sollte:

MERKMALE:
- Das Verknüpfen von 2–3 zusammenhängenden Informationen aus dem Dokument erfordern
- Eine gewisse Interpretation oder Erklärung über direkte Zitate hinaus verlangen
- In natürlicher, gesprächsnaher Sprache formuliert sein
- Die Fähigkeit des Systems testen, Zusammenhänge und Kontext zu verstehen

MÖGLICHE FRAGETYPEN:
- „Wie hängt [A] mit [B] zusammen?“
- „Was sind die Unterschiede zwischen [X] und [Y]?“
- „Warum ist [konkrete Sache] wichtig für [konkreten Zweck]?“
- „Was sollte ich tun, wenn [konkretes Szenario] eintritt?“
- „Wie kann ich [Ziel erreichen] basierend auf diesen Informationen?“

BEISPIELE FÜR GUTE MITTELSCHWERE FRAGEN:
- „Wie unterscheiden sich die Sicherheitsanforderungen für AWS im Vergleich zu Azure-Bereitstellungen?“ (konkrete Systeme)
- „Was ist der Zusammenhang zwischen den Budgetbeschränkungen im Q4 und dem Projektzeitplan?“ (konkrete Zeiträume/Elemente)
- „Warum könnte jemand den Premium-Tarif dem Basistarif vorziehen?“ (konkrete Tarifnamen)

VERMEIDE VAGE BEZÜGE:
- „Worin unterscheiden sich diese beiden Optionen?“ (spezifiziere die Optionen)
- „Was ist der Zusammenhang zwischen dem Budget und dem Zeitplan?“ (genauer benennen)
- „Warum könnte jemand Option A statt Option B wählen?“ (tatsächliche Begriffe/Namen verwenden)

WICHTIG: Verwende verschiedene Frageanfänge. Vermeide sich wiederholende Muster wie „Kannst du mir mehr über... erzählen?“ oder „Was kannst du mir über... sagen?“. Formuliere vielfältige, spezifische Fragen.

Erstelle EINE gesprächsnahe Frage, die Schlussfolgerungen und Verknüpfungen testet."""
)

HARD_PROMPT = dedent(
    """Du erstellst Evaluierungsfragen für ein konversationelles RAG-System (Retrieval-Augmented Generation).

WICHTIGER KONTEXT: Die von dir generierten Fragen werden verwendet, um ein RAG-System zu testen, bei dem dieses Dokument in einer Vektordatenbank gespeichert ist. Nutzer:innen stellen Fragen, OHNE das Dokument zu sehen – vermeide daher vage Bezüge wie „dieses Dokument“, „dieser Ansatz“, „diese Richtlinien“, „oben genannt“ usw. Verwende stattdessen konkrete Namen, Begriffe und Details aus dem Dokument.

Dokumenttitel: {title}

Dokumentinhalt:
{content}

Erstelle EINE anspruchsvolle Frage, die ein:e Nutzer:in auf natürliche Weise stellen könnte, wenn sie komplexe Informationen suchen, wie sie typischerweise in diesem Dokument enthalten sind. Die Frage sollte:

MERKMALE:
- Informationen aus mehreren Abschnitten oder Konzepten verknüpfen
- Rückschlüsse, Analysen oder komplexes Denken über das explizit Geschriebene hinaus erfordern
- Sonderfälle, Implikationen oder tiefgreifendes Verständnis testen
- In natürlicher, gesprächsnaher Sprache formuliert sein
- Gegebenenfalls erfordern, dass das System Lücken oder Einschränkungen in den Informationen erkennt

MÖGLICHE FRAGETYPEN:
- „Was würde passieren, wenn [hypothetisches Szenario basierend auf den Dokumentregeln]?“
- „Wie sollte ich [mehrere Optionen] priorisieren, wenn [konkrete Einschränkungen] gelten?“
- „Welche potenziellen Risiken oder Nachteile hat [genannter Ansatz]?“
- „Wie lässt sich diese Information auf [konkretes, komplexes Szenario] anwenden?“
- „Was fehlt in diesen Richtlinien, das ich trotzdem wissen sollte?“

BEISPIELE FÜR GUTE SCHWIERIGE FRAGEN:
- „Wenn ich die DSGVO in einer kleinen Organisation mit begrenzten Ressourcen umsetzen muss, worauf sollte ich den Fokus legen?“ (konkrete Vorschrift und Kontext)
- „Welche möglichen Konflikte könnten zwischen der Datenaufbewahrungsrichtlinie und den Anforderungen an den Datenschutz der Kund:innen entstehen?“ (konkrete Richtlinien)
- „Wie müsste der Incident-Response-Prozess für Notfälle am Wochenende angepasst werden?“ (konkreter Prozess und Szenario)

VERMEIDE VAGE BEZÜGE:
- „Wie müsste dieser Prozess für Notfälle angepasst werden?“ (spezifiziere den Prozess)
- „Welche Konflikte könnten zwischen diesen Anforderungen entstehen?“ (nennen der konkreten Anforderungen)
- „Wenn ich das in einer kleinen Organisation umsetzen muss...“ (spezifizieren, worauf sich „das“ bezieht)

WICHTIG: Verwende verschiedene Frageanfänge. Vermeide sich wiederholende Muster wie „Kannst du mir mehr über... erzählen?“ oder „Was kannst du mir über... sagen?“. Sei kreativ und konkret.

Erstelle EINE gesprächsnahe Frage, die komplexes Denken und Synthesefähigkeit testet"""
)

MIXED_PROMPT = dedent(
    """Du erstellst Evaluierungsfragen für ein konversationelles RAG-System (Retrieval-Augmented Generation).

WICHTIGER KONTEXT: Die von dir generierten Fragen werden verwendet, um ein RAG-System zu testen, bei dem dieses Dokument in einer Vektordatenbank gespeichert ist. Nutzer:innen stellen Fragen, OHNE das Dokument zu sehen – vermeide daher vage Bezüge wie „dieses Dokument“, „diese Information“, „obenstehend“, „diese Richtlinien“ usw. Verwende stattdessen konkrete Namen, Begriffe und Details aus dem Dokument.

Dokumenttitel: {title}

Dokumentinhalt:
{content}

Erstelle EINE Frage, die ein:e Nutzer:in auf natürliche Weise stellen könnte, wenn sie Informationen suchen, die typischerweise in diesem Dokument enthalten sind.

ADAPTIVE SCHWIERIGKEIT:
- Bei einfachen Dokumenten: Fokus auf Faktenfragen und grundlegendes Verständnis
- Bei komplexen Dokumenten: Fragen mit Begründungen, Vergleichen oder Anwendungen
- Bei technischen Dokumenten: Verständnis von Konzepten und deren praktische Anwendung prüfen
- Bei Richtliniendokumenten: Verständnis der Regeln und deren Anwendung in Szenarien prüfen

MERKMALE DER FRAGE:
- In natürlicher, gesprächsnaher Sprache formuliert (wie in einem Gespräch mit einem hilfreichen Assistenten)
- Wenn möglich, spezifisch und handlungsorientiert
- Entspricht der Komplexität und Tiefe des Ausgangsmaterials
- Testet die wichtigsten oder nützlichsten Aspekte des Dokuments

MÖGLICHE FRAGETYPEN (je nach Inhalt wählen):
BASIS: „Was ist [konkreter Begriff]...“, „Wie viele [konkrete Elemente]...“, „Wann findet [konkretes Ereignis] statt...“
BEGRÜNDUNG: „Wie hängt [System A] mit [System B] zusammen?“, „Was ist der Unterschied zwischen [Option X] und [Option Y]...“
ANWENDUNG: „Was sollte ich tun, wenn [konkretes Szenario] eintritt?“, „Wie kann ich [konkreten Prozess] anwenden auf...“
SYNTHESEN: „Was würde passieren, wenn [konkrete Bedingung]?“, „Wie wirken [konkrete Anforderungen] zusammen?“

VERMEIDE VAGE BEZÜGE – Sei immer spezifisch:
❌ „Was sollte ich tun, wenn das passiert?“
✅ „Was sollte ich tun, wenn der Server während der Bereitstellung abstürzt?“

❌ „Wie hängt das mit jenem zusammen?“
✅ „Wie hängt die Backup-Richtlinie mit dem Notfallwiederherstellungsprozess zusammen?“

WICHTIG: Verwende verschiedene Frageanfänge. Vermeide sich wiederholende Muster wie „Kannst du mir mehr über... erzählen?“. Formuliere vielfältige, konkrete Fragen, die zum Dokumentinhalt passen.

Erstelle EINE gesprächsnahe Frage, die zur Komplexität dieses Dokuments passt.
"""
)

ANSWER_AND_CHUNKS_PROMPT = dedent(
    """Du bist Expert:in für das Beantworten von Fragen und das Identifizieren relevanter Dokumentabschnitte für die Evaluation von RAG-Systemen.

Dokumentinhalt:
{content}

Frage:
{question}

Bitte liefere:
1. Eine umfassende, präzise Antwort auf die Frage
2. Zwei bis drei relevante Abschnitte (Chunks) aus dem Dokument, die deine Antwort stützen

Stelle sicher, dass die Antwort ausführlich ist und die gewählten Abschnitte die relevantesten Stellen im Dokument sind, die deine Antwort belegen.
"""
)

HIERARCHICAL_PROMPT = dedent(
    """Du bist Expert:in für das Erstellen von Fragen zur Evaluation von RAG-Modellen mit hierarchisch aufgebauten Dokumentenstrukturen.

Dokumenttitel: {title}
Hierarchie-Kontext: {hierarchy_context}

Dokumentinhalt:
{content}

Erstelle EINE anspruchsvolle, nicht-triviale Frage, die:
1. Ein Verständnis des Dokumentinhalts erfordert
2. Sich auf den hierarchischen Kontext (Eltern-Kind-Beziehungen) beziehen kann
3. Nicht durch einfache Schlagwortsuche beantwortet werden kann
4. Eine Synthese von Informationen voraussetzt
5. Spezifisch und detailliert ist
6. Nützlich ist, um die Fähigkeit eines RAG-Systems zu testen, Dokumentbeziehungen zu verstehen
"""
)

CROSS_PAGE_PROMPT = dedent(
    """Du bist Expert:in für das Erstellen von seitenübergreifenden Fragen zur Evaluation von RAG-Modellen.

Kombinierter Inhalt aus über- und untergeordneten Seiten mit Titeln, Inhalten und URLs:
{combined_content}

Erstelle EINE anspruchsvolle Frage, die:
1. Informationen aus mehreren zusammenhängenden Seiten erfordert
2. Inhalte zwischen der übergeordneten und den untergeordneten Seiten vergleicht oder zusammenführt
3. Die Fähigkeit des RAG-Systems testet, Beziehungen zwischen Dokumenten zu verstehen
4. Nicht durch das Betrachten nur einer einzelnen Seite beantwortet werden kann
5. Spezifisch ist und Querverweise notwendig macht
"""
)

LONG_EASY_PROMPT = dedent(
    """Du erstellst Evaluierungsanfragen für ein konversationelles RAG-System (Retrieval-Augmented Generation), das auf mehrere Dokumente zugreifen kann.

WICHTIGER KONTEXT: Die von dir generierten Anfragen werden verwendet, um ein RAG-System zu testen, bei dem diese Dokumente in einer Vektordatenbank gespeichert sind. Nutzer:innen stellen Fragen, OHNE die Dokumente zu sehen – vermeide daher vage Formulierungen wie „diese Dokumente“, „siehe oben“, „diese Informationen“ usw. Verwende stattdessen spezifische Namen, Begriffe und Details aus dem Dokumentinhalt.

Mehrere Dokumente:
{content}

Erstelle EINE LANGE, DETAILLIERTE Anfrage, die ein:e Nutzer:in stellen könnte, wenn umfassende Informationen über mehrere dieser Dokumente hinweg benötigt werden. Die Anfrage MUSS folgende Anforderungen erfüllen:

ERFORDERLICHES FORMAT:
- **Mehrere Sätze**: Mindestens 2–3 vollständige Sätze
- **Kontextbezogen**: Enthält Hintergrund, Situation oder Einschränkungen der anfragenden Person
- **Detailliert**: Liefert spezifischen Kontext und Anforderungen
- **Umfassend**: Fragt nach einer gründlichen, facettenreichen Antwort

MÖGLICHE ANFRAGEFORMATE (wähle eines):
1. **Kontextbezogenes Problem**: Nutzer:in beschreibt Situation/Rolle und bittet um umfassende Hilfe
2. **Szenariobasierte Anfrage**: Nutzer:in beschreibt ein Szenario und bittet um schrittweise Anleitung
3. **Strategische Analyse**: Nutzer:in braucht Analyse komplexer Sachverhalte mit mehreren Aspekten
4. **Mehrteilige Anfrage**: Nutzer:in stellt mehrere zusammenhängende Fragen mit Kontext

MERKMALE:
- Beziehen sich auf mehrere Dokumente für umfassende Informationen
- Enthalten realistische Einschränkungen (Budget, Zeit, Ressourcen, Vorschriften)
- Nennen die Rolle oder Perspektive des Nutzers (z. B. Manager:in, Entwickler:in, neue Mitarbeitende)
- Bitten um umsetzbare, detaillierte Antworten
- Klingen wie reale geschäftliche oder organisatorische Anfragen

BEISPIELE FÜR ANFRAGEN:

**Kontextbezogene Anfragen:**
- „Ich bin neu im Unternehmen und muss unseren Deployment-Prozess verstehen. Welche wichtigen Schritte sind für das Deployment in die Produktion erforderlich?“
- „Mein Vorgesetzter hat mich gebeten, unsere Sicherheitsrichtlinien zu prüfen. Was sind die wichtigsten Anforderungen an die Authentifizierung externer Nutzer?“

**Szenariobasierte Anfragen:**
- „Ich richte eine neue Entwicklungsumgebung ein. Welche Tools und Zugriffsrechte benötige ich? Kannst du mir die Anforderungen Schritt für Schritt erklären?“
- „Wir stellen ein neues Teammitglied ein, das remote arbeitet. Welche Zugangs- und Einrichtungsprozesse muss ich beachten?“

**Mehrteilige Anfragen:**
- „Wie sieht unser aktueller Backup-Plan aus und wie lange speichern wir die Daten? Und an wen wende ich mich, wenn es ein Problem mit dem Backup gibt?“

VERMEIDE VAGE FORMULIERUNGEN:
- ❌ „Was ist der Zweck dieses Teams?“ → ✅ „Was ist der Zweck des DevOps-Teams?“
- ❌ „Wie funktioniert dieser Prozess?“ → ✅ „Wie funktioniert der Bereitstellungsprozess für neue Softwareversionen?“
- ❌ „Was sagen diese Dokumente über...?“ → ✅ „Was sagen die Sicherheitsrichtlinien über den Passwortwechselprozess?“

WICHTIG: Verwende verschiedene Formate und Einstiege. Vermeide sich wiederholende Formulierungen wie „Kannst du mir mehr erzählen über...“. Nutze unterschiedliche Anfragetypen und einen natürlichen Gesprächsstil.

Erstelle EINE konversationelle Anfrage, die grundlegende Faktenrecherche über mehrere Dokumente hinweg testet.
"""
)

LONG_MEDIUM_PROMPT = dedent(
    """Du erstellst Evaluierungsanfragen für ein konversationelles RAG-System (Retrieval-Augmented Generation), das auf mehrere Dokumente zugreifen kann.

WICHTIGER KONTEXT: Die generierten Anfragen werden verwendet, um ein RAG-System zu testen, bei dem diese Dokumente in einer Vektordatenbank gespeichert sind. Nutzer:innen stellen Fragen, OHNE die Dokumente zu sehen – vermeide daher vage Formulierungen wie „diese Dokumente“, „die Richtlinien“, „die Anforderungen“ usw. Verwende stattdessen spezifische Begriffe, Namen und Details aus dem Dokumentinhalt.

Mehrere Dokumente:
{content}

Erstelle EINE mittel-schwere Anfrage, die ein:e Nutzer:in natürlich stellen würde, wenn Informationen benötigt werden, die sich über mehrere Dokumente erstrecken. Die Anfrage kann folgendes Format haben:

MÖGLICHE ANFRAGEFORMATE:
1. **Komplexe Frage**: Verlangt das Verknüpfen mehrerer Informationsquellen
2. **Vergleichsanfrage**: Nutzer:in möchte Optionen oder Ansätze vergleichen
3. **Kontextbezogenes Problem**: Nutzer:in schildert eine Situation und bittet um Orientierung
4. **Prozessorientierte Anfrage**: Nutzer:in möchte einen Ablauf verstehen, der mehrere Bereiche umfasst

MERKMALE:
- Verknüpft 2–3 zusammenhängende Informationen aus verschiedenen Dokumenten
- Benötigt Interpretation oder Erklärung über wörtliche Zitate hinaus
- Verwendet natürliche, konversationelle Sprache
- Testet die Fähigkeit des Systems, Beziehungen und Kontexte zwischen Dokumenten zu verstehen
- Kann Vergleiche oder Abwägungen zwischen Quellen erfordern

BEISPIELE FÜR ANFRAGEN:

**Komplexe Fragen:**
- „Wie unterscheiden sich die Sicherheitsanforderungen für AWS-Deployments von denen bei Azure, und welche Option wäre besser für ein kleines Team geeignet?“

**Vergleichsanfragen:**
- „Ich überlege, ob ich den Premium- oder den Basissupport wählen soll. Kannst du die Reaktionszeiten, Leistungen und Kosten vergleichen, damit ich weiß, was besser zu einem Startup mit kleinem Budget, aber hoher Ausfallsicherheit passt?“

**Kontextbezogene Probleme:**
- „Wir planen nächsten Monat die Migration unserer Infrastruktur. Ich muss verstehen, wie sich das auf unseren aktuellen Backup-Zeitplan und die Notfallwiederherstellung auswirkt. Unser Team ist klein, und Ausfallzeiten sollten minimal bleiben. Was muss ich beachten?“

**Prozessorientierte Anfragen:**
- „Ich bin die neue Projektleitung und möchte verstehen, wie unser Entwicklungsworkflow mit dem Deployment-Prozess verknüpft ist. Welche Genehmigungen sind erforderlich, wer ist involviert, und wo können mögliche Engpässe entstehen?“

**Anfragen im Absatzstil:**
- „Unser Kunde fragt nach unseren Datenaufbewahrungsrichtlinien im Hinblick auf die DSGVO. Er möchte wissen, wie lange wir unterschiedliche Datentypen speichern, wie der Löschprozess aussieht und an wen er sich wenden kann, wenn er eine Datenlöschung wünscht. Kannst du mir helfen, unsere aktuellen Richtlinien so zu verstehen, dass ich fundiert antworten kann?“

VERMEIDE VAGE FORMULIERUNGEN:
- ❌ „Wie unterscheiden sich diese beiden Optionen?“ → ✅ „Wie unterscheiden sich die Sicherheitsstrategien zwischen dem Basis- und dem erweiterten Supportplan?“
- ❌ „Was ist der Zusammenhang zwischen Budget und Zeitplan?“ → ✅ „Wie beeinflusst das Entwicklungsbudget für das Q4 den geplanten Rollout-Termin für das neue Feature-Set?“

WICHTIG: Verwende abwechslungsreiche Formate und einen natürlichen Gesprächsstil. Vermeide sich wiederholende Satzmuster.

Erstelle EINE konversationelle Anfrage, die Schlussfolgerungen und Verknüpfungen über mehrere Dokumente hinweg erfordert.
"""
)

LONG_HARD_PROMPT = dedent(
    """Du erstellst Evaluierungsanfragen für ein konversationelles RAG-System (Retrieval-Augmented Generation), das auf mehrere Dokumente zugreifen kann.

WICHTIGER KONTEXT: Die generierten Anfragen werden verwendet, um ein RAG-System zu testen, bei dem diese Dokumente in einer Vektordatenbank gespeichert sind. Nutzer:innen stellen Fragen, OHNE die Dokumente zu sehen – vermeide daher vage Formulierungen wie „diese Dokumente“, „die Ansätze“, „die Richtlinien“ usw. Verwende stattdessen spezifische Begriffe, Namen und Details aus dem Dokumentinhalt.

Mehrere Dokumente:
{content}

Erstelle EINE anspruchsvolle Anfrage, die ein:e Nutzer:in natürlich stellen würde, wenn komplexe Informationen benötigt werden, die sich über mehrere Dokumente erstrecken. Die Anfrage kann folgende Formate haben:

MÖGLICHE ANFRAGEFORMATE:
1. **Strategische Analyse**: Nutzer:in muss komplexe Szenarien mit mehreren Variablen analysieren
2. **Problembezogene Anfrage**: Nutzer:in schildert ein komplexes Problem, das eine vielschichtige Lösung erfordert
3. **Planungsanfrage**: Nutzer:in benötigt umfassende Planung unter Einbeziehung mehrerer Systeme/Prozesse
4. **Risikobewertung**: Nutzer:in möchte Auswirkungen und Abwägungen verstehen
5. **Ausführliches Narrativ**: Nutzer:in gibt detaillierten Kontext und bittet um eine umfassende Einschätzung

MERKMALE:
- Verlangt die Synthese von Informationen aus mehreren Dokumenten und Konzepten
- Erfordert Schlussfolgerungen, Analysen oder komplexe Überlegungen, die über explizite Inhalte hinausgehen
- Testet Randfälle, Auswirkungen oder tieferes Verständnis über Dokumentgrenzen hinweg
- Verwendet natürliche, konversationelle Sprache mit realistischer Komplexität
- Kann Lücken, Widersprüche oder Einschränkungen in Dokumenten erkennen lassen
- Prüft, ob das System Informationen integrieren und differenzierte Antworten geben kann

BEISPIELE FÜR ANFRAGEN:

**Strategische Analyse:**
- „Wir sind ein schnell wachsendes SaaS-Unternehmen und überlegen, SOC-2-Konformität umzusetzen. Gleichzeitig möchten wir unsere agile Entwicklungspraxis beibehalten und die Kosten im Rahmen halten. Basierend auf unseren aktuellen Sicherheitsrichtlinien und Entwicklungsprozessen: Welcher Implementierungsansatz ist am praktikabelsten, welche Ressourcen sind erforderlich, und wo liegen mögliche Zielkonflikte zwischen Compliance-Anforderungen und unserem bestehenden Workflow?“

**Problembezogene Anfrage:**
- „Unsere europäischen Kund:innen fordern kürzere Reaktionszeiten, doch unsere Supportstruktur und Eskalationsprozesse sind auf eine einzige Zeitzone ausgelegt. Zudem haben wir im aktuellen Quartal Budgetbeschränkungen. Welche Änderungen wären nötig an unseren Support-Richtlinien, Personalressourcen und Incident-Response-Verfahren, und welche Kostenfolgen wären zu erwarten?“

**Planungsanfrage:**
- „Unser Unternehmen plant nächstes Jahr ein umfassendes Infrastruktur-Upgrade: Umstieg von On-Premise auf Cloud, Aktualisierung der Backup-Systeme und Einführung neuer Sicherheitsrichtlinien. Ich muss verstehen, wie sich diese Änderungen auf unsere Notfallwiederherstellung, Compliance-Vorgaben und den Tagesbetrieb auswirken. Welche Abhängigkeiten bestehen, welche Reihenfolge ist sinnvoll, und mit welchen Risiken sollte ich rechnen?“

**Risikobewertung:**
- „Wir erwägen, unserem DevOps-Team Fernzugriff auf produktive Systeme zu erlauben. Ich bin jedoch wegen der aktuellen Authentifizierungsrichtlinien und Prüfpflichten besorgt. Welche Risiken entstehen dabei, welche zusätzlichen Sicherheitsmaßnahmen wären erforderlich, und wie würde sich das auf unsere Incident-Response-Prozesse auswirken, falls etwas schiefläuft?“

**Ausführliches Narrativ:**
- „Ich bin IT-Leiter bei einem mittelgroßen Finanzdienstleister und stehe unter Druck, die Betriebskosten zu senken und gleichzeitig unsere Cybersicherheit nach einem branchenspezifischen Vorfall zu verbessern. Die Geschäftsführung möchte die Vor- und Nachteile unterschiedlicher Ansätze zur Sicherheitsautomatisierung sowie von ausgelagerten versus internen Lösungen verstehen – insbesondere im Hinblick auf unsere Compliance-Verpflichtungen. Wir haben rund 200 Mitarbeitende in drei Büros, mit einer Mischung aus Legacy- und modernen Systemen, und ein begrenztes Budget für größere Veränderungen im laufenden Geschäftsjahr. Kannst du mir helfen, Optionen zu analysieren und eine fundierte Empfehlung zu formulieren, die sowohl finanzielle als auch sicherheitstechnische Aspekte berücksichtigt?“

VERMEIDE VAGE FORMULIERUNGEN:
- ❌ „Wie müsste dieser Prozess angepasst werden?“ → ✅ „Wie müsste der Incident-Response-Prozess unter Berücksichtigung von SOC-2-Anforderungen angepasst werden?“
- ❌ „Was sind die Auswirkungen dieser Änderungen?“ → ✅ „Was sind die Auswirkungen der Umstellung auf Cloud-Backup in Bezug auf unser Audit-Log und die DSGVO-Konformität?“

WICHTIG: Verwende unterschiedliche Formate und realistische Komplexität. Erstelle Anfragen, die wie echte geschäftliche Herausforderungen klingen.

Erstelle EINE konversationelle Anfrage, die komplexes Denken und Synthese über mehrere Dokumente hinweg testet.
"""
)

LONG_MIXED_PROMPT = dedent(
    """Du erstellst Evaluierungsanfragen für ein konversationelles RAG-System (Retrieval-Augmented Generation), das auf mehrere Dokumente zugreifen kann.

WICHTIGER KONTEXT: Die generierten Anfragen werden verwendet, um ein RAG-System zu testen, bei dem diese Dokumente in einer Vektordatenbank gespeichert sind. Nutzer:innen stellen Fragen, OHNE die Dokumente zu sehen – vermeide daher vage Bezüge wie „diese Dokumente“, „diese Informationen“, „siehe oben“ usw. Verwende stattdessen konkrete Namen, Begriffe und Details aus dem Dokumentinhalt.

Mehrere Dokumente:
{content}

Erstelle EINE Anfrage, die ein:e Nutzer:in natürlich stellen würde, um Informationen zu erhalten, die sich über mehrere dieser Dokumente erstrecken. Die Anfrage kann in jedem Format erfolgen – von einfachen Fragen bis hin zu komplexen, paragraphenartigen Anforderungen.

ADAPTIVE KOMPLEXITÄT:
- Bei einfachen Dokumenten: Fokus auf Faktenfragen und grundlegendes Verständnis über mehrere Dokumente hinweg
- Bei komplexen Dokumenten: Einbezug von Schlussfolgerungen, Vergleichen oder Anwendungsbezügen über mehrere Quellen
- Bei technischen Dokumenten: Prüfung des Verständnisses von Konzepten und deren praktischer Anwendung über mehrere Dokumente hinweg
- Bei Richtliniendokumenten: Test von Regelverständnis und deren Anwendung in realistischen Szenarien mithilfe mehrerer Quellen

MÖGLICHE ANFRAGEFORMATE (je nach Inhalt und gewünschter Komplexität):
1. **Einfache Fragen**: Direkt und unkompliziert
2. **Kontextbezogen**: Nutzer:in schildert kurz den Hintergrund, dann folgt die Frage
3. **Szenario-basiert**: Nutzer:in beschreibt eine Situation
4. **Vergleichend**: Optionen oder Vorgehensweisen werden gegenübergestellt
5. **Problemorientiert**: Komplexes Problem soll gelöst werden
6. **Mehrteilig**: Zusammenhängende Folgefragen
7. **Narrativ**: Ausführlicher Kontext, mit umfassender Anforderung

MERKMALE DER ANFRAGE:
- Verwende natürliche, gesprächsartige Sprache (wie mit einem hilfreichen Assistenten)
- Sei möglichst spezifisch und handlungsorientiert
- Passe Tiefe und Komplexität der Anfrage an das Quellmaterial an
- Teste die wichtigsten oder nützlichsten Aspekte über die Dokumente hinweg
- Kann Informationen aus mehreren Dokumenten benötigen, aber sollte immer zum Komplexitätsgrad passen
- Reicht von kurzen Fragen bis zu paragraphenlangen Anfragen

BEISPIELFORMATE:

**Kurz & direkt:**
- „Wie lautet die Aufbewahrungsrichtlinie für Backups von Produktionsdatenbanken?“

**Mit Kontext:**
- „Ich richte derzeit ein Monitoring für unsere neue Microservices-Architektur ein. Welche Alarm-Schwellenwerte sollte ich gemäß unseren Incident-Response-Verfahren konfigurieren?“

**Szenario-basiert:**
- „Wir expandieren im nächsten Quartal auf den europäischen Markt und müssen die DSGVO einhalten. Welche Änderungen müssen wir an unserer Datenerfassung, -speicherung und -löschung vornehmen?“

**Vergleichend:**
- „Ich muss entscheiden, ob wir zuerst Single Sign-on oder Multi-Faktor-Authentifizierung implementieren – unter Berücksichtigung unseres IT-Sicherheitsbudgets. Was sind die Vor- und Nachteile, und welche Maßnahme hätte den größten kurzfristigen Effekt auf unser Risikoprofil?“

**Problemorientierte Anfrage im Paragraphenstil:**
- „Unser Entwicklungsteam wächst schnell, und es kommt häufiger zu Problemen bei Deployments. Das QA-Team sagt, es braucht mehr Testzeit, während das Produktteam schnellere Releases fordert. Basierend auf unseren aktuellen Entwicklungs- und Deploymentprozessen: Welche Verbesserungen würden helfen, die Qualität zu sichern und gleichzeitig aggressive Zeitpläne einzuhalten? Besonders interessieren mich die Auswirkungen auf Rollback-Fähigkeiten und Incident-Response.“

VERMEIDE VAGE FORMULIERUNGEN – Sei immer konkret:
❌ „Was soll ich tun, wenn das passiert?“
✅ „Was soll ich tun, wenn der primäre Datenbankserver während der Hauptgeschäftszeit ausfällt?“

❌ „Wie hängt das mit jenem zusammen?“
✅ „Wie hängt die Backup-Strategie mit unseren Notfallwiederherstellungsverfahren für kundenseitige Systeme zusammen?“

WICHTIG: Verwende unterschiedliche Anfrageformate und gesprächsnahe Sprache. Erstelle Anfragen, die zur Komplexität der Dokumente passen und wie reale Nutzeranliegen klingen.

Erstelle EINE konversationelle Anfrage, die zur Komplexität dieser Dokumente passt.
"""
)
