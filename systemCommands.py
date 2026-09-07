import subprocess
from time import monotonic

SYSTEM_COMMAND_CONFIRM_SECONDS = 5


gDisplayData = None
gPrintDebug = None
gSystemCommandCounter = 0
gSystemCommandCode = -1
gSystemCommandArmedAt = 0


def init(displayData, printDebug):
    global gDisplayData
    global gPrintDebug

    gDisplayData = displayData
    gPrintDebug = printDebug


def resetSystemCommandCounter():
    global gSystemCommandCounter
    global gSystemCommandArmedAt
    gSystemCommandCounter = 0
    gSystemCommandArmedAt = 0


def executeSystemCommand(code):
    global gSystemCommandCounter
    global gSystemCommandCode
    global gSystemCommandArmedAt

    _debug("EXECUTE SYSTEM COMMAND")
    command = ""
    displayText = ""

    # Safety confirmation: first matching MIDI message arms the command,
    # second consecutive matching message executes it.
    if gSystemCommandCounter > 0 and (
            gSystemCommandCode != code or
            monotonic() - gSystemCommandArmedAt > SYSTEM_COMMAND_CONFIRM_SECONDS):
        resetSystemCommandCounter()

    if code == 1:
        displayText = 'SHUTDOWN'
        if gSystemCommandCounter > 0:
            gDisplayData.drawShutdown()
        command = "/usr/bin/sudo -n /usr/bin/systemctl poweroff"
    elif code == 2:
        displayText = 'REBOOT'
        if gSystemCommandCounter > 0:
            gDisplayData.drawReboot()
        command = "/usr/bin/sudo -n /usr/bin/systemctl reboot"
    elif code == 3:
        displayText = 'RESTART FCB1010'
        if gSystemCommandCounter > 0:
            gDisplayData.drawReboot()
        command = "/usr/bin/sudo -n /usr/bin/systemctl restart fcb1010.service"
    else:
        _debug("ExecuteSystemCommand. Unknown command")
        return False

    if gSystemCommandCounter > 0:
        if command != "":
            _debug("Code =%d, Command=%s" % (code, command))
            process = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
            output = process.communicate()[0]
            _debug(output)
        return True

    gDisplayData.drawSysCommand(displayText)
    _debug(displayText)
    gSystemCommandCounter = gSystemCommandCounter + 1
    gSystemCommandCode = code
    gSystemCommandArmedAt = monotonic()
    return False


def _debug(message):
    if gPrintDebug:
        gPrintDebug(message)
