# 💧 AquaControl 5.0

<p align="center">
  <img width="100%" alt="AquaControl Desktop Environment" src="https://github.com/user-attachments/assets/efbfd2c3-da86-43a8-8a79-99fb95e6eaa7" />
</p>

### Scopo del progetto

AquaControl è una suite di controllo nativa per Linux, scritta specificamente per
l'ecosistema Aquacomputer e per la logica dell'Aquaero 6 LT e del Farbwerk 360. Mira a
offrire le stesse funzionalità della suite ufficiale per la gestione di impianti a liquido
custom, ponendosi come alternativa Linux al noto CoolerControl che supporta molti più
dispositivi ma non offre i controlli avanzati di questo software. È inoltre, a oggi, l'unico
software Linux nativo a supportare la gestione dei LED del Farbwerk 360.

### Lettura dei sensori e motore di calcolo

Per la lettura dei sensori esposti in `/sys/class/hwmon`, AquaControl si appoggia in parte al
driver ufficiale del kernel Linux (`aquacomputer_d5next` di Aleksa Savic). Sopra queste
letture innesta un motore di calcolo indipendente, che scrive in tempo reale i valori da 0 a
255 con cui pilota i quattro canali dell'Aquaero 6 LT.

### Reverse engineering dei protocolli USB

Il modulo del kernel non permette di cambiare il tipo di erogazione (PWM/DC) dei quattro
canali 12 V, né di gestire la calibrazione dei sensori di flusso. Per colmare queste lacune
ho analizzato il traffico USB con Wireshark e ho integrato dei moduli che comunicano
direttamente con la scheda tramite `python-hidapi`. Con lo stesso metodo sono riuscito a far
funzionare il Farbwerk 360 e a catturare il payload necessario per salvare le impostazioni
nella sua EEPROM.

A differenza del Farbwerk 360, AquaControl non salva le impostazioni nella EEPROM
dell'Aquaero 6 LT: lavora in modalità override in tempo reale, per scelta dell'autore.

### Architettura: i servizi in background

AquaControl adotta un'architettura client/server basata su due servizi in background, così le
sue funzioni essenziali continuano a lavorare anche quando l'interfaccia grafica è chiusa.

**Il servizio root (`aquacontrold`)** si occupa del lavoro sull'hardware. Gira con i
privilegi di sistema, si avvia all'accensione (ancora prima del login), e controlla i
quattro canali dell'Aquaero 6 LT secondo il profilo scelto nell'interfaccia. Applica anche le
regole di sicurezza (soglie di temperatura, RPM, flusso e tensione) e, se una condizione
critica persiste, esegue lo spegnimento d'emergenza. Lo stesso servizio pilota il Farbwerk
360, applicando il profilo di colori ed effetti salvato all'avvio, alla ripresa dalla
sospensione o ogni volta che lo modifichi nell'interfaccia. Poiché lavora in modo
indipendente dall'interfaccia grafica, queste funzioni operano senza alcun utente connesso e
senza finestre aperte — per esempio il profilo del Farbwerk viene applicato all'avvio del
sistema, interamente in background, senza che AquaControl venga mai aperto.

**Il servizio utente (`aquacontrol-agent`)** gira all'interno della sessione desktop e parte
al login. 
Quando scatta un allarme mostra un avviso, riproduce un suono ed esegue subito il comando
personalizzato che hai definito nell'interfaccia, per esempio poco prima che il servizio
root proceda con lo spegnimento forzato. Mostra inoltre un riepilogo diagnostico dopo uno
spegnimento forzato, così scopri sempre cos'è successo e perché, anche se nel frattempo non
hai più riaperto l'interfaccia. In aggiunta, il demone utente gestisce anche la funzionalità
di autoswitch tra un profilo e l'altro, cosi' da permettere il cambio del profilo in base all'
apertura di uno specifico programma anche quando la GUI e' chiusa.

## 🚀 Funzionalità di AquaControl 5.0

<p align="center">
  <img width="100%" alt="AquaControl Dashboard" src="https://github.com/user-attachments/assets/cd41c603-876e-483f-8d31-5eeeb5d0464f" />
</p>

- **Interfaccia grafica e supporto multilingua**: L'interfaccia grafica è ispirata a quella di altri software che ritengo ben progettati con una ragionata organizzazione delle funzioni, concepita per essere "user friendly". Per rendere il software accessibile a chiunque, è stato tradotto in italiano, inglese, tedesco, spagnolo, francese, russo e cinese semplificato e integra all'interno del programma stesso un manuale (anch'esso tradotto) per descrivere l'uso delle funzioni avanzate del programma.

- **Controllo PWM/DC:** Come spiegato sopra, switch a caldo bypassando le limitazioni del kernel.
- **Calibrazione Sensori di Flusso:** Possibilità di calibrare i valori di imp/L in base al tipo di sensore utilizzato, al fluido refrigerante e al tipo di raccordo. È possibile impostare il parametro manualmente per sensori non in elenco come nel software originale.

- **Gestione Curve:** Il software permette di gestire l'erogazione di ogni canale attraverso quattro modalità distinte:
  - **Modalità Automatica:** Creazione di una curva di erogazione basata su parametri impostabili dall'utente (Temperatura minima/massima, Potenza minima/massima e Curvatura/Gamma).
  - **Modalità Manuale:** Impostazione della curva di erogazione punto per punto tramite un grafico interattivo.
  - **Modalità PID:** Utilizzo di un algoritmo (Proporzionale, Integrale, Derivativo) per variare dinamicamente l'erogazione di potenza al fine di mantenere una temperatura target costante su un sensore a scelta dell'utente. Include 3 comportamenti preimpostati (*Lento, Normale, Veloce*) e una modalità manuale.
  - **Modalità Fissa:** Impostazione di un valore di potenza costante.

<p align="center">
  <img width="100%" alt="AquaControl Curve Management" src="https://github.com/user-attachments/assets/e397cf3c-6723-45f8-a2fa-bedb90803626" />
</p>

- **Isteresi**: Calcola un valore medio di temperatura sulla base dei valori misurati in un determinato arco di tempo (personalizzabile) evitando la continua accelerazione/decelerazione delle ventole a causa di minime variazioni di temperatura.

- **Avvio Rapido (Start Boost):** È necessaria una maggiore potenza per avviare un rotore rispetto alla potenza necessaria per mantenerlo in movimento. La funzione "avvio rapido" permette di applicare una potenza iniziale del 100% per una frazione di secondo per vincere l'inerzia statica del rotore, per poi assestarsi al valore di potenza richiesto in base alle impostazioni scelte dall'utente.

- **Sensori Virtuali (Delta T):** Possibilità di creare un sensore virtuale calcolato sulla differenza tra due sensori. Lo scopo primario di questa funzione è di poterla utilizzare con un sensore di rilevamento di temperatura ambientale accoppiato ad un sensore di rilevamento per la temperatura del liquido. In questo modo si può creare una curva che regola il sistema in base a un Delta T costante, slegando il controllo dei profili dell'impianto dalla temperatura assoluta del liquido, che può variare in base alle stagioni dell'anno.

- **Calibrazione dei sensori di flusso:** Il driver linux legge il valore associato ai sensori di flusso in litri/ora, ovvero non mostra il valore "grezzo" del sensore, ma il valore già elaborato dal firmware della scheda, quello di default o impostato tramite Aquasuite e salvato sulla EEPROM. Aquacontrol può modificare liberamente il valore di impulsi/litro in base al vostro specifico sensore di flusso e ho aggiunto gli stessi sensori (preset con parametri modificabili) disponibili in Aquasuite.

- **Funzioni di sicurezza:** Il software monitora costantemente i valori di RPM, potenza e voltaggio delle quattro uscite 12V dell'Aquaero, oltre a monitorare i sensori delle temperature. È possibile configurare delle soglie critiche in cui il sistema potrà attivarsi:

  - **Intervento Automatico:** Al superamento della soglia, il programma interviene in automatico mostrando un allarme (visivo e sonoro), con la possibilità di lanciare un comando personalizzato, o spegnendo forzatamente il PC con i permessi di root.
  - **Diagnostica integrata:** In caso di spegnimento di emergenza forzato, il software genera un log di sistema. Al riavvio successivo del PC, una finestra popup indicherà all'utente quale componente ha causato l'anomalia.
  - **Ritardo Allarme:** Filtro temporale personalizzabile (in secondi) per ignorare letture critiche temporanee, risolvendo il problema dei falsi allarmi. Questa funzione è stata introdotta per gestire la ripresa dalla sospensione: al risveglio del sistema la lettura dei sensori è immediata, ma alcuni componenti (come una pompa D5) richiedono qualche istante di tempo per tornare a regime.

<p align="center">
  <img width="100%" alt="AquaControl Security Settings" src="https://github.com/user-attachments/assets/d2a71308-a6c9-48fb-aaf0-a7d37ffdf771" />
</p>

- **Overlay su Schermo (OSD):** Un pannello personalizzabile che è possibile spostare ovunque sul desktop. 
**Nota bene:** Per via delle regole di sicurezza di Wayland, l'OSD non è stato progettato per sovrapporsi alle schermate dei giochi in modalità fullscreen. L'OSD non mira a sostituire o sovrapporsi a strumenti dedicati come Mangohud, ma nasce come strumento di monitoring del sistema, pensato per mostrare i sensori durante le normali sessioni di lavoro sul desktop o durante stress test in finestra. Non ho integrato e non intendo integrare funzioni che fuoriescano dallo scopo del progetto.

- **Cambio Profilo Automatico:** AquaControl permette di creare profili personalizzati e di associare specifici programmi (come li si avvierebbe tramite terminale); è possibile quindi associare un profilo più aggressivo all'apertura di un videogame o di un software di rendering, con ripristino automatico del profilo precedente alla chiusura del programma.

- **Supporto Farbwerk 360 (parziale):**
Il Farbwerk 360 è una complessa scheda che integra al suo interno numerose funzioni, completamente indipendente e slegata dall'Aquaero 6 LT, che è invece una scheda pensata per il controllo degli impianti a liquido. 
Al momento il supporto è "parziale", perché AquaControl è in grado di gestirla come semplice header RGB e non ho integrato ulteriori funzioni, al di fuori del controllo dei LED RGB. Sono riuscito a codificare la logica delle strisce LED virtuali (20 in totale, impostabili sui quattro canali RGBpx) e l'impostazione di diversi effetti hardware. Il software è in grado di salvare le impostazioni dentro la EEPROM del dispositivo, quindi le modifiche alla configurazione dei LED possono sopravvivere al riavvio del sistema. A differenza di Aquasuite, che salva in automatico le impostazioni della configurazione LED, questo software offre la possibilità di applicare gli effetti senza salvarli in memoria. L'integrazione del Farbwerk 360 è ancora in sviluppo a causa della complessità e del numero di funzioni presenti.

<p align="center">
  <img width="100%" alt="Farbwerk 360 Support" src="https://github.com/user-attachments/assets/6369a3d3-d009-49de-b65f-22688cbfaf64" />
</p>

  - **Effetti pienamente supportati:** *Arcobaleno rotante, Arcobaleno scorrevole, Respiro, Sfumatura colore, Cambio colore, Lampeggio, Sequenza colori, Sequenza, Scanner, Laser, Onda, Fiamma, Pioggia, Nevicata, Polvere di stelle.*
    
## ⚠️ AVVISO IMPORTANTE: SI SCONSIGLIA DI AGGIORNARE I FIRMWARE

Il corretto funzionamento del software è stato verificato e testato su schede **Aquaero 6 LT dotate di Firmware 2104** e su schede **Farbwerk 360 dotate di Firmware 1025**. Non viene garantita la compatibilità di funzioni come lo switch PWM/DC e la calibrazione dei sensori di flusso su altre versioni firmware dell'Aquaero 6 LT, così come non viene garantita la funzionalità del controllo dei LED RGB e degli effetti del Farbwerk 360, perché tali funzioni sono state implementate tramite reverse engineering dei protocolli proprietari di Aquacomputer.
Il produttore utilizza protocolli chiusi. Gli aggiornamenti ufficiali possono alterare imprevedibilmente la struttura dei dati e interrompere in modo permanente la compatibilità con AquaControl.

## 🛠 Installazione

### Arch Linux

1. Clona questo repository sul tuo computer eseguendo nel terminale:

   ```bash
   git clone https://github.com/raffaele-90/aquacontrol.git
   ```

2. Apri il terminale nella cartella dei sorgenti appena clonata e compila il pacchetto:

   ```bash
   cd aquacontrol
   makepkg -si
   ```

   Questo compila e installa l'applicazione, crea il gruppo di sistema `aquacontrol` e la cartella di configurazione condivisa, e risolve automaticamente le dipendenze necessarie (come `python-hidapi`).

3. In linea con le convenzioni di Arch Linux, il pacchetto **non** abilita i servizi né modifica il tuo sistema da solo. Completa la configurazione con:

   ```bash

   sudo systemctl enable --now aquacontrold.service

   systemctl --user enable --now aquacontrol-agent.service

   sudo usermod -aG aquacontrol "$USER"
   ```

   Poi esegui il **logout e rientra** (o riavvia) affinché l'aggiunta al gruppo abbia effetto.

4. Se utilizzi una scheda video NVIDIA e desideri visualizzarne i dati di carico e temperatura, installa il pacchetto aggiuntivo da AUR/pacman:

   ```bash
   sudo pacman -S python-pynvml
   ```

### Debian / Ubuntu / Linux Mint

> **Compatibilità.** Il pacchetto `.deb` richiede **Debian 13 (Trixie) o Ubuntu 24.10 (o versioni successive)**, oppure una distribuzione derivata basata su di esse. Il motivo è PySide6, la libreria dell'interfaccia grafica, presente nei repository ufficiali solo a partire da queste versioni. Sulle release precedenti — incluse le attuali LTS di Ubuntu (24.04 e 22.04) e le versioni di Linux Mint basate su di esse — PySide6 non è pacchettizzato: il `.deb` **non si installerà**, perché `apt` non riuscirà a soddisfare le dipendenze. Su queste distribuzioni occorre installare da sorgente e procurarsi PySide6 manualmente (ad esempio con `pip`, preferibilmente in un ambiente virtuale).

1. Scarica l'ultima versione del pacchetto `.deb` dalla pagina [Releases](https://github.com/raffaele-90/aquacontrol/releases) del repository.

2. Apri il terminale nella cartella in cui hai scaricato il file ed esegui il comando:

   ```bash
   sudo apt install ./aquacontrol_*.deb
   ```

   Il gestore dei pacchetti installerà l'applicazione risolvendo automaticamente tutte le dipendenze necessarie.

3. Se utilizzi una scheda video NVIDIA e desideri visualizzarne i dati di carico e temperatura, installa il pacchetto aggiuntivo eseguendo: 

   ```bash
   sudo apt install python3-pynvml
   ```

## 📜 Licenza
Rilasciato sotto licenza internazionale libera GNU GPLv3. Questo è un progetto indipendente sviluppato da un utente della community Linux e non è in alcun modo affiliato, supportato o approvato da Aquacomputer.

## 👤 Autore / Maintainer

Sviluppato e mantenuto da **Raffaele Schiavone** ([@raffaele-90](https://github.com/raffaele-90)).
Link al repository del progetto: [AquaControl su GitHub](https://github.com/raffaele-90/aquacontrol)

*Scrivo software libero perché credo nel diritto di poter usare l'hardware che acquisto sul sistema operativo che preferisco, senza dover installare Microsoft Windows.*
