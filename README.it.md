# 💧 OpenAquaero 2.2

OpenAquaero è un pannello di controllo termico open-source, nativo e leggero per Linux, progettato specificamente per la scheda **Aquacomputer Aquaero 6 LT**. Offre un'interfaccia moderna e focalizzata per la gestione degli impianti a liquido custom direttamente dal tuo ambiente desktop Linux.

## ⚠ Scopo del Progetto e Limitazioni
Questo progetto si concentra sull'offrire un'esperienza di controllo reattiva ed essenziale per i componenti principali dell'impianto. Non è da intendersi come una replica completa della suite ufficiale per Windows.
* **Hardware Supportato:** Attualmente gestisce le **4 uscite principali a 12V** (ventole e pompe).
* **Controllo in Tempo Reale:** Il software opera in modalità override in tempo reale. Il salvataggio permanente dei profili nella EPROM interna della scheda non è ancora supportato.
* **Stato PWM/DC:** Le uscite funzionano in base al loro ultimo stato hardware configurato. Lo switch via software tra le modalità PWM e DC è in fase di sviluppo.
* **Moduli Estesi:** Dispositivi Aquabus e sensori di allarme esterni complessi non sono attualmente gestiti.

## ✨ Funzionalità Principali
OpenAquaero introduce diverse funzionalità moderne pensate per l'ecosistema Linux:
- **Monitoraggio Hardware:** Legge le temperature di CPU e GPU direttamente dal kernel Linux (`sysfs`), garantendo un monitoraggio accurato e a bassissimo impatto sulle risorse, senza l'uso di demoni in background.
- **OSD Intelligente (On-Screen Display):** Un overlay fluttuante scalabile, trascinabile e senza bordi per monitorare lo stato dell'impianto a liquido in modo trasparente durante le sessioni di gioco.
- **Auto-Switch basato sui Processi:** Associa dinamicamente i profili termici ad applicazioni specifiche. Il software applicherà automaticamente il profilo di raffreddamento desiderato all'avvio di un determinato processo (es. un gioco o un software di rendering).
- **Filtro di Isteresi Regolabile:** Utilizza una media temporale dinamica per smussare i picchi improvvisi di temperatura. Questo previene sbalzi repentini nei giri delle ventole, garantendo transizioni acustiche graduali e silenziose.
- **Interfaccia Multilingua:** Tradotto nativamente in Italiano, Inglese, Tedesco, Francese e Spagnolo.

## 🛠 Installazione (Arch Linux)
1. Clona questo repository sul tuo computer.
2. Esegui `makepkg -si` per compilare il pacchetto, installarlo e applicare automaticamente le regole `udev` necessarie.
3. *(Opzionale)* Installa `python-pynvml` tramite pacman per un supporto esteso al monitoraggio hardware.

## 📜 Licenza
Rilasciato sotto **GNU GPLv3**. Questo è un progetto indipendente sviluppato dalla community e non è affiliato ad Aquacomputer.
