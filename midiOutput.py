from time import monotonic, sleep

from config import (
    MIDI_CC_DELAY,
    MIDI_EXPRESSION_CC_DELAY,
    MIDI_PC_DELAY,
    MIDI_PRESET_VOLUME_REASSERT_DELAY,
    MIDI_PRESET_VOLUME_REASSERT_ENABLED,
    VOLUME_CC,
)


gMidiOutput = None
gCurrentVolumeList = None
gPendingVolumeReassertDict = {}
gPrintDebug = None


def setMidiOutput(midiOutput):
    global gMidiOutput
    gMidiOutput = midiOutput


def setPrintDebug(printDebug):
    global gPrintDebug
    gPrintDebug = printDebug


def setCurrentVolumeList(volumeList):
    global gCurrentVolumeList
    gCurrentVolumeList = volumeList


def sendCCMessage(channel, CC, value):
    _debugMidi("CC", channel, CC, value)
    gMidiOutput.write_short(0xb0 + int(channel) - 1, int(CC), int(value))
    sleep(MIDI_CC_DELAY)


def sendPCMessage(channel, PC):
    _debugMidi("PC", channel, PC)
    gMidiOutput.write_short(0xc0 + int(channel) - 1, int(PC))
    sleep(MIDI_PC_DELAY)


def sendGenericMidiCommand(msg0, msg1, msg2):
    _debug(f">>> MIDI OUT GENERIC statusBase={msg0}, data1={msg1}, data2={msg2}")
    gMidiOutput.write_short(0xb0 + int(msg0), msg1, msg2)


def muteChannel(channel, volume, step):
    if volume > 0:
        x = volume
        while x > 0:
            sendCCMessage(channel, VOLUME_CC, x)
            x = x - step
        sendCCMessage(channel, VOLUME_CC, 0)


def unmuteChannel(channel, volume, step):
    x = step
    while x < volume:
        sendCCMessage(channel, VOLUME_CC, x)
        x = x + step


def calibratePedalVolume(maxValue, value):
    result = int(127 / maxValue * value)
    if result < 6:
        result = 0
    if result > 127:
        result = 127
    return result


def scheduleVolumeReassert(channel, volume):
    if not MIDI_PRESET_VOLUME_REASSERT_ENABLED:
        return

    gPendingVolumeReassertDict[int(channel)] = {
        "volume": int(volume),
        "dueTime": monotonic() + MIDI_PRESET_VOLUME_REASSERT_DELAY,
    }
    _debug(
        f">>> MIDI OUT SCHEDULE VOLUME REASSERT channel={channel}, cc={VOLUME_CC}, "
        f"value={int(volume)}, delay={MIDI_PRESET_VOLUME_REASSERT_DELAY}")


def cancelPendingVolumeReassert(channel):
    if gPendingVolumeReassertDict.pop(int(channel), None):
        _debug(f">>> MIDI OUT CANCEL VOLUME REASSERT channel={channel}")


def processPendingVolumeReasserts():
    now = monotonic()
    dueChannels = [
        channel
        for channel, pendingVolume in gPendingVolumeReassertDict.items()
        if pendingVolume["dueTime"] <= now
    ]

    for channel in dueChannels:
        pendingVolume = gPendingVolumeReassertDict.pop(channel, None)
        if pendingVolume:
            _debug(f">>> MIDI OUT REASSERT VOLUME channel={channel}, cc={VOLUME_CC}, value={pendingVolume['volume']}")
            sendCCMessage(channel, VOLUME_CC, pendingVolume["volume"])


def sendPedalVolumeCC(channel, idx, volume):
    cancelPendingVolumeReassert(channel)
    maxVol = gCurrentVolumeList[idx]
    if volume <= maxVol:
        _debug(
            f">>> MIDI OUT EXPRESSION VOLUME channel={channel}, idx={idx}, cc={VOLUME_CC}, "
            f"value={int(volume)}, max={maxVol}")
        gMidiOutput.write_short(0xb0 + int(channel) - 1, VOLUME_CC, int(volume))
        sleep(MIDI_EXPRESSION_CC_DELAY)
    else:
        _debug(
            f">>> MIDI OUT EXPRESSION VOLUME SKIP channel={channel}, idx={idx}, cc={VOLUME_CC}, "
            f"value={int(volume)}, max={maxVol}")


def _debugMidi(messageType, channel, data1, data2=None):
    if data2 is None:
        _debug(f">>> MIDI OUT {messageType} channel={channel}, pc={data1}")
    else:
        _debug(f">>> MIDI OUT {messageType} channel={channel}, cc={data1}, value={data2}")


def _debug(message):
    if gPrintDebug:
        gPrintDebug(message)
