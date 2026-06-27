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

## Test

```powershell
python -m unittest discover -s tests
```

