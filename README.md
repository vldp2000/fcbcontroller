# FCB Controller

Python MIDI controller for the VGMates FCB1010/Raspberry Pi live rig.

The controller receives direct MIDI from the Behringer FCB1010, sends Program Change and Control Change messages to the live devices, updates the OLED display, and exchanges live state notifications with the API.

## Live Device Order

Song-program preset slots are fixed:

1. BiasFX on iPad, MIDI channel 6
2. SampleTank on iPad, MIDI channel 1
3. BiasFX on MacBook, MIDI channel 4
4. Alchemy on MacBook, MIDI channel 2

Expression pedal 1 controls slots 1 and 3. Expression pedal 2 controls slots 2 and 4. BiasFX effect toggles are only processed for slots 1 and 3.

## FCB1010 Bank 8 System Controls

Bank 8 is reserved for controller/system operations:

1. Shutdown Raspberry Pi
2. Reboot Raspberry Pi
3. Restart the Python controller service
6. Select previous gig
7. Select next gig

Shutdown, reboot, and service restart require two consecutive presses of the same button. Previous/next gig execute immediately, wrap around the gig list, show the selected gig on the display, and select the first song in that gig.

## Test

```powershell
python -m unittest discover -s tests
```
