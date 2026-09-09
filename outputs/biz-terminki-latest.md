# Business — Termin-/Anruf-KI  ·  Kunden
> 2026-09-09_0013 · via gemini

Hier ist die konkrete Vorschau für die Demo, die du dem Betriebsinhaber direkt im Gespräch über den Lautsprecher vorspielst. Sie nutzt die extrem geringe Latenz und natürliche Tonalität unseres Rencora-Voice-Stacks.

---

### SZENARIO
**„Montagmorgen im Handwerk: Heizungsausfall vs. Wartungsanfrage“**  
*(Betrieb: Sanitär & Heizung Meisterbetrieb, Kundenanruf während die Monteure unterwegs sind)*

*   **Anrufer:** „Guten Tag, Schmidt hier. Bei uns im Keller tropft ein Rohr massiv und das Wasser steht schon leicht. Außerdem wollte ich fragen, wann Sie Zeit für die jährliche Heizungswartung haben?“
*   **KI (Alex):** „Guten Tag Herr Schmidt, keine Sorge, das kriegen wir hin. Damit der Schaden klein bleibt: Wissen Sie, wo der Hauptwasserhahn liegt und können Sie ihn sofort zudrehen?“
*   **Anrufer:** „Ja, das mache ich gleich!“
*   **KI (Alex):** „Perfekt. Ich markiere das direkt als Notfall. Ich habe Ihre Nummer im Display. Unter welcher Adresse steht das Haus?“
*   **Anrufer:** „Hauptstraße 14 in Musterstadt.“
*   **KI (Alex):** „Alles klar. Ich habe unserem Notdienst-Monteur gerade eine Eilmeldung geschickt, er meldet sich in max. 15 Minuten bei Ihnen. Die Routine-Wartung machen wir direkt danach aus – ich schicke Ihnen jetzt einen Link per SMS für Ihren Wunschtermin nächste Woche. Haben Sie das SMS-Geräusch bekommen?“
*   **Anrufer:** „Ja, ist da. Danke!“
*   **KI (Alex):** „Sehr gerne. Bitte jetzt den Wasserhahn zudrehen, wir melden uns sofort. Auf Wiederhören!“

---

### WAS ES ZEIGT
1.  **Menschliche Gesprächsführung (Rencora Stack):** Antwortzeiten unter 800ms, natürliche Betonung, Unterbrechungen durch den Anrufer sind problemlos möglich (Interrupt-Handling).
2.  **Intelligente Qualifizierung:** Die KI unterscheidet im selben Satz zwischen *akutem Notfall* (sofortige Priorisierung) und *Standard-Anfrage* (automatisierte Buchung).
3.  **Stressreduktion & Sicherheit:** Klare Handlungsanweisung an den Anrufer („Hauptwasserhahn zudrehen“), um Folgeschäden zu minimieren.
4.  **Multi-Channel-Aktion:** Gleichzeitige SMS-Ausspielung (Terminlink) und Benachrichtigung an den Notdienst-Monteur (Slack/WhatsApp/E-Mail/CRM), ohne dass ein Mitarbeiter das Telefon berühren musste.

---

### ERSTER TAG
*(So sieht die Integration für den Betrieb an Tag 1 aus – absolut barrierefrei)*

1.  **Rufumleitung aktivieren:** Der Betrieb richtet bei seinem bestehenden Anbieter (Telekom, Vodafone, Sipgate etc.) einfach eine Bedingte Rufumleitung ein (*„Wenn besetzt“* oder *„Nach 15 Sekunden Nichtmelden“* an unsere KI-Nummer).
2.  **Kalender-Sync:** Anbindung an den Google Kalender, Outlook oder das Praxis-/Branchen-System (z. B. Doctolib, Handwerker-Software).
3.  **Scharfschaltung:** Ab Minute 1 geht kein Auftrag und kein Patient mehr verloren. Der Betrieb arbeitet weiter wie bisher, erhält aber nur noch vorqualifizierte Termine und strukturierte Zusammenfassungen per Mail/SMS.
