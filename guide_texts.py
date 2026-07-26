# AquaControl
# Copyright (C) 2026 Raffaele Schiavone
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
from config_manager import global_config

# 1. Calcolo dinamico della cartella principale (dove si trova questo script)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 2. Creazione dei percorsi assoluti per le icone (compatibili con Qt)
ICON_CURVES = os.path.join(BASE_DIR, "assets", "icons", "curves.svg").replace("\\", "/")
ICON_HARDWARE = os.path.join(BASE_DIR, "assets", "icons", "hardware.svg").replace("\\", "/")
ICON_SECURITY = os.path.join(BASE_DIR, "assets", "icons", "security.svg").replace("\\", "/")
ICON_LAMP = os.path.join(BASE_DIR, "assets", "icons", "lamp.svg").replace("\\", "/")


GUIDE_TRANSLATIONS = {
"it": f"""
        <h2 style="font-size: 18px; color: #cdd6f4; margin-top: 0; margin-bottom: 10px;">Guida alle funzioni avanzate del programma</h2>
        <p style="font-size: 14px; color: #a6adc8; margin-bottom: 16px;">Questa guida illustra il funzionamento delle logiche avanzate del software, suddivise in sezioni.</p>

        <h3 style="font-size: 16px; color: #00e5ff; background-color: rgba(0, 229, 255, 0.1); padding: 5px 10px; border-radius: 4px;">
            <img src="{ICON_CURVES}" width="24" height="24" align="middle"> Gestione Curve
        </h3>

        <h4 style="font-size: 15px; color: #00e5ff; margin-top: 15px; margin-bottom: 5px;">Modalità PID</h4>
        <p style="font-size: 14px;">A differenza della modalità automatica, la modalità PID utilizza un algoritmo che adatta in maniera dinamica la potenza per mantenere il sensore di riferimento scelto alla temperatura impostata (<b>Obiettivo</b>), in base al carico del sistema in tempo reale.</p>
        <p style="font-size: 14px;">Il software offre tre profili preimpostati (<b>Lento, Normale, Veloce</b>). Per gli utenti esperti, la modalità <b>Manuale</b> permette di definire i tre parametri matematici in modo da adattare l'algoritmo alle specifiche caratteristiche del proprio impianto:</p>

        <ul style="margin-top: 5px; margin-bottom: 15px;">
            <li style="font-size: 14px; margin-bottom: 8px;"><b style="color: #00e5ff;">Proporzionale (P):</b> Regola la sensibilità di base alle variazioni di temperatura. Agisce in risposta alla differenza istantanea tra la temperatura rilevata e l'<b>Obiettivo</b>. Un valore troppo elevato rende l’algoritmo eccessivamente reattivo, innescando continue oscillazioni nel regime di rotazione delle ventole. Incrementalo a step di <b>0.5</b>.</li>
            <li style="font-size: 14px; margin-bottom: 8px;"><b style="color: #00e5ff;">Integrale (I):</b> Gestisce la compensazione cumulativa sul lungo periodo. Analizza il tempo trascorso fuori dall'<b>Obiettivo</b> e accumula la correzione necessaria per far convergere le ventole al regime di rotazione necessario (es. 60% fisso) per mantenere stabilmente la temperatura del sensore. A causa dell'elevata inerzia termica dell'acqua, questo valore deve essere mantenuto molto basso. Modificalo a piccoli step di <b>0.01</b>.</li>
            <li style="font-size: 14px; margin-bottom: 8px;"><b style="color: #00e5ff;">Derivativo (D):</b> Applica uno smorzamento dinamico in base alla velocità con cui cambia la temperatura. <b>Nei sistemi a liquido si consiglia di mantenerlo vicino allo 0.</b> Poiché l'acqua si scalda in modo graduale, un valore eccessivamente alto porterebbe a improvvisi e ingiustificati picchi di rotazione in risposta a minime fluttuazioni di lettura del sensore.</li>
        </ul>

        <div style="margin-top: 15px; margin-bottom: 15px;">
            <h4 style="font-size: 15px; color: #00e5ff; margin-bottom: 5px;"><img src="{ICON_LAMP}" width="16" height="16" align="middle"> Valori di Riferimento (Preset del Software)</h4>
            <p style="font-size: 14px; margin-top: 0; margin-bottom: 10px;">Se si desidera creare una curva manuale, è possibile utilizzare questi parametri come punto di partenza orientativo:</p>
            <div style="color: #cdd6f4; background-color: rgba(0, 229, 255, 0.1); padding: 8px; border-left: 4px solid #00e5ff; margin-bottom: 8px; font-size: 13px; font-family: monospace;"><b>Lento:</b> P = 3.0 | I = 0.05 | D = 0.1</div>
            <div style="color: #cdd6f4; background-color: rgba(0, 229, 255, 0.1); padding: 8px; border-left: 4px solid #00e5ff; margin-bottom: 8px; font-size: 13px; font-family: monospace;"><b>Normale:</b> P = 5.0 | I = 0.08 | D = 0.3</div>
            <div style="color: #cdd6f4; background-color: rgba(0, 229, 255, 0.1); padding: 8px; border-left: 4px solid #00e5ff; margin-bottom: 8px; font-size: 13px; font-family: monospace;"><b>Veloce:</b> P = 8.0 | I = 0.10 | D = 0.5</div>
        </div>

        <h4 style="font-size: 15px; color: #00e5ff; margin-top: 15px; margin-bottom: 5px;">Sensore Virtuale (ΔT)</h4>
        <p style="font-size: 14px;">Attivando il <b>Sensore Virtuale (ΔT)</b>, AquaControl calcola costantemente la differenza tra il sensore principale impostato e un secondo sensore di riferimento: <br><code style="background-color: #1e1e2e; padding: 2px 5px;">[Principale] - [Riferimento] = ΔT</code></p>
        <p style="font-size: 14px;"><b>Scenario di utilizzo tipico:</b><br>
        In un sistema di raffreddamento a liquido convenzionale, la temperatura dei componenti non può mai scendere sotto la temperatura ambientale. Una curva impostata per tenere il liquido a 35°C funzionerà in inverno, ma in estate (con Tamb > 35°C) costringerà le ventole al 100% per raggiungere una temperatura fisicamente impossibile.</p>
        <p style="font-size: 14px;">Sottraendo la <i>Temperatura dell'Aria</i> (riferimento) alla <i>Temperatura del Liquido</i> (principale), è possibile impostare un <b>Obiettivo</b> PID o una curva basata su un <b>ΔT di 10°C</b>. In questo modo, il sistema manterrà l'acqua a 30°C in inverno (20°C ambiente + 10) e a 40°C in estate (30°C ambiente + 10).</p>

        <h4 style="font-size: 15px; color: #00e5ff; margin-top: 15px; margin-bottom: 5px;">Cambio Profilo Automatico (Auto-Switch)</h4>
        <p style="font-size: 14px;">Questa funzione permette ad AquaControl di caricare un profilo specifico quando avvii determinati programmi, per poi ripristinare il profilo predefinito alla loro chiusura.</p>
        <p style="font-size: 14px;">Essendo un software nativo Linux, non è necessario cercare il percorso dell’eseguibile. È sufficiente digitare il <b>nome del programma</b> così come verrebbe digitato nel terminale di sistema (ad esempio <code>steam</code>, <code>firefox</code>, <code>blender</code>) per garantire che il software rilevi l'apertura del programma.</p>

        <hr style="border: 1px solid #313244; margin: 25px 0;">

        <h3 style="font-size: 16px; color: #00e5ff; background-color: rgba(0, 229, 255, 0.1); padding: 5px 10px; border-radius: 4px;">
            <img src="{ICON_HARDWARE}" width="24" height="24" align="middle"> Configurazione Hardware
        </h3>

        <h4 style="font-size: 15px; color: #00e5ff; margin-top: 15px; margin-bottom: 5px;">Potenza Minima (Prevenzione Stallo)</h4>
        <p style="font-size: 14px;">I motori delle ventole e delle pompe hanno un limite fisico sotto il quale non riescono a girare. Esempio: impostando questo limite al 25%, il software ricalcolerà l'intera curva in modo che lo 0% del grafico corrisponda al 25% inviato al motore. Al di sotto del valore minimo, il canale toglierà del tutto l'alimentazione, spegnendo la periferica ed evitando così fastidiosi ronzii elettrici o danni al motore dovuti allo stallo prolungato.</p>

        <h4 style="font-size: 15px; color: #00e5ff; margin-top: 15px; margin-bottom: 5px;">Start Boost (Avvio Rapido)</h4>
        <p style="font-size: 14px;">L'inerzia è un elemento non trascurabile in un sistema fisico. Una ventola che gira stabilmente al 20% potrebbe non avere la forza sufficiente per <i>iniziare</i> a girare partendo da zero a quella stessa percentuale. Attivando lo <i>Start Boost</i>, ogni volta che il canale si accende, il controller invierà un impulso al 100% della potenza per una frazione di secondo (durata configurabile) per dare una spinta al rotore, per poi assestarlo istantaneamente alla velocità richiesta dalla curva impostata.</p>

        <hr style="border: 1px solid #313244; margin: 25px 0;">

        <h3 style="font-size: 16px; color: #ff3333; background-color: rgba(255, 51, 51, 0.1); padding: 5px 10px; border-radius: 4px;">
            <img src="{ICON_SECURITY}" width="24" height="24" align="middle"> Impostazioni di Sicurezza
        </h3>
        <p style="font-size: 14px;">Il sistema di sicurezza interviene automaticamente per prevenire danni all'hardware. Il sistema di emergenza ha due impostazioni separate, che hanno scopi specifici:</p>

        <p style="font-size: 14px;"><b>1. Ritardo Allarme (Sensibilità)</b><br>
        Impostabile per ogni singolo canale, definisce <b>quanti secondi</b> un valore critico deve persistere prima di far scattare il sistema di emergenza. Esempio: se una pompa scende a 0 RPM, ma il <i>Ritardo Allarme</i> è impostato a 3 secondi, il software aspetterà. Se entro 3 secondi la pompa riparte (es. uscita dallo stato di sospensione del pc), l'allarme non scatterà. Questa funzione è stata integrata proprio per evitare falsi allarmi che potevano verificarsi alla ripresa dalla sospensione.</p>

        <p style="font-size: 14px;"><b>2. Azioni Globali e Attesa Spegnimento</b><br>
        Una volta innescato il sistema di emergenza, il software esegue le azioni richieste (notifiche, allarmi sonori, esecuzione script personalizzati). Se hai attivato lo <i>Spegnimento forzato di emergenza</i> in combinazione con un comando personalizzato (es. uno script per salvare file aperti), l'opzione <b>Attesa esecuzione comando</b> permette di imporre al sistema di aspettare <b>X</b> secondi prima di staccare forzatamente l'alimentazione, dando tempo allo script di terminare il proprio compito.</p>
    """,

"en": f"""
        <h2 style="font-size: 18px; color: #cdd6f4; margin-top: 0; margin-bottom: 10px;">Guide to the program's advanced features</h2>
        <p style="font-size: 14px; color: #a6adc8; margin-bottom: 16px;">This guide explains the operation of the software's advanced logic, divided into sections.</p>

        <h3 style="font-size: 16px; color: #00e5ff; background-color: rgba(0, 229, 255, 0.1); padding: 5px 10px; border-radius: 4px;">
            <img src="{ICON_CURVES}" width="24" height="24" align="middle"> Curve Management
        </h3>

        <h4 style="font-size: 15px; color: #00e5ff; margin-top: 15px; margin-bottom: 5px;">PID Mode</h4>
        <p style="font-size: 14px;">Unlike automatic mode, PID mode uses an algorithm that dynamically adapts the power to keep the chosen reference sensor at the set temperature (<b>Target</b>), based on the real-time system load.</p>
        <p style="font-size: 14px;">The software offers three preset profiles (<b>Slow, Normal, Fast</b>). For advanced users, <b>Manual</b> mode allows you to define the three mathematical parameters to adapt the algorithm to the specific characteristics of your system:</p>

        <ul style="margin-top: 5px; margin-bottom: 15px;">
            <li style="font-size: 14px; margin-bottom: 8px;"><b style="color: #cba6f7;">Proportional (P):</b> Adjusts the basic sensitivity to temperature variations. It acts in response to the instantaneous difference between the detected temperature and the <b>Target</b>. A value that is too high makes the algorithm overly reactive, triggering continuous oscillations in fan speed. Increase it in steps of <b>0.5</b>.</li>
            <li style="font-size: 14px; margin-bottom: 8px;"><b style="color: #cba6f7;">Integral (I):</b> Manages the cumulative compensation over the long term. It analyzes the time spent outside the <b>Target</b> and accumulates the necessary correction to make the fans converge to the required rotational speed (e.g., fixed 60%) to steadily maintain the sensor temperature. Due to the high thermal inertia of water, this value must be kept very low. Modify it in small steps of <b>0.01</b>.</li>
            <li style="font-size: 14px; margin-bottom: 8px;"><b style="color: #cba6f7;">Derivative (D):</b> Applies dynamic dampening based on the speed at which the temperature changes. <b>In liquid systems, it is recommended to keep it close to 0.</b> Since water heats up gradually, an excessively high value would lead to sudden and unjustified rotation spikes in response to minimal sensor reading fluctuations.</li>
        </ul>

        <div style="margin-top: 15px; margin-bottom: 15px;">
            <h4 style="font-size: 15px; color: #00e5ff; margin-bottom: 5px;"><img src="{ICON_LAMP}" width="16" height="16" align="middle"> Reference Values (Software Presets)</h4>
            <p style="font-size: 14px; margin-top: 0; margin-bottom: 10px;">If you want to create a manual curve, use these values as a starting point for guidance:</p>
            <div style="color: #cdd6f4; background-color: rgba(0, 229, 255, 0.1); padding: 8px; border-left: 4px solid #00e5ff; margin-bottom: 8px; font-size: 13px; font-family: monospace;"><b>Slow:</b> P = 3.0 | I = 0.05 | D = 0.1</div>
            <div style="color: #cdd6f4; background-color: rgba(0, 229, 255, 0.1); padding: 8px; border-left: 4px solid #00e5ff; margin-bottom: 8px; font-size: 13px; font-family: monospace;"><b>Normal:</b> P = 5.0 | I = 0.08 | D = 0.3</div>
            <div style="color: #cdd6f4; background-color: rgba(0, 229, 255, 0.1); padding: 8px; border-left: 4px solid #00e5ff; margin-bottom: 8px; font-size: 13px; font-family: monospace;"><b>Fast:</b> P = 8.0 | I = 0.10 | D = 0.5</div>
        </div>

        <h4 style="font-size: 15px; color: #00e5ff; margin-top: 15px; margin-bottom: 5px;">Virtual Sensor (ΔT)</h4>
        <p style="font-size: 14px;">By activating the <b>Virtual Sensor (ΔT)</b>, AquaControl constantly calculates the difference between the set main sensor and a second reference sensor: <br><code style="background-color: #1e1e2e; padding: 2px 5px;">[Main] - [Reference] = ΔT</code></p>
        <p style="font-size: 14px;"><b>Typical use case:</b><br>
        In a conventional liquid cooling system, component temperatures can never drop below ambient temperature. A curve set to keep the liquid at 35°C will work in winter, but in summer (with Tamb > 35°C) it will force the fans to 100% to reach a physically impossible temperature.</p>
        <p style="font-size: 14px;">By subtracting the <i>Air Temperature</i> (reference) from the <i>Liquid Temperature</i> (main), it is possible to set a PID <b>Target</b> or a curve based on a <b>ΔT of 10°C</b>. This way, the system will keep the water at 30°C in winter (20°C ambient + 10) and at 40°C in summer (30°C ambient + 10).</p>

        <h4 style="font-size: 15px; color: #00e5ff; margin-top: 15px; margin-bottom: 5px;">Automatic Profile Switch (Auto-Switch)</h4>
        <p style="font-size: 14px;">This function allows AquaControl to load a specific profile when you start certain programs, and then restore the default profile when they close.</p>
        <p style="font-size: 14px;">Since it is native Linux software, there is no need to find the executable path. Simply type the <b>program name</b> exactly as it would be typed in the system terminal (for example <code>steam</code>, <code>firefox</code>, <code>blender</code>) to ensure the software detects the program opening.</p>

        <hr style="border: 1px solid #313244; margin: 25px 0;">

        <h3 style="font-size: 16px; color: #00e5ff; background-color: rgba(0, 229, 255, 0.1); padding: 5px 10px; border-radius: 4px;">
            <img src="{ICON_HARDWARE}" width="24" height="24" align="middle"> Hardware Configuration
        </h3>

        <h4 style="font-size: 15px; color: #00e5ff; margin-top: 15px; margin-bottom: 5px;">Minimum Power (Stall Prevention)</h4>
        <p style="font-size: 14px;">Fan and pump motors have a physical limit below which they cannot spin. Example: by setting this limit to 25%, the software will recalculate the entire curve so that 0% on the graph corresponds to the 25% sent to the motor. Below the minimum value, the channel will cut power completely, turning off the device and thus avoiding annoying electrical buzzing or motor damage due to prolonged stalling.</p>

        <h4 style="font-size: 15px; color: #00e5ff; margin-top: 15px; margin-bottom: 5px;">Start Boost (Quick Start)</h4>
        <p style="font-size: 14px;">Inertia is a significant element in a physical system. A fan that spins steadily at 20% might not have enough force to <i>start</i> spinning from zero at that same percentage. By activating <i>Start Boost</i>, every time the channel turns on, the controller will send a 100% power pulse for a fraction of a second (configurable duration) to give the rotor a push, before instantly settling it to the speed required by the set curve.</p>

        <hr style="border: 1px solid #313244; margin: 25px 0;">

        <h3 style="font-size: 16px; color: #ff3333; background-color: rgba(255, 51, 51, 0.1); padding: 5px 10px; border-radius: 4px;">
            <img src="{ICON_SECURITY}" width="24" height="24" align="middle"> Security Settings (Fail-Safe)
        </h3>
        <p style="font-size: 14px;">The security system automatically intervenes to prevent hardware damage. The emergency system has two separate settings, which serve specific purposes:</p>

        <p style="font-size: 14px;"><b>1. Alarm Delay (Sensitivity)</b><br>
        Configurable for each individual channel, it defines <b>how many seconds</b> a critical value must persist before triggering the emergency system. Example: if a pump drops to 0 RPM, but the <i>Alarm Delay</i> is set to 3 seconds, the software will wait. If the pump restarts within 3 seconds (e.g., waking from PC sleep state), the alarm will not trigger. This feature was integrated specifically to prevent false alarms that could occur when resuming from sleep.</p>

        <p style="font-size: 14px;"><b>2. Global Actions and Shutdown Wait</b><br>
        Once the emergency system is triggered, the software executes the requested actions (notifications, sound alarms, custom script execution). If you have activated the <i>Emergency forced shutdown</i> in combination with a custom command (e.g., a script to save open files), the <b>Wait for command execution</b> option allows you to force the system to wait <b>X</b> seconds before forcibly cutting power, giving the script time to finish its task.</p>
    """,

    "fr": f"""
        <h2 style="font-size: 18px; color: #cdd6f4; margin-top: 0; margin-bottom: 10px;">Guide des fonctions avancées du programme</h2>
        <p style="font-size: 14px; color: #a6adc8; margin-bottom: 16px;">Ce guide explique le fonctionnement des logiques avancées du logiciel, réparties en sections.</p>

        <h3 style="font-size: 16px; color: #00e5ff; background-color: rgba(0, 229, 255, 0.1); padding: 5px 10px; border-radius: 4px;">
            <img src="{ICON_CURVES}" width="24" height="24" align="middle"> Gestion des Courbes
        </h3>

        <h4 style="font-size: 15px; color: #00e5ff; margin-top: 15px; margin-bottom: 5px;">Mode PID</h4>
        <p style="font-size: 14px;">Contrairement au mode automatique, le mode PID utilise un algorithme qui adapte dynamiquement la puissance pour maintenir le capteur de référence choisi à la température définie (<b>Cible</b>), en fonction de la charge du système en temps réel.</p>
        <p style="font-size: 14px;">Le logiciel propose trois profils prédéfinis (<b>Lent, Normal, Rapide</b>). Pour les utilisateurs experts, le mode <b>Manuel</b> permet de définir les trois paramètres mathématiques afin d'adapter l'algorithme aux caractéristiques spécifiques de votre système :</p>

        <ul style="margin-top: 5px; margin-bottom: 15px;">
            <li style="font-size: 14px; margin-bottom: 8px;"><b style="color: #cba6f7;">Proportionnel (P):</b> Règle la sensibilité de base aux variations de température. Il agit en réponse à la différence instantanée entre la température détectée et la <b>Cible</b>. Une valeur trop élevée rend l'algorithme excessivement réactif, déclenchant des oscillations continues du régime des ventilateurs. Augmentez-le par paliers de <b>0.5</b>.</li>
            <li style="font-size: 14px; margin-bottom: 8px;"><b style="color: #cba6f7;">Intégral (I):</b> Gère la compensation cumulative sur le long terme. Il analyse le temps passé en dehors de la <b>Cible</b> et accumula la correction nécessaire pour faire converger les ventilateurs vers le régime de rotation requis (ex. 60% fixe) pour maintenir de manière stable la température du capteur. En raison de l'inertie thermique élevée de l'eau, cette valeur doit être maintenue très basse. Modifiez-la par petits paliers de <b>0.01</b>.</li>
            <li style="font-size: 14px; margin-bottom: 8px;"><b style="color: #cba6f7;">Dérivé (D):</b> Applique un amortissement dynamique en fonction de la vitesse à laquelle la température change. <b>Dans les systèmes liquides, il est recommandé de le maintenir proche de 0.</b> L'eau se réchauffant progressivement, une valeur excessivement élevée entraînerait des pics de rotation soudains et injustifiés en réponse à de minimes fluctuations de lecture du capteur.</li>
        </ul>

        <div style="margin-top: 15px; margin-bottom: 15px;">
            <h4 style="font-size: 15px; color: #00e5ff; margin-bottom: 5px;"><img src="{ICON_LAMP}" width="16" height="16" align="middle"> Valeurs de Référence (Préréglages du logiciel)</h4>
            <p style="font-size: 14px; margin-top: 0; margin-bottom: 10px;">Si vous souhaitez créer une courbe manuelle, utilisez ces valeurs comme point de départ pour vous guider :</p>
            <div style="color: #cdd6f4; background-color: rgba(0, 229, 255, 0.1); padding: 8px; border-left: 4px solid #00e5ff; margin-bottom: 8px; font-size: 13px; font-family: monospace;"><b>Lent:</b> P = 3.0 | I = 0.05 | D = 0.1</div>
            <div style="color: #cdd6f4; background-color: rgba(0, 229, 255, 0.1); padding: 8px; border-left: 4px solid #00e5ff; margin-bottom: 8px; font-size: 13px; font-family: monospace;"><b>Normal:</b> P = 5.0 | I = 0.08 | D = 0.3</div>
            <div style="color: #cdd6f4; background-color: rgba(0, 229, 255, 0.1); padding: 8px; border-left: 4px solid #00e5ff; margin-bottom: 8px; font-size: 13px; font-family: monospace;"><b>Rapide:</b> P = 8.0 | I = 0.10 | D = 0.5</div>
        </div>

        <h4 style="font-size: 15px; color: #00e5ff; margin-top: 15px; margin-bottom: 5px;">Capteur Virtuel (ΔT)</h4>
        <p style="font-size: 14px;">En activant le <b>Capteur Virtuel (ΔT)</b>, AquaControl calcule constamment la différence entre le capteur principal défini et un second capteur de référence : <br><code style="background-color: #1e1e2e; padding: 2px 5px;">[Principal] - [Référence] = ΔT</code></p>
        <p style="font-size: 14px;"><b>Scénario d'utilisation typique :</b><br>
        Dans un système de refroidissement liquide conventionnel, la température des composants ne peut jamais descendre en dessous de la température ambiante. Une courbe réglée pour maintenir le liquide à 35°C fonctionnera en hiver, mais en été (avec Tamb > 35°C), elle forcera les ventilateurs à 100% pour atteindre une température physiquement impossible.</p>
        <p style="font-size: 14px;">En soustrayant la <i>Température de l'Air</i> (référence) à la <i>Température du Liquide</i> (principal), il est possible de définir une <b>Cible</b> PID ou une courbe basée sur un <b>ΔT de 10°C</b>. Ainsi, le système maintiendra l'eau à 30°C en hiver (20°C ambiant + 10) et à 40°C en été (30°C ambiant + 10).</p>

        <h4 style="font-size: 15px; color: #00e5ff; margin-top: 15px; margin-bottom: 5px;">Changement de Profil Automatique (Auto-Switch)</h4>
        <p style="font-size: 14px;">Cette fonction permet à AquaControl de charger un profil spécifique lors du lancement de certains programmes, puis de restaurer le profil par défaut à leur fermeture.</p>
        <p style="font-size: 14px;">S'agissant d'un logiciel natif Linux, il n'est pas nécessaire de chercher le chemin de l'exécutable. Il suffit de taper le <b>nom du programme</b> tel qu'il serait tapé dans le terminal système (par exemple <code>steam</code>, <code>firefox</code>, <code>blender</code>) pour garantir que le logiciel détecte l'ouverture du programme.</p>

        <hr style="border: 1px solid #313244; margin: 25px 0;">

        <h3 style="font-size: 16px; color: #00e5ff; background-color: rgba(0, 229, 255, 0.1); padding: 5px 10px; border-radius: 4px;">
            <img src="{ICON_HARDWARE}" width="24" height="24" align="middle"> Configuration Matérielle
        </h3>

        <h4 style="font-size: 15px; color: #00e5ff; margin-top: 15px; margin-bottom: 5px;">Puissance Minimale (Prévention de Blocage)</h4>
        <p style="font-size: 14px;">Les moteurs de ventilateurs et de pompes ont une limite physique en dessous de laquelle ils ne peuvent pas tourner. Exemple : en fixant cette limite à 25%, le logiciel recalculera toute la courbe pour que 0% sur le graphique corresponde aux 25% envoyés au moteur. En dessous de la valeur minimale, le canal coupera complètement l'alimentation, éteignant le périphérique et évitant ainsi les bourdonnements électriques gênants ou les dommages au moteur dus à un blocage prolongé.</p>

        <h4 style="font-size: 15px; color: #00e5ff; margin-top: 15px; margin-bottom: 5px;">Start Boost (Démarrage Rapide)</h4>
        <p style="font-size: 14px;">L'inertie est un élément non négligeable dans un système physique. Un ventilador qui tourne de manière stable à 20% pourrait ne pas avoir la force suffisante pour <i>commencer</i> à tourner en partant de zéro à ce même pourcentage. En activant le <i>Start Boost</i>, chaque fois que le canal s'allume, le contrôleur enverra une impulsion à 100% de puissance pendant une fraction de seconde (durée configurable) pour donner une poussée au rotor, puis le stabilisera instantanément à la vitesse requise par la courbe définie.</p>

        <hr style="border: 1px solid #313244; margin: 25px 0;">

        <h3 style="font-size: 16px; color: #ff3333; background-color: rgba(255, 51, 51, 0.1); padding: 5px 10px; border-radius: 4px;">
            <img src="{ICON_SECURITY}" width="24" height="24" align="middle"> Paramètres de Sécurité (Fail-Safe)
        </h3>
        <p style="font-size: 14px;">Le système de sécurité intervient automatiquement pour prévenir les dommages matériels. Le système d'urgence a deux paramètres distincts, qui ont des objectifs spécifiques :</p>

        <p style="font-size: 14px;"><b>1. Délai d'Alarme (Sensibilité)</b><br>
        Configurable pour chaque canal, il définit <b>combien de secondes</b> une valeur critique doit persister avant de déclencher le système d'urgence. Exemple : si une pompe tombe à 0 RPM, mais que le <i>Délai d'Alarme</i> est réglé sur 3 secondes, le logiciel attendra. Si la pompe redémarre dans les 3 secondes (ex. sortie de l'état de veille du PC), l'alarme ne se déclenchera pas. Cette fonction a été intégrée précisément pour éviter les fausses alarmes qui pouvaient se produire lors de la sortie de veille.</p>

        <p style="font-size: 14px;"><b>2. Actions Globales et Attente d'Arrêt</b><br>
        Une fois le système d'urgence déclenché, le logiciel exécute les actions demandées (notifications, alarmes sonores, exécution de scripts personnalisés). Si vous avez activé l'<i>Arrêt forcé d'urgence</i> en combinaison avec une commande personnalisée (ex. un script pour sauvegarder les fichiers ouverts), l'option <b>Attente exécution commande</b> permet d'imposer au système d'attendre <b>X</b> secondes avant de couper l'alimentation de force, laissant ainsi le temps au script de terminer sa tâche.</p>
    """,

    "es": f"""
        <h2 style="font-size: 18px; color: #cdd6f4; margin-top: 0; margin-bottom: 10px;">Guía de las funciones avanzadas del programa</h2>
        <p style="font-size: 14px; color: #a6adc8; margin-bottom: 16px;">Esta guía explica el funcionamiento de las lógicas avanzadas del software, divididas en secciones.</p>

        <h3 style="font-size: 16px; color: #00e5ff; background-color: rgba(0, 229, 255, 0.1); padding: 5px 10px; border-radius: 4px;">
            <img src="{ICON_CURVES}" width="24" height="24" align="middle"> Gestión de Curvas
        </h3>

        <h4 style="font-size: 15px; color: #00e5ff; margin-top: 15px; margin-bottom: 5px;">Modo PID</h4>
        <p style="font-size: 14px;">A diferencia del modo automático, el modo PID utiliza un algoritmo que adapta dinámicamente la potencia para mantener el sensor de referencia elegido a la temperatura establecida (<b>Objetivo</b>), en función de la carga del sistema en tiempo real.</p>
        <p style="font-size: 14px;">El software ofrece tres perfiles preestablecidos (<b>Lento, Normal, Rápido</b>). Para usuarios expertos, el modo <b>Manual</b> permite definir los tres parámetros matemáticos para adaptar el algoritmo a las características específicas de tu sistema:</p>

        <ul style="margin-top: 5px; margin-bottom: 15px;">
            <li style="font-size: 14px; margin-bottom: 8px;"><b style="color: #cba6f7;">Proporcional (P):</b> Regula la sensibilidad base a las variaciones de temperatura. Actúa en respuesta a la diferencia instantánea entre la temperatura detectada y el <b>Objetivo</b>. Un valor demasiado alto hace que el algoritmo sea excesivamente reactivo, provocando oscilaciones continuas en la velocidad de los ventiladores. Increméntalo en pasos de <b>0.5</b>.</li>
            <li style="font-size: 14px; margin-bottom: 8px;"><b style="color: #cba6f7;">Integral (I):</b> Gestiona la compensación acumulativa a largo plazo. Analiza el tiempo transcurrido fuera del <b>Objetivo</b> y acumula la corrección necesaria para hacer que los ventiladores converjan al régimen de rotación necesario (ej. 60% fijo) para mantener estable la temperatura del sensor. Debido a la alta inercia térmica del agua, este valor debe mantenerse muy bajo. Modifícalo en pequeños pasos de <b>0.01</b>.</li>
            <li style="font-size: 14px; margin-bottom: 8px;"><b style="color: #cba6f7;">Derivativo (D):</b> Aplica una amortiguación dinámica en función de la velocidad a la que cambia la temperatura. <b>En los sistemas líquidos se recomienda mantenerlo cerca de 0.</b> Dado que el agua se calienta gradualmente, un valor excesivamente alto provocaría picos de rotación repentinos e injustificados en respuesta a mínimas fluctuaciones de lectura del sensor.</li>
        </ul>

        <div style="margin-top: 15px; margin-bottom: 15px;">
            <h4 style="font-size: 15px; color: #00e5ff; margin-bottom: 5px;"><img src="{ICON_LAMP}" width="16" height="16" align="middle"> Valores de Referencia (Ajustes preestablecidos del software)</h4>
            <p style="font-size: 14px; margin-top: 0; margin-bottom: 10px;">Si deseas crear una curva manual, utiliza estos valores como punto de partida para orientarte:</p>
            <div style="color: #cdd6f4; background-color: rgba(0, 229, 255, 0.1); padding: 8px; border-left: 4px solid #00e5ff; margin-bottom: 8px; font-size: 13px; font-family: monospace;"><b>Lento:</b> P = 3.0 | I = 0.05 | D = 0.1</div>
            <div style="color: #cdd6f4; background-color: rgba(0, 229, 255, 0.1); padding: 8px; border-left: 4px solid #00e5ff; margin-bottom: 8px; font-size: 13px; font-family: monospace;"><b>Normal:</b> P = 5.0 | I = 0.08 | D = 0.3</div>
            <div style="color: #cdd6f4; background-color: rgba(0, 229, 255, 0.1); padding: 8px; border-left: 4px solid #00e5ff; margin-bottom: 8px; font-size: 13px; font-family: monospace;"><b>Rápido:</b> P = 8.0 | I = 0.10 | D = 0.5</div>
        </div>

        <h4 style="font-size: 15px; color: #00e5ff; margin-top: 15px; margin-bottom: 5px;">Sensor Virtual (ΔT)</h4>
        <p style="font-size: 14px;">Al activar el <b>Sensor Virtual (ΔT)</b>, AquaControl calcula constantemente la diferencia entre el sensor principal establecido y un segundo sensor de referencia: <br><code style="background-color: #1e1e2e; padding: 2px 5px;">[Principal] - [Referencia] = ΔT</code></p>
        <p style="font-size: 14px;"><b>Escenario de uso típico:</b><br>
        En un sistema de refrigeración líquida convencional, la temperatura de los componentes nunca puede caer por debajo de la temperatura ambiente. Una curva configurada para mantener el líquido a 35°C funcionará en invierno, pero en verano (con Tamb > 35°C) forzará los ventiladores al 100% para alcanzar una temperatura físicamente imposible.</p>
        <p style="font-size: 14px;">Restando la <i>Temperatura del Aire</i> (referencia) a la <i>Temperatura del Líquido</i> (principal), es posible establecer un <b>Objetivo</b> PID o una curva basada en un <b>ΔT de 10°C</b>. De esta manera, el sistema mantendrá el agua a 30°C en invierno (20°C ambiente + 10) y a 40°C en verano (30°C ambiente + 10).</p>

        <h4 style="font-size: 15px; color: #00e5ff; margin-top: 15px; margin-bottom: 5px;">Cambio de Perfil Automático (Auto-Switch)</h4>
        <p style="font-size: 14px;">Esta función permite a AquaControl cargar un perfil específico cuando inicias determinados programas, para luego restaurar el perfil predeterminado al cerrarlos.</p>
        <p style="font-size: 14px;">Al ser un software nativo de Linux, no es necesario buscar la ruta del ejecutable. Basta con escribir el <b>nombre del programa</b> tal como se escribiría en la terminal del sistema (por ejemplo <code>steam</code>, <code>firefox</code>, <code>blender</code>) para garantizar que el software detecte la apertura del programa.</p>

        <hr style="border: 1px solid #313244; margin: 25px 0;">

        <h3 style="font-size: 16px; color: #00e5ff; background-color: rgba(0, 229, 255, 0.1); padding: 5px 10px; border-radius: 4px;">
            <img src="{ICON_HARDWARE}" width="24" height="24" align="middle"> Configuración de Hardware
        </h3>

        <h4 style="font-size: 15px; color: #00e5ff; margin-top: 15px; margin-bottom: 5px;">Potencia Mínima (Prevención de Estancamiento)</h4>
        <p style="font-size: 14px;">Los motores de ventiladores y bombas tienen un límite físico por debajo del cual no pueden girar. Ejemplo: al establecer este límite en 25%, el software recalculará toda la curva para que el 0% del gráfico corresponda al 25% enviado al motor. Por debajo del valor mínimo, el canal cortará por completo la alimentación, apagando el periférico y evitando así molestos zumbidos eléctricos o daños en el motor debido a un estancamiento prolongado.</p>

        <h4 style="font-size: 15px; color: #00e5ff; margin-top: 15px; margin-bottom: 5px;">Start Boost (Arranque Rápido)</h4>
        <p style="font-size: 14px;">La inercia es un elemento nada despreciable en un sistema físico. Un ventilador que gira de forma estable al 20% podría no tener la fuerza suficiente para <i>empezar</i> a girar partiendo de cero a ese mismo porcentaje. Al activar el <i>Start Boost</i>, cada vez que el canal se enciende, el controlador enviará un impulso al 100% de potencia durante una fracción de segundo (duración configurable) para dar un empujón al rotor, para luego asentarlo instantáneamente a la velocidad requerida por la curva establecida.</p>

        <hr style="border: 1px solid #313244; margin: 25px 0;">

        <h3 style="font-size: 16px; color: #ff3333; background-color: rgba(255, 51, 51, 0.1); padding: 5px 10px; border-radius: 4px;">
            <img src="{ICON_SECURITY}" width="24" height="24" align="middle"> Ajustes de Seguridad (Fail-Safe)
        </h3>
        <p style="font-size: 14px;">El sistema de seguridad interviene automáticamente para prevenir daños en el hardware. El sistema de emergencia tiene dos ajustes separados, que tienen propósitos específicos:</p>

        <p style="font-size: 14px;"><b>1. Retraso de Alarma (Sensibilidad)</b><br>
        Configurable para cada canal individual, define <b>cuántos segundos</b> debe persistir un valor crítico antes de activar el sistema de emergencia. Ejemplo: si una bomba cae a 0 RPM, pero el <i>Retraso de Alarma</i> está establecido en 3 segundos, el software esperará. Si la bomba se reinicia en 3 segundos (ej. salida del estado de suspensión del pc), la alarma no saltará. Esta función se integró precisamente para evitar falsas alarmas que podían ocurrir al reanudar desde la suspensión.</p>

        <p style="font-size: 14px;"><b>2. Acciones Globales y Espera de Apagado</b><br>
        Una vez activado el sistema de emergencia, el software ejecuta las acciones solicitadas (notificaciones, alarmas sonoras, ejecución de scripts personalizados). Si has activado el <i>Apagado forzado de emergencia</i> en combinación con un comando personalizado (ej. un script para guardar archivos abiertos), la opción <b>Espera de ejecución del comando</b> permite imponer al sistema que espere <b>X</b> segundos antes de cortar forzosamente la alimentación, dando tiempo al script para terminar su tarea.</p>
    """,

    "de": f"""
        <h2 style="font-size: 18px; color: #cdd6f4; margin-top: 0; margin-bottom: 10px;">Anleitung zu den erweiterten Programmfunktionen</h2>
        <p style="font-size: 14px; color: #a6adc8; margin-bottom: 16px;">Diese Anleitung erläutert die Funktionsweise der erweiterten Softwarelogiken, unterteilt in Abschnitte.</p>

        <h3 style="font-size: 16px; color: #00e5ff; background-color: rgba(0, 229, 255, 0.1); padding: 5px 10px; border-radius: 4px;">
            <img src="{ICON_CURVES}" width="24" height="24" align="middle"> Kurvenverwaltung
        </h3>

        <h4 style="font-size: 15px; color: #00e5ff; margin-top: 15px; margin-bottom: 5px;">PID-Modus</h4>
        <p style="font-size: 14px;">Im Gegensatz zum automatischen Modus verwendet der PID-Modus einen Algorithmus, der die Leistung dynamisch anpasst, um den gewählten Referenzsensor basierend auf der Echtzeit-Systemlast auf der eingestellten Temperatur (<b>Ziel</b>) zu halten.</p>
        <p style="font-size: 14px;">Die Software bietet drei voreingestellte Profile (<b>Langsam, Normal, Schnell</b>). Für erfahrene Benutzer ermöglicht der <b>Manuell</b>-Modus die Definition der drei mathematischen Parameter, um den Algorithmus an die spezifischen Eigenschaften Ihres Systems anzupassen:</p>

        <ul style="margin-top: 5px; margin-bottom: 15px;">
            <li style="font-size: 14px; margin-bottom: 8px;"><b style="color: #cba6f7;">Proportional (P):</b> Passt die grundlegende Empfindlichkeit gegenüber Temperaturschwankungen an. Er reagiert auf die momentane Differenz zwischen der erfassten Temperatur und dem <b>Ziel</b>. Ein zu hoher Wert macht den Algorithmus übermäßig reaktiv und löst kontinuierliche Schwankungen der Lüfterdrehzahl aus. Erhöhen Sie ihn in Schritten von <b>0.5</b>.</li>
            <li style="font-size: 14px; margin-bottom: 8px;"><b style="color: #cba6f7;">Integral (I):</b> Verwaltet die kumulative Kompensation über einen langen Zeitraum. Er analysiert die außerhalb des <b>Ziels</b> verbrachte Zeit und akkumuliert die notwendige Korrektur, um die Lüfter auf die erforderliche Drehzahl (z. B. konstant 60 %) zu bringen, um die Sensortemperatur stabil zu halten. Aufgrund der hohen thermischen Trägheit von Wasser muss dieser Wert sehr niedrig gehalten werden. Ändern Sie ihn in kleinen Schritten von <b>0.01</b>.</li>
            <li style="font-size: 14px; margin-bottom: 8px;"><b style="color: #cba6f7;">Derivativ (D):</b> Wendet eine dynamische Dämpfung basierend auf der Geschwindigkeit der Temperaturänderung an. <b>In Flüssigkeitssystemen wird empfohlen, ihn nahe 0 zu halten.</b> Da sich Wasser allmählich erwärmt, würde ein zu hoher Wert zu plötzlichen und ungerechtfertigten Drehzahlsprüngen als Reaktion auf minimale Schwankungen der Sensorwerte führen.</li>
        </ul>

        <div style="margin-top: 15px; margin-bottom: 15px;">
            <h4 style="font-size: 15px; color: #00e5ff; margin-bottom: 5px;"><img src="{ICON_LAMP}" width="16" height="16" align="middle"> Richtwerte (Software-Voreinstellungen)</h4>
            <p style="font-size: 14px; margin-top: 0; margin-bottom: 10px;">Wenn Sie eine manuelle Kurve erstellen möchten, verwenden Sie diese Werte als Ausgangspunkt zur Orientierung:</p>
            <div style="color: #cdd6f4; background-color: rgba(0, 229, 255, 0.1); padding: 8px; border-left: 4px solid #00e5ff; margin-bottom: 8px; font-size: 13px; font-family: monospace;"><b>Langsam:</b> P = 3.0 | I = 0.05 | D = 0.1</div>
            <div style="color: #cdd6f4; background-color: rgba(0, 229, 255, 0.1); padding: 8px; border-left: 4px solid #00e5ff; margin-bottom: 8px; font-size: 13px; font-family: monospace;"><b>Normal:</b> P = 5.0 | I = 0.08 | D = 0.3</div>
            <div style="color: #cdd6f4; background-color: rgba(0, 229, 255, 0.1); padding: 8px; border-left: 4px solid #00e5ff; margin-bottom: 8px; font-size: 13px; font-family: monospace;"><b>Schnell:</b> P = 8.0 | I = 0.10 | D = 0.5</div>
        </div>

        <h4 style="font-size: 15px; color: #00e5ff; margin-top: 15px; margin-bottom: 5px;">Virtueller Sensor (ΔT)</h4>
        <p style="font-size: 14px;">Durch Aktivieren des <b>Virtuellen Sensors (ΔT)</b> berechnet AquaControl ständig die Differenz zwischen dem eingestellten Hauptsensor und einem zweiten Referenzsensor: <br><code style="background-color: #1e1e2e; padding: 2px 5px;">[Hauptsensor] - [Referenz] = ΔT</code></p>
        <p style="font-size: 14px;"><b>Typisches Anwendungsszenario:</b><br>
        In einem herkömmlichen Flüssigkeitskühlsystem kann die Temperatur der Komponenten niemals unter die Umgebungstemperatur fallen. Eine Kurve, die darauf eingestellt ist, die Flüssigkeit bei 35 °C zu halten, funktioniert im Winter. Im Sommer (mit Tamb > 35 °C) erzwingt sie jedoch eine Lüfterleistung von 100 %, um eine physikalisch unmögliche Temperatur zu erreichen.</p>
        <p style="font-size: 14px;">Durch Subtraktion der <i>Lufttemperatur</i> (Referenz) von der <i>Flüssigkeitstemperatur</i> (Hauptsensor) ist es möglich, ein PID-<b>Ziel</b> oder eine Kurve basierend auf einem <b>ΔT von 10 °C</b> einzustellen. Auf diese Weise hält das System das Wasser im Winter auf 30 °C (20 °C Umgebung + 10) und im Sommer auf 40 °C (30 °C Umgebung + 10).</p>

        <h4 style="font-size: 15px; color: #00e5ff; margin-top: 15px; margin-bottom: 5px;">Automatischer Profilwechsel (Auto-Switch)</h4>
        <p style="font-size: 14px;">Diese Funktion ermöglicht es AquaControl, ein spezifisches Profil zu laden, wenn Sie bestimmte Programme starten, und das Standardprofil beim Schließen wiederherzustellen.</p>
        <p style="font-size: 14px;">Da es sich um eine native Linux-Software handelt, ist es nicht erforderlich, den Pfad der ausführbaren Datei zu suchen. Geben Sie einfach den <b>Programmnamen</b> so ein, wie er in das Systemterminal eingegeben würde (z. B. <code>steam</code>, <code>firefox</code>, <code>blender</code>), um sicherzustellen, dass die Software den Programmstart erkennt.</p>

        <hr style="border: 1px solid #313244; margin: 25px 0;">

        <h3 style="font-size: 16px; color: #00e5ff; background-color: rgba(0, 229, 255, 0.1); padding: 5px 10px; border-radius: 4px;">
            <img src="{ICON_HARDWARE}" width="24" height="24" align="middle"> Hardware-Konfiguration
        </h3>

        <h4 style="font-size: 15px; color: #00e5ff; margin-top: 15px; margin-bottom: 5px;">Minimale Leistung (Blockierschutz)</h4>
        <p style="font-size: 14px;">Lüfter- und Pumpenmotoren haben eine physikalische Grenze, unterhalb derer sie sich nicht drehen können. Beispiel: Wenn dieses Limit auf 25 % eingestellt wird, berechnet die Software die gesamte Kurve neu, sodass 0 % im Diagramm den an den Motor gesendeten 25 % entsprechen. Unterhalb des Mindestwerts unterbricht der Kanal die Stromversorgung vollständig, schaltet das Gerät ab und vermeidet so störendes elektrisches Summen oder Motorschäden durch längeres Blockieren.</p>

        <h4 style="font-size: 15px; color: #00e5ff; margin-top: 15px; margin-bottom: 5px;">Start Boost (Schnellstart)</h4>
        <p style="font-size: 14px;">Trägheit ist ein nicht zu vernachlässigendes Element in einem physikalischen System. Ein Lüfter, der stabil bei 20 % dreht, hat möglicherweise nicht genug Kraft, um bei demselben Prozentsatz aus dem Stillstand zu <i>starten</i>. Durch Aktivieren von <i>Start Boost</i> sendet der Controller bei jedem Einschalten des Kanals für den Bruchteil einer Sekunde (konfigurierbare Dauer) einen 100 %-Leistungsimpuls, um dem Rotor einen Schubs zu geben, und regelt ihn dann sofort auf die von der eingestellten Kurve geforderte Geschwindigkeit ein.</p>

        <hr style="border: 1px solid #313244; margin: 25px 0;">

        <h3 style="font-size: 16px; color: #ff3333; background-color: rgba(255, 51, 51, 0.1); padding: 5px 10px; border-radius: 4px;">
            <img src="{ICON_SECURITY}" width="24" height="24" align="middle"> Sicherheitseinstellungen (Fail-Safe)
        </h3>
        <p style="font-size: 14px;">Das Sicherheitssystem greift automatisch ein, um Hardwareschäden zu verhindern. Das Notfallsystem verfügt über zwei separate Einstellungen, die bestimmten Zwecken dienen:</p>

        <p style="font-size: 14px;"><b>1. Alarmverzögerung (Empfindlichkeit)</b><br>
        Konfigurierbar für jeden einzelnen Kanal, definiert es, <b>wie viele Sekunden</b> ein kritischer Wert anhalten muss, bevor das Notfallsystem ausgelöst wird. Beispiel: Wenn eine Pumpe auf 0 RPM fällt, die <i>Alarmverzögerung</i> jedoch auf 3 Sekunden eingestellt ist, wartet die Software. Startet die Pumpe innerhalb von 3 Sekunden wieder (z. B. Aufwachen aus dem PC-Ruhezustand), wird der Alarm nicht ausgelöst. Diese Funktion wurde integriert, um Fehlalarme zu vermeiden, die beim Aufwachen aus dem Ruhezustand auftreten konnten.</p>

        <p style="font-size: 14px;"><b>2. Globale Aktionen und Wartezeit vor Herunterfahren</b><br>
        Sobald das Notfallsystem aktiviert ist, führt die Software die angeforderten Aktionen aus (Benachrichtigungen, akustische Alarme, Ausführung benutzerdefinierter Skripte). Wenn Sie das <i>Not-Aus erzwingen</i> in Kombination mit einem benutzerdefinierten Befehl (z. B. ein Skript zum Speichern geöffneter Dateien) aktiviert haben, können Sie mit der Option <b>Wartezeit für Befehlsausführung</b> das System zwingen, <b>X</b> Sekunden zu warten, bevor der Strom gewaltsam abgeschaltet wird, damit das Skript Zeit hat, seine Aufgabe zu beenden.</p>
    """,

    "ru": f"""
        <h2 style="font-size: 18px; color: #cdd6f4; margin-top: 0; margin-bottom: 10px;">Руководство по расширенным функциям программы</h2>
        <p style="font-size: 14px; color: #a6adc8; margin-bottom: 16px;">В этом руководстве объясняется работа расширенной логики программного обеспечения, разделенной на разделы.</p>

        <h3 style="font-size: 16px; color: #00e5ff; background-color: rgba(0, 229, 255, 0.1); padding: 5px 10px; border-radius: 4px;">
            <img src="{ICON_CURVES}" width="24" height="24" align="middle"> Управление кривыми
        </h3>

        <h4 style="font-size: 15px; color: #00e5ff; margin-top: 15px; margin-bottom: 5px;">Режим PID</h4>
        <p style="font-size: 14px;">В отличие от автоматического режима, режим PID использует алгоритм, который динамически адаптирует мощность для поддержания выбранного эталонного датчика на заданной температуре (<b>Цель</b>) в зависимости от нагрузки системы в реальном времени.</p>
        <p style="font-size: 14px;">Программное обеспечение предлагает три предустановленных профиля (<b>Медленно, Нормально, Быстро</b>). Для опытных пользователей режим <b>Вручную</b> позволяет задать три математических параметра для адаптации алгоритма к специфическим характеристикам вашей системы:</p>

        <ul style="margin-top: 5px; margin-bottom: 15px;">
            <li style="font-size: 14px; margin-bottom: 8px;"><b style="color: #cba6f7;">Пропорциональный (P):</b> Регулирует базовую чувствительность к изменениям температуры. Действует в ответ на мгновенную разницу между обнаруженной температурой и <b>Целью</b>. Слишком высокое значение делает алгоритм чрезмерно реактивным, вызывая постоянные колебания скорости вращения вентиляторов. Увеличивайте с шагом <b>0.5</b>.</li>
            <li style="font-size: 14px; margin-bottom: 8px;"><b style="color: #cba6f7;">Интегральный (I):</b> Управляет кумулятивной компенсацией в долгосрочной перспективе. Анализирует время, проведенное за пределами <b>Цели</b>, и накапливает необходимую коррекцию, чтобы вентиляторы достигли требуемой скорости вращения (например, стабильные 60%) для стабильного поддержания температуры датчика. Из-за высокой тепловой инерции воды это значение должно оставаться очень низким. Изменяйте его небольшими шагами по <b>0.01</b>.</li>
            <li style="font-size: 14px; margin-bottom: 8px;"><b style="color: #cba6f7;">Дифференциальный (D):</b> Применяет динамическое демпфирование в зависимости от скорости изменения температуры. <b>В жидкостных системах рекомендуется держать его близким к 0.</b> Поскольку вода нагревается постепенно, чрезмерно высокое значение приведет к внезапным и необоснованным скачкам вращения в ответ на минимальные колебания показаний датчика.</li>
        </ul>

        <div style="margin-top: 15px; margin-bottom: 15px;">
            <h4 style="font-size: 15px; color: #00e5ff; margin-bottom: 5px;"><img src="{ICON_LAMP}" width="16" height="16" align="middle"> Справочные значения (Пресеты ПО)</h4>
            <p style="font-size: 14px; margin-top: 0; margin-bottom: 10px;">Если вы хотите создать кривую вручную, используйте эти параметры в качестве отправной точки:</p>
            <div style="color: #cdd6f4; background-color: rgba(0, 229, 255, 0.1); padding: 8px; border-left: 4px solid #00e5ff; margin-bottom: 8px; font-size: 13px; font-family: monospace;"><b>Медленно:</b> P = 3.0 | I = 0.05 | D = 0.1</div>
            <div style="color: #cdd6f4; background-color: rgba(0, 229, 255, 0.1); padding: 8px; border-left: 4px solid #00e5ff; margin-bottom: 8px; font-size: 13px; font-family: monospace;"><b>Нормально:</b> P = 5.0 | I = 0.08 | D = 0.3</div>
            <div style="color: #cdd6f4; background-color: rgba(0, 229, 255, 0.1); padding: 8px; border-left: 4px solid #00e5ff; margin-bottom: 8px; font-size: 13px; font-family: monospace;"><b>Быстро:</b> P = 8.0 | I = 0.10 | D = 0.5</div>
        </div>

        <h4 style="font-size: 15px; color: #00e5ff; margin-top: 15px; margin-bottom: 5px;">Виртуальный датчик (ΔT)</h4>
        <p style="font-size: 14px;">При активации <b>Виртуального датчика (ΔT)</b> AquaControl постоянно вычисляет разницу между заданным основным датчиком и вторым эталонным датчиком: <br><code style="background-color: #1e1e2e; padding: 2px 5px;">[Основной] - [Эталонный] = ΔT</code></p>
        <p style="font-size: 14px;"><b>Типичный сценарий использования:</b><br>
        В обычной системе жидкостного охлаждения температура компонентов никогда не может опуститься ниже температуры окружающей среды. Кривая, настроенная на поддержание температуры жидкости на уровне 35°C, будет работать зимой, но летом (при T_окруж > 35°C) заставит вентиляторы работать на 100% для достижения физически невозможной температуры.</p>
        <p style="font-size: 14px;">Вычтя <i>Температуру воздуха</i> (эталон) из <i>Температуры жидкости</i> (основной), можно установить <b>Цель</b> PID или кривую на основе <b>ΔT 10°C</b>. Таким образом, система будет поддерживать температуру воды на уровне 30°C зимой (20°C окруж. + 10) и 40°C летом (30°C окруж. + 10).</p>

        <h4 style="font-size: 15px; color: #00e5ff; margin-top: 15px; margin-bottom: 5px;">Автопереключение профиля (Auto-Switch)</h4>
        <p style="font-size: 14px;">Эта функция позволяет AquaControl загружать определенный профиль при запуске определенных программ, а затем восстанавливать профиль по умолчанию при их закрытии.</p>
        <p style="font-size: 14px;">Поскольку это нативное программное обеспечение Linux, нет необходимости искать путь к исполняемому файлу. Просто введите <b>имя программы</b> так, как оно было бы введено в системном терминале (например, <code>steam</code>, <code>firefox</code>, <code>blender</code>), чтобы программное обеспечение распознало открытие программы.</p>

        <hr style="border: 1px solid #313244; margin: 25px 0;">

        <h3 style="font-size: 16px; color: #00e5ff; background-color: rgba(0, 229, 255, 0.1); padding: 5px 10px; border-radius: 4px;">
            <img src="{ICON_HARDWARE}" width="24" height="24" align="middle"> Настройки оборудования
        </h3>

        <h4 style="font-size: 15px; color: #00e5ff; margin-top: 15px; margin-bottom: 5px;">Мин. мощность (Предотвращение остановки)</h4>
        <p style="font-size: 14px;">Двигатели вентиляторов и помп имеют физический предел, ниже которого они не могут вращаться. Пример: при установке этого предела на 25%, программное обеспечение пересчитает всю кривую так, чтобы 0% на графике соответствовало 25%, отправляемым на двигатель. Ниже минимального значения канал полностью отключит питание, выключив периферийное устройство и избежав тем самым раздражающего электрического гудения или повреждения двигателя из-за длительной остановки.</p>

        <h4 style="font-size: 15px; color: #00e5ff; margin-top: 15px; margin-bottom: 5px;">Start Boost (Быстрый старт)</h4>
        <p style="font-size: 14px;">Инерция — значительный элемент в физической системе. Вентилятор, который стабильно вращается на 20%, может не иметь достаточной силы, чтобы <i>начать</i> вращаться с нуля при том же проценте. При активации <i>Start Boost</i> каждый раз при включении канала контроллер будет посылать импульс мощности 100% на долю секунды (настраиваемая длительность), чтобы дать ротору толчок, а затем мгновенно установит его на скорость, требуемую заданной кривой.</p>

        <hr style="border: 1px solid #313244; margin: 25px 0;">

        <h3 style="font-size: 16px; color: #ff3333; background-color: rgba(255, 51, 51, 0.1); padding: 5px 10px; border-radius: 4px;">
            <img src="{ICON_SECURITY}" width="24" height="24" align="middle"> Настройки безопасности (Fail-Safe)
        </h3>
        <p style="font-size: 14px;">Система безопасности автоматически вмешивается для предотвращения повреждения оборудования. Экстренная система имеет две отдельные настройки со своими специфическими целями:</p>

        <p style="font-size: 14px;"><b>1. Задержка тревоги (Чувствительность)</b><br>
        Настраивается для каждого отдельного канала, определяет, <b>сколько секунд</b> должно сохраняться критическое значение до срабатывания экстренной системы. Пример: если скорость помпы падает до 0 RPM, но <i>Задержка тревоги</i> установлена на 3 секунды, программа подождет. Если помпа перезапустится в течение 3 секунд (например, при выходе ПК из спящего режима), тревога не сработает. Эта функция была интегрирована специально во избежание ложных срабатываний при выходе из сна.</p>

        <p style="font-size: 14px;"><b>2. Глобальные действия и Ожидание выключения</b><br>
        После срабатывания экстренной системы программа выполняет запрошенные действия (уведомления, звуковые сигналы, выполнение пользовательских скриптов). Если вы активировали <i>Принудительное выключение</i> в сочетании с пользовательской командой (например, скрипт для сохранения открытых файлов), опция <b>Ожидание выполнения команды</b> позволяет заставить систему подождать <b>X</b> секунд перед принудительным отключением питания, давая скрипту время завершить свою задачу.</p>
    """,

    "zh": f"""
        <h2 style="font-size: 18px; color: #cdd6f4; margin-top: 0; margin-bottom: 10px;">程序高级功能指南</h2>
        <p style="font-size: 14px; color: #a6adc8; margin-bottom: 16px;">本指南说明了软件高级逻辑的运行方式，分为多个部分。</p>

        <h3 style="font-size: 16px; color: #00e5ff; background-color: rgba(0, 229, 255, 0.1); padding: 5px 10px; border-radius: 4px;">
            <img src="{ICON_CURVES}" width="24" height="24" align="middle"> 曲线管理
        </h3>

        <h4 style="font-size: 15px; color: #00e5ff; margin-top: 15px; margin-bottom: 5px;">PID 模式</h4>
        <p style="font-size: 14px;">与自动模式不同，PID 模式使用一种算法，根据实时系统负载，动态调整功率，使所选参考传感器保持在设定温度（<b>目标</b>）。</p>
        <p style="font-size: 14px;">软件提供三种预设配置文件（<b>慢、正常、快</b>）。对于高级用户，<b>手动</b>模式允许您定义三个数学参数，以使算法适应您系统的特定特性：</p>

        <ul style="margin-top: 5px; margin-bottom: 15px;">
            <li style="font-size: 14px; margin-bottom: 8px;"><b style="color: #cba6f7;">比例 (P):</b> 调整对温度变化的基本灵敏度。它响应于检测到的温度与<b>目标</b>之间的瞬时差异。过高的值会使算法反应过度，引发风扇转速的连续振荡。请以 <b>0.5</b> 的步长增加它。</li>
            <li style="font-size: 14px; margin-bottom: 8px;"><b style="color: #cba6f7;">积分 (I):</b> 管理长期的累积补偿。它分析偏离<b>目标</b>的时间，并积累必要的修正量，使风扇收敛到所需的转速（例如固定的 60%）以稳定地保持传感器温度。由于水的高热惯性，该值必须保持得非常低。请以 <b>0.01</b> 的小步长修改它。</li>
            <li style="font-size: 14px; margin-bottom: 8px;"><b style="color: #cba6f7;">微分 (D):</b> 根据温度变化的速度应用动态阻尼。<b>在水冷系统中，建议将其保持在接近 0 的位置。</b> 由于水是逐渐加热的，过高的值会导致针对极小的传感器读数波动产生突然且不合理的转速峰值。</li>
        </ul>

        <div style="margin-top: 15px; margin-bottom: 15px;">
            <h4 style="font-size: 15px; color: #00e5ff; margin-bottom: 5px;"><img src="{ICON_LAMP}" width="16" height="16" align="middle"> 参考值 (软件预设)</h4>
            <p style="font-size: 14px; margin-top: 0; margin-bottom: 10px;">如果您想创建手动曲线，请使用这些值作为起点指南：</p>
            <div style="color: #cdd6f4; background-color: rgba(0, 229, 255, 0.1); padding: 8px; border-left: 4px solid #00e5ff; margin-bottom: 8px; font-size: 13px; font-family: monospace;"><b>慢:</b> P = 3.0 | I = 0.05 | D = 0.1</div>
            <div style="color: #cdd6f4; background-color: rgba(0, 229, 255, 0.1); padding: 8px; border-left: 4px solid #00e5ff; margin-bottom: 8px; font-size: 13px; font-family: monospace;"><b>正常:</b> P = 5.0 | I = 0.08 | D = 0.3</div>
            <div style="color: #cdd6f4; background-color: rgba(0, 229, 255, 0.1); padding: 8px; border-left: 4px solid #00e5ff; margin-bottom: 8px; font-size: 13px; font-family: monospace;"><b>快:</b> P = 8.0 | I = 0.10 | D = 0.5</div>
        </div>

        <h4 style="font-size: 15px; color: #00e5ff; margin-top: 15px; margin-bottom: 5px;">虚拟传感器 (ΔT)</h4>
        <p style="font-size: 14px;">通过激活<b>虚拟传感器 (ΔT)</b>，AquaControl 会持续计算设定的主传感器与第二个参考传感器之间的温差：<br><code style="background-color: #1e1e2e; padding: 2px 5px;">[主传感器] - [参考] = ΔT</code></p>
        <p style="font-size: 14px;"><b>典型使用场景：</b><br>
        在传统的液冷系统中，组件温度永远不会降至环境温度以下。设置为将液体保持在 35°C 的曲线在冬天可以工作，但在夏天（当环境温度 > 35°C 时），它将迫使风扇达到 100% 以试图达到物理上不可能的温度。</p>
        <p style="font-size: 14px;">通过从<i>液体温度</i>（主传感器）中减去<i>空气温度</i>（参考），可以设置 PID <b>目标</b>或基于 <b>ΔT 为 10°C</b> 的曲线。这样，系统将在冬天将水温保持在 30°C（20°C 环境温度 + 10），而在夏天将水温保持在 40°C（30°C 环境温度 + 10）。</p>

        <h4 style="font-size: 15px; color: #00e5ff; margin-top: 15px; margin-bottom: 5px;">自动切换配置文件 (Auto-Switch)</h4>
        <p style="font-size: 14px;">此功能允许 AquaControl 在您启动某些程序时加载特定的配置文件，然后在它们关闭时恢复默认配置文件。</p>
        <p style="font-size: 14px;">由于它是原生的 Linux 软件，因此无需查找可执行文件路径。只需输入在系统终端中输入的<b>程序名称</b>（例如 <code>steam</code>、<code>firefox</code>、<code>blender</code>），即可确保软件检测到程序打开。</p>

        <hr style="border: 1px solid #313244; margin: 25px 0;">

        <h3 style="font-size: 16px; color: #00e5ff; background-color: rgba(0, 229, 255, 0.1); padding: 5px 10px; border-radius: 4px;">
            <img src="{ICON_HARDWARE}" width="24" height="24" align="middle"> 硬件配置
        </h3>

        <h4 style="font-size: 15px; color: #00e5ff; margin-top: 15px; margin-bottom: 5px;">最小功率 (防止失速)</h4>
        <p style="font-size: 14px;">风扇和泵电机具有物理限制，低于该限制则无法旋转。例如：通过将此限制设置为 25%，软件将重新计算整个曲线，以便图表上的 0% 对应于发送到电机的 25%。低于最小值时，通道将完全切断电源，关闭外围设备，从而避免由于长时间失速而产生烦人的电流嗡嗡声或电机损坏。</p>

        <h4 style="font-size: 15px; color: #00e5ff; margin-top: 15px; margin-bottom: 5px;">启动加速 (快速启动)</h4>
        <p style="font-size: 14px;">惯性是物理系统中的一个重要因素。以 20% 稳定旋转的风扇可能没有足够的力量以相同的百分比从零<i>开始</i>旋转。通过激活<i>启动加速</i>，每次通道开启时，控制器将在几分之一秒（持续时间可配置）内发送 100% 的功率脉冲来推动转子，然后立即将其稳定在设定曲线所需的速度。</p>

        <hr style="border: 1px solid #313244; margin: 25px 0;">

        <h3 style="font-size: 16px; color: #ff3333; background-color: rgba(255, 51, 51, 0.1); padding: 5px 10px; border-radius: 4px;">
            <img src="{ICON_SECURITY}" width="24" height="24" align="middle"> 安全设置 (Fail-Safe)
        </h3>
        <p style="font-size: 14px;">安全系统会自动干预以防止硬件损坏。紧急系统有两个单独的设置，具有特定用途：</p>

        <p style="font-size: 14px;"><b>1. 警报延迟 (灵敏度)</b><br>
        可为每个单独的通道进行配置，它定义了在触发紧急系统之前临界值必须持续<b>多少秒</b>。示例：如果泵降至 0 RPM，但<i>警报延迟</i>设置为 3 秒，软件将等待。如果泵在 3 秒内重新启动（例如，从 PC 睡眠状态唤醒），则不会触发警报。集成此功能正是为了避免从睡眠中恢复时可能出现的错误警报。</p>

        <p style="font-size: 14px;"><b>2. 全局操作和关机等待</b><br>
        紧急系统触发后，软件将执行请求的操作（通知、声音警报、自定义脚本执行）。如果您结合自定义命令（例如，用于保存打开的文件的脚本）激活了<i>紧急强制关机</i>，则<b>等待命令执行</b>选项允许您强制系统在强制切断电源之前等待 <b>X</b> 秒，从而为脚本留出完成其任务的时间。</p>
    """,

    "la": f"""
        <h2 style="font-size: 18px; color: #FFD700; margin-top: 0; margin-bottom: 10px;">Manifestum Imperiale</h2>

        <p style="font-size: 14px; color: #a6adc8; margin-bottom: 16px;">Hail, web wanderers, Gatekeepers of perfect code, and keyboard warriors of various kinds. If you are reading this digital parchment, chances are you have scoured the repository looking for the least elegant line of code to point me out as incompetent, to rant against "AI-generated trash", or to indignantly report some bug due to my lack of omniscience regarding Linux or programming.</p>
        <p style="font-size: 14px; color: #a6adc8; margin-bottom: 16px;">To you I say: <i>Errare humanum est, perseverare in Windows diabolicum.</i></p>

        <p style="font-size: 14px; color: #a6adc8; margin-bottom: 12px;">Let's get a couple of things straight. I am not a Senior programmer. I am learning. This project is born from the mud and blood of pure and simple frustration. The frustration of having spent my sesterces on magnificent hardware only to find myself chained to that Windows bloatware just to be able to use it.</p>

        <p style="font-size: 14px; color: #a6adc8; margin-bottom: 12px;">I could have written a trivial Python script for my own personal use, just to make my fans spin the way I wanted, and kept it on my PC. Et instead, no. I have worked from January 2026 to today, sacrificing countless hours (now counted in entire 24-hour weeks) and paying out of my own pocket for artificial oracles just to reverse-engineer closed hardware, generating code based on my logic, which I still had to personally test and review by hand. Do I use the animated RGB effects of the Farbwerk 360? No, static color was enough for me. But I used Wireshark to capture the payloads and decipher the effects solely to offer you all an Open Source alternative on Linux that currently no one (not even the excellent CoolerControl) is capable of managing in this way. And all this <i>gratis et amore dei</i>, at a pure loss.</p>

        <p style="font-size: 14px; color: #a6adc8; margin-bottom: 12px;">"Why doesn't AquaControl support other hardware?" I don't own it at the moment, ergo I cannot write code and test it myself. Furthermore, the parent company uses closed protocols. At the next firmware update, these gentlemen could change a comma in the code and send all this work of mine down the drain in a second. Enjoy this freedom while it lasts.</p>

        <p style="font-size: 14px; color: #FFD700; font-weight: bold; margin-top: 20px; margin-bottom: 8px;">One last note for the historical pedants and grammar nazis: the "Imperium" interface is a prank, a joke, a divertissement.</p>

        <ul style="margin-top: 5px; margin-bottom: 15px;">
            <li style="font-size: 14px; color: #a6adc8; margin-bottom: 8px;"><b style="color: #FFD700;">Roman numerals with a comma</b> (e.g., XII,NIV Volt) DO NOT exist. Zero (represented here by the 'N' for Nihil) was not conceived.</li>
            <li style="font-size: 14px; color: #a6adc8; margin-bottom: 8px;"><b style="color: #FFD700;">Degrees of Galen (°G)</b> DO NOT exist. No centurion two thousand years ago had to measure the thermal deltas of a liquid cooling loop for a CPU.</li>
            <li style="font-size: 14px; color: #a6adc8; margin-bottom: 8px;"><b style="color: #FFD700;">Latin translations</b> in the IT field are, obviously, macaronic concoctions.</li>
        </ul>

        <p style="font-size: 14px; color: #a6adc8; margin-bottom: 12px;">The idea of restructuring the entire software to use historically accurate Roman fractions instead of decimals would have been pure madness. It's a compromise: it makes you laugh, it makes historians turn up their noses, but it works and it's readable. If you can't grasp the irony and get outraged by the philological inaccuracy of my translations or the use of AI... I'll get over it.</p>

        <p style="font-size: 14px; color: #a6adc8; margin-bottom: 12px;">If the software is useful to you, you're welcome. If it disgusts you, open your favorite editor and write your own daemon from scratch. <b>Roma locuta, causa finita.</b></p>
    """,
}

def get_guide_text():
    lang = global_config.get("lang", "en")
    return GUIDE_TRANSLATIONS.get(lang, GUIDE_TRANSLATIONS["en"])
