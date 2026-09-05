from time import sleep

import controllerSocket
import dataController
import dataHelper
import midiOutput

from config import (
    BIASFX_EFFECT_TARGETS,
    BIASFX_BOOST_TOGGLE_CC,
    BIASFX_DELAY_TOGGLE_CC,
    BIASFX_MOD_TOGGLE_CC,
    BIASFX_REVERB_TOGGLE_CC,
    VOLUME_CC,
)
from midiOutput import scheduleVolumeReassert, sendCCMessage, sendPCMessage


gDisplayData = None
gPrintDebug = None
gResetSystemCommandCounter = None

gSelectedGigId = -1
gGig = {}
gCurrentSong = {}

gInstrumentChannelDict = {}
gPresetDict = {}
gInstrumentBankDict = {}

gCurrentSongIdx = -1
gCurrentSongId = -1
gCurrentProgramIdx = -1

gCurrentPCList = [0, 0, 0, 0]
gCurrentVolumeList = [0, 0, 0, 0]
gCurrentDelayList = [0, 0, 0, 0]
gCurrentReverbList = [0, 0, 0, 0]
gCurrentModList = [0, 0, 0, 0]
gCurrentBoostList = [0, 0, 0, 0]
gInitialisationComplete = False

midiOutput.setCurrentVolumeList(gCurrentVolumeList)

EFFECT_DELAY = "delay"
EFFECT_REVERB = "reverb"
EFFECT_MOD = "mod"
EFFECT_BOOST = "boost"


def init(displayData, printDebug, resetSystemCommandCounter):
    global gDisplayData
    global gPrintDebug
    global gResetSystemCommandCounter

    gDisplayData = displayData
    gPrintDebug = printDebug
    gResetSystemCommandCounter = resetSystemCommandCounter


def loadAllData():
    global gSelectedGigId
    global gGig
    global gCurrentSong
    global gInstrumentChannelDict
    global gInstrumentBankDict
    global gPresetDict
    global gInitialisationComplete

    _debug(' << Load All Data >>')
    if gGig:
        gGig.clear()
    if gCurrentSong:
        gCurrentSong.clear()
    if gInstrumentChannelDict:
        gInstrumentChannelDict.clear()
    if gInstrumentBankDict:
        gInstrumentBankDict.clear()
    if gPresetDict:
        gPresetDict.clear()

    _debug(' << All objects and collections are cleared>>')

    try:
        gGig = dataHelper.loadScheduledGig()

        if gGig:
            gSelectedGigId = gGig["id"]
            gDisplayData.drawMessage("Gig loaded", gGig["name"])
        else:
            gDisplayData.drawError("Gig not found")
            _debug("Gig not found")
        sleep(1)

        gInstrumentChannelDict = dataHelper.initInstruments()
        if not gInstrumentChannelDict:
            gDisplayData.drawError("Instruments not found")
            sleep(1)

        gPresetDict = dataHelper.initPresets()
        if not gInstrumentChannelDict:
            gDisplayData.drawError("Presets not found")
            sleep(1)

        gInstrumentBankDict = dataHelper.initInstrumentBanks()
        if not gInstrumentChannelDict:
            gDisplayData.drawError("Banks not found")
            sleep(1)

        gDisplayData.setDataAPIStatus(255)
        gInitialisationComplete = True

    except:
        gDisplayData.setDataAPIStatus(0)
        gDisplayData.drawScreen()
        _debug('<< Exception. loadAllData >>')
        gInitialisationComplete = False


def selectFirstSong():
    global gCurrentSongIdx
    global gCurrentSongId
    global gCurrentProgramIdx

    if gGig and gGig["shortSongList"]:
        gCurrentSongIdx = -1
        gCurrentSongId = -1
        selectNextSong(1)
        gCurrentProgramIdx = 0


def refreshCurrentGigIfChanged(payload):
    changedGigId = _extractGigId(payload)
    loadedGigId = _extractGigId(gGig)

    if _isGigSelectionMessage(payload):
        _debug(f"Select gig {changedGigId}")
        _loadGigAndSelectFirstSong(changedGigId)
        return

    if changedGigId != gSelectedGigId and changedGigId != loadedGigId:
        _debug(f"Ignore changed gig {changedGigId}; selected gig is {gSelectedGigId}, loaded gig is {loadedGigId}")
        return

    _debug(f"Reload changed current gig {changedGigId}")
    _loadGigAndSelectFirstSong(changedGigId)


def _loadGigAndSelectFirstSong(gigId):
    global gSelectedGigId
    global gGig
    global gCurrentSong
    global gCurrentSongIdx
    global gCurrentSongId
    global gCurrentProgramIdx

    newGig = dataController.getGig(gigId)
    if not newGig:
        _debug(f"Gig {gigId} could not be loaded")
        return

    gGig = newGig
    gSelectedGigId = gigId
    songCount = len(gGig.get("shortSongList", []))
    _debug(f"Loaded gig {gigId} with {songCount} songs")
    _showGigName(gGig)
    if gGig.get("shortSongList"):
        selectFirstSong()
        return

    controllerSocket.sendGigNotificationMessage(gSelectedGigId)
    if gCurrentSong:
        gCurrentSong.clear()
    gCurrentSongIdx = -1
    gCurrentSongId = -1
    gCurrentProgramIdx = -1
    controllerSocket.sendSongNotificationMessage(-1)
    if gDisplayData:
        gDisplayData.setSongName("")
        gDisplayData.drawScreen()


def selectNextGig(step):
    _resetSystemCommandCounter()

    try:
        gigs = dataController.getGigs()
    except:
        _debug("Gigs not found")
        if gDisplayData:
            gDisplayData.drawError("Gigs not found")
        return

    if not gigs:
        _debug("No gigs configured")
        if gDisplayData:
            gDisplayData.drawError("No gigs")
        return

    currentGigId = gSelectedGigId
    if currentGigId <= 0:
        currentGigId = _extractGigId(gGig)

    currentIdx = -1
    for idx, gig in enumerate(gigs):
        if _extractGigId(gig) == currentGigId:
            currentIdx = idx
            break

    if currentIdx < 0:
        nextIdx = 0 if step > 0 else len(gigs) - 1
    else:
        nextIdx = (currentIdx + step + len(gigs)) % len(gigs)

    nextGigId = _extractGigId(gigs[nextIdx])
    _debug(f"Select gig by pedal. current={currentGigId}, next={nextGigId}, step={step}")
    _loadGigAndSelectFirstSong(nextGigId)


def selectNextSong(step):
    global gCurrentSongIdx

    _resetSystemCommandCounter()
    if step > 0:
        if (gCurrentSongIdx + step < len(gGig["shortSongList"])):
            gCurrentSongIdx = gCurrentSongIdx + step
        else:
            gCurrentSongIdx = 0
    else:
        if gCurrentSongIdx + step > -1:
            gCurrentSongIdx = gCurrentSongIdx + step
        else:
            gCurrentSongIdx = len(gGig["shortSongList"]) - 1

    controllerSocket.sendGigNotificationMessage(gSelectedGigId)
    id = gGig["shortSongList"][gCurrentSongIdx]["id"]

    setCurrentSong(id)
    controllerSocket.sendSongNotificationMessage(id)


def setCurrentSong(id, showSplash=False):
    global gCurrentSong
    global gCurrentSongId

    try:
        if gCurrentSong:
            gCurrentSong.clear()
            gCurrentSong = None

        gCurrentSong = dataController.getSong(id)

        if gCurrentSong:
            gCurrentSongId = gCurrentSong["id"]
            name = gCurrentSong["name"]
            _debug(f"Selected song = {name}")
            gDisplayData.setSongName(f"{gCurrentSongIdx}.{name}")
            setSongProgram(0)
            if showSplash:
                _showSongName(gCurrentSong)
        else:
            _debug("Song corrupted")
            gDisplayData.drawError("Song corrupted")

    except:
        _debug("Song not found")
        gDisplayData.drawError("Song not found")


def setSongProgram(idx):
    global gCurrentProgramIdx

    _resetSystemCommandCounter()
    gCurrentProgramIdx = idx

    program = gCurrentSong["programList"][idx]

    if program:
        _debug(f"Selected program. idx={idx}")
        i = 0
        for songPreset in program['presetList']:
            setPreset(program, songPreset, i)
            i = i + 1

        gDisplayData.drawScreen()
        controllerSocket.sendProgramNotificationMessage(idx)

    else:
        _debug(f"Program {idx} not found")
        gDisplayData.drawError(f"Program {idx} not found")


def setPreset(program, songPreset, idx):
    id = songPreset['refpreset']
    preset = gPresetDict[str(id)]

    if preset:
        channel = int(gInstrumentChannelDict[str(songPreset['refinstrument'])])
        newPC = int(preset['midipc'])
        oldPC = gCurrentPCList[idx]

        newVolume = 0
        if newPC == 0:
            _debug(
                f"Preset Selected slot={idx} instrument={songPreset['refinstrument']} "
                f"channel={channel} presetId={id} preset={preset['name']} "
                f"requestedPC={newPC} cachedPC={oldPC} action=SENT")
            sendCCMessage(channel, VOLUME_CC, newVolume)
            sendPCMessage(channel, newPC)
            sendCCMessage(channel, VOLUME_CC, newVolume)
        else:
            newVolume = songPreset['volume']
            _debug(f"Preset Volume {newVolume}")

            if newVolume > 127:
                newVolume = 127
            if newVolume < 0:
                newVolume = 0

            samePC = newPC == oldPC
            action = "SKIPPED" if samePC else "SENT"
            _debug(
                f"Preset Selected slot={idx} instrument={songPreset['refinstrument']} "
                f"channel={channel} presetId={id} preset={preset['name']} "
                f"requestedPC={newPC} cachedPC={oldPC} action={action}")

            sendCCMessage(channel, VOLUME_CC, 0)

            if not samePC:
                sendPCMessage(channel, newPC)

            processProgramEffects(samePC, idx, channel, songPreset)
            processProgramBoost(samePC, idx, channel, songPreset)

            sendCCMessage(channel, VOLUME_CC, newVolume)

        if preset['refinstrument'] == 1:
            gDisplayData.setProgramName(
                f"{program['name']}.{preset['name']}")

        gCurrentPCList[idx] = newPC
        gCurrentVolumeList[idx] = newVolume
        scheduleVolumeReassert(channel, newVolume)

    else:
        _debug(f"Preset {id} not found")
        gDisplayData.drawError(f"Preset {id} not found")
        sleep(0.2)


def processProgramEffects(samePCFlag, idx, channel, songPreset):
    if not _isBiasFXEffectTarget(channel, idx):
        return

    oldDelay = 0
    oldReverb = 0
    oldMod = 0

    if samePCFlag:
        oldDelay = int(gCurrentDelayList[idx])
        oldReverb = int(gCurrentReverbList[idx])
        oldMod = int(gCurrentModList[idx])

    rawDelayFlag = songPreset.get('delayflag', 0)
    delayFlag = _toEffectFlag(rawDelayFlag)
    if delayFlag != oldDelay:
        _debugEffectDecision("Delay", "SEND", idx, channel, samePCFlag, oldDelay, delayFlag, rawDelayFlag, BIASFX_DELAY_TOGGLE_CC)
        sendCCMessage(channel, BIASFX_DELAY_TOGGLE_CC, 127)
    else:
        _debugEffectDecision("Delay", "SKIP", idx, channel, samePCFlag, oldDelay, delayFlag, rawDelayFlag, BIASFX_DELAY_TOGGLE_CC)

    rawReverbFlag = songPreset.get('reverbflag', 0)
    reverbFlag = _toEffectFlag(rawReverbFlag)
    if reverbFlag != oldReverb:
        _debugEffectDecision("Reverb", "SEND", idx, channel, samePCFlag, oldReverb, reverbFlag, rawReverbFlag, BIASFX_REVERB_TOGGLE_CC)
        sendCCMessage(channel, BIASFX_REVERB_TOGGLE_CC, 127)
    else:
        _debugEffectDecision("Reverb", "SKIP", idx, channel, samePCFlag, oldReverb, reverbFlag, rawReverbFlag, BIASFX_REVERB_TOGGLE_CC)

    rawModeFlag = songPreset.get('modeflag', 0)
    modeFlag = _toEffectFlag(rawModeFlag)
    if modeFlag != oldMod:
        _debugEffectDecision("Mod", "SEND", idx, channel, samePCFlag, oldMod, modeFlag, rawModeFlag, BIASFX_MOD_TOGGLE_CC)
        sendCCMessage(channel, BIASFX_MOD_TOGGLE_CC, 127)
    else:
        _debugEffectDecision("Mod", "SKIP", idx, channel, samePCFlag, oldMod, modeFlag, rawModeFlag, BIASFX_MOD_TOGGLE_CC)

    if idx == 0:
        _debug(
            f">>>  idx = {idx},  samepc = {samePCFlag}, delay {oldDelay} >> {delayFlag} , reverb {oldReverb} >> {reverbFlag} ,  mod {oldMod} >> {modeFlag} ,  channel = {channel}")

    gCurrentDelayList[idx] = delayFlag
    gCurrentReverbList[idx] = reverbFlag
    gCurrentModList[idx] = modeFlag
    updateEffectDisplayStatus()


def processProgramBoost(samePCFlag, idx, channel, songPreset):
    if not _isBiasFXEffectTarget(channel, idx):
        return

    oldBoost = int(gCurrentBoostList[idx]) if samePCFlag else 0
    rawBoostFlag = songPreset.get('boostflag', 0)
    boostFlag = _toEffectFlag(rawBoostFlag)
    if boostFlag != oldBoost:
        _debugEffectDecision("Boost", "SEND", idx, channel, samePCFlag, oldBoost, boostFlag, rawBoostFlag, BIASFX_BOOST_TOGGLE_CC)
        sendCCMessage(channel, BIASFX_BOOST_TOGGLE_CC, 127)
    else:
        _debugEffectDecision("Boost", "SKIP", idx, channel, samePCFlag, oldBoost, boostFlag, rawBoostFlag, BIASFX_BOOST_TOGGLE_CC)

    gCurrentBoostList[idx] = boostFlag
    updateEffectDisplayStatus()


def toggleLiveDelayEffect():
    toggleLiveEffect(EFFECT_DELAY)


def toggleLiveReverbEffect():
    toggleLiveEffect(EFFECT_REVERB)


def toggleLiveModEffect():
    toggleLiveEffect(EFFECT_MOD)


def toggleLiveBoostEffect():
    toggleLiveEffect(EFFECT_BOOST)


def toggleLiveEffect(effectName):
    effectList, effectCC = getEffectStateAndCC(effectName)
    _masterChannel, masterIdx = BIASFX_EFFECT_TARGETS[0]
    targetState = 0 if int(effectList[masterIdx]) > 0 else 1

    for channel, idx in BIASFX_EFFECT_TARGETS:
        if int(effectList[idx]) != targetState:
            sendCCMessage(channel, effectCC, 127)
            effectList[idx] = targetState

    updateEffectDisplayStatus()
    if gDisplayData:
        gDisplayData.drawScreen()


def getEffectStateAndCC(effectName):
    if effectName == EFFECT_DELAY:
        return gCurrentDelayList, BIASFX_DELAY_TOGGLE_CC
    if effectName == EFFECT_REVERB:
        return gCurrentReverbList, BIASFX_REVERB_TOGGLE_CC
    if effectName == EFFECT_MOD:
        return gCurrentModList, BIASFX_MOD_TOGGLE_CC
    if effectName == EFFECT_BOOST:
        return gCurrentBoostList, BIASFX_BOOST_TOGGLE_CC
    raise ValueError(f"Unknown live effect {effectName}")


def updateEffectDisplayStatus():
    if not gDisplayData or not hasattr(gDisplayData, "setEffectStatus"):
        return

    _masterChannel, masterIdx = BIASFX_EFFECT_TARGETS[0]
    delayStatus = int(gCurrentDelayList[masterIdx] > 0)
    reverbStatus = int(gCurrentReverbList[masterIdx] > 0)
    modStatus = int(gCurrentModList[masterIdx] > 0)
    boostStatus = int(gCurrentBoostList[masterIdx] > 0)
    gDisplayData.setEffectStatus(delayStatus, reverbStatus, modStatus, boostStatus)


def _isBiasFXEffectTarget(channel, idx):
    return (channel, idx) in BIASFX_EFFECT_TARGETS


def _toEffectFlag(value):
    if isinstance(value, bool):
        return 1 if value else 0
    if value is None:
        return 0
    if isinstance(value, (int, float)):
        return 1 if int(value) != 0 else 0

    normalized = str(value).strip().lower()
    if normalized in ("1", "true", "yes", "on", "checked"):
        return 1
    if normalized in ("", "0", "false", "no", "off", "unchecked"):
        return 0

    _debug(f">>> Unknown effect flag value {value!r}; treating as OFF")
    return 0


def _extractGigId(payload):
    if isinstance(payload, dict):
        payload = payload.get("gigId", payload.get("id", -1))

    try:
        return int(payload)
    except (TypeError, ValueError):
        return -1


def _isGigSelectionMessage(payload):
    if not isinstance(payload, dict):
        return False

    action = payload.get("action")
    return action == "select" or payload.get("selectGig") is True


def _debugEffectDecision(effectName, action, idx, channel, samePCFlag, oldFlag, newFlag, rawFlag, cc):
    _debug(
        f">>> {effectName} {action}: idx={idx}, channel={channel}, samepc={samePCFlag}, "
        f"old={oldFlag}, new={newFlag}, raw={rawFlag!r}, cc={cc}")


def _resetSystemCommandCounter():
    if gResetSystemCommandCounter:
        gResetSystemCommandCounter()


def _showGigName(gig):
    if not gDisplayData:
        return

    name = gig.get("name", "") if gig else ""
    if hasattr(gDisplayData, "showGigName"):
        gDisplayData.showGigName(name, 5)
    else:
        gDisplayData.drawMessage("Gig", name)


def _showSongName(song):
    if not gDisplayData:
        return

    name = song.get("name", "") if song else ""
    if hasattr(gDisplayData, "showSongName"):
        gDisplayData.showSongName(name, 2)
    else:
        gDisplayData.drawMessage("Song", name)


def _debug(message):
    if gPrintDebug:
        gPrintDebug(message)
