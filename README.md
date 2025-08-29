# Meshtastic TTL

this program is comprised of two components: TX and RX. The TX will control a raspberry pi gpio pin upon disconnect from RX. 

The program runs as follows:
1. TX sends countdown to RX
2. RX replies "okay" (this step is comprised of sending three messages, for redundancy)
3. TX recieves reply, decrements countdown

this continues until *either* the TX does not hear a reply, or if the countdown reaches zero.

if the TX doesnt hear a reply, it will decrement a 'grace point' - the current default is 5 points. grace points are meant to account for any issues with the mesh or transmission speed. this can easily be changed later.

upon disconnect, the TX will send GPIO 18 high, in order to light an LED, or power a buzzer. this is user configurable.
