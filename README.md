# FCB Controller

Python MIDI controller for the VGMates FCB1010/Raspberry Pi live rig.

The controller receives direct MIDI from the Behringer FCB1010, sends Program Change and Control Change messages to the live devices, updates the OLED display, and exchanges live state notifications with the API.

## Live Device Order

Song-program preset slots are fixed:

1. BiasFX on iPad, MIDI channel 6
2. BiasFX on MacBook, MIDI channel 4
3. SampleTank on iPad, MIDI channel 1
4. Alchemy on MacBook, MIDI channel 2

Expression pedal 1 controls slots 1 and 2. Expression pedal 2 controls slots 3 and 4. BiasFX effect toggles are only processed for slots 1 and 2.

## FCB1010 Bank 8 System Controls

Bank 8 is reserved for controller/system operations:

1. Shutdown Raspberry Pi
2. Reboot Raspberry Pi
3. Restart the Python controller service
6. Select previous gig
7. Select next gig

Shutdown, reboot, and service restart require two consecutive presses of the same button. Previous/next gig execute immediately, wrap around the gig list, show the selected gig on the display, and select the first song in that gig.

Install the narrow sudo policy required by the three privileged controls:

```sh
sudo install -o root -g root -m 0440 scripts/fcbcontroller-sudoers /etc/sudoers.d/fcbcontroller
sudo visudo -cf /etc/sudoers.d/fcbcontroller
```

The controller uses non-interactive sudo and can only power off, reboot, or
restart `fcb1010.service`; it cannot execute arbitrary commands as root.

## Install

Create a virtual environment and install the pinned dependencies:

```sh
python -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Set `FCB_MIDI_INPUT_NAME` and `FCB_MIDI_OUTPUT_NAME` to stable substrings of
the device names. The legacy numeric indices remain as a fallback. API and
Socket.IO endpoints can be overridden with `FCB_API_URL` and
`FCB_MESSAGE_URL`. An example systemd unit is in `scripts/fcb1010.service`.

## Test

```powershell
python -m unittest discover -s tests
```
