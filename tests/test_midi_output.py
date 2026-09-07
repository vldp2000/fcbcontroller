import sys
import unittest
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config
import midiOutput


class FakeMidiOutput:
    def __init__(self):
        self.messages = []

    def write_short(self, status, data1, data2=None):
        self.messages.append((status, data1, data2))


class MidiOutputTest(unittest.TestCase):
    def setUp(self):
        self.fakeOutput = FakeMidiOutput()
        self.debugMessages = []
        midiOutput.setMidiOutput(self.fakeOutput)
        midiOutput.setPrintDebug(self.debugMessages.append)
        midiOutput.setCurrentVolumeList([90, 80, 70, 60])
        midiOutput.gPendingVolumeReassertDict.clear()

    def tearDown(self):
        midiOutput.gPendingVolumeReassertDict.clear()
        midiOutput.setPrintDebug(None)

    def test_calibrate_pedal_volume_scales_to_midi_range(self):
        self.assertEqual(midiOutput.calibratePedalVolume(113, 0), 0)
        self.assertEqual(midiOutput.calibratePedalVolume(113, 4), 0)
        self.assertEqual(midiOutput.calibratePedalVolume(113, 113), 127)
        self.assertEqual(midiOutput.calibratePedalVolume(113, 200), 127)

    def test_normalize_pedal_volume_scales_by_program_maximum(self):
        self.assertEqual(midiOutput.normalizePedalVolume(100, 75), 59)
        self.assertEqual(midiOutput.normalizePedalVolume(80, 75), 47)
        self.assertEqual(midiOutput.normalizePedalVolume(100, 127), 100)
        self.assertEqual(midiOutput.normalizePedalVolume(80, 127), 80)
        self.assertEqual(midiOutput.normalizePedalVolume(200, 200), 127)
        self.assertEqual(midiOutput.normalizePedalVolume(-1, -1), 0)

    @patch.object(midiOutput, "sleep", return_value=None)
    def test_send_cc_message_writes_control_change_and_sleeps(self, sleepMock):
        midiOutput.sendCCMessage(config.DEV2_KEYBOARD_CHANNEL, 10, 64)

        self.assertEqual(
            self.fakeOutput.messages,
            [(0xB0 + config.DEV2_KEYBOARD_CHANNEL - 1, 10, 64)],
        )
        self.assertEqual(
            self.debugMessages,
            [f">>> MIDI OUT CC channel={config.DEV2_KEYBOARD_CHANNEL}, cc=10, value=64"],
        )
        sleepMock.assert_called_once_with(config.MIDI_CC_DELAY)

    @patch.object(midiOutput, "sleep", return_value=None)
    def test_send_pc_message_writes_program_change_and_sleeps(self, sleepMock):
        midiOutput.sendPCMessage(config.DEV1_GUITAR_CHANNEL, 12)

        self.assertEqual(
            self.fakeOutput.messages,
            [(0xC0 + config.DEV1_GUITAR_CHANNEL - 1, 12, None)],
        )
        self.assertEqual(
            self.debugMessages,
            [f">>> MIDI OUT PC channel={config.DEV1_GUITAR_CHANNEL}, pc=12"],
        )
        sleepMock.assert_called_once_with(config.MIDI_PC_DELAY)

    def test_send_generic_midi_command_writes_control_change_status(self):
        midiOutput.sendGenericMidiCommand(3, 99, 45)

        self.assertEqual(self.fakeOutput.messages, [(0xB0 + 3, 99, 45)])
        self.assertEqual(
            self.debugMessages,
            [">>> MIDI OUT GENERIC statusBase=3, data1=99, data2=45"],
        )

    def test_send_messages_are_safe_when_output_is_disconnected(self):
        midiOutput.setMidiOutput(None)

        self.assertFalse(midiOutput.sendCCMessage(1, 7, 64))
        self.assertFalse(midiOutput.sendPCMessage(1, 12))
        self.assertFalse(midiOutput.sendGenericMidiCommand(0, 7, 64))

    @patch.object(midiOutput, "sleep", return_value=None)
    def test_mute_channel_steps_down_to_zero(self, _sleep):
        midiOutput.muteChannel(config.DEV1_KEYBOARD_CHANNEL, 25, 10)

        self.assertEqual(
            self.fakeOutput.messages,
            [
                (0xB0 + config.DEV1_KEYBOARD_CHANNEL - 1, config.VOLUME_CC, 25),
                (0xB0 + config.DEV1_KEYBOARD_CHANNEL - 1, config.VOLUME_CC, 15),
                (0xB0 + config.DEV1_KEYBOARD_CHANNEL - 1, config.VOLUME_CC, 5),
                (0xB0 + config.DEV1_KEYBOARD_CHANNEL - 1, config.VOLUME_CC, 0),
            ],
        )

    @patch.object(midiOutput, "sleep", return_value=None)
    def test_mute_channel_does_nothing_for_zero_volume(self, _sleep):
        midiOutput.muteChannel(config.DEV1_KEYBOARD_CHANNEL, 0, 10)

        self.assertEqual(self.fakeOutput.messages, [])

    @patch.object(midiOutput, "sleep", return_value=None)
    def test_unmute_channel_steps_up_below_target_volume(self, _sleep):
        midiOutput.unmuteChannel(config.DEV1_KEYBOARD_CHANNEL, 25, 10)

        self.assertEqual(
            self.fakeOutput.messages,
            [
                (0xB0 + config.DEV1_KEYBOARD_CHANNEL - 1, config.VOLUME_CC, 10),
                (0xB0 + config.DEV1_KEYBOARD_CHANNEL - 1, config.VOLUME_CC, 20),
            ],
        )

    @patch.object(midiOutput, "sleep", return_value=None)
    def test_send_pedal_volume_uses_channel_status_and_volume_cc(self, _sleep):
        midiOutput.sendPedalVolumeCC(config.DEV1_GUITAR_CHANNEL, config.DEV1_GUITAR_VOLUME_IDX, 55)

        self.assertEqual(
            self.fakeOutput.messages,
            [(0xB0 + config.DEV1_GUITAR_CHANNEL - 1, config.VOLUME_CC, 38)],
        )
        self.assertEqual(
            self.debugMessages,
            [
                f">>> MIDI OUT EXPRESSION VOLUME channel={config.DEV1_GUITAR_CHANNEL}, "
                f"idx={config.DEV1_GUITAR_VOLUME_IDX}, cc={config.VOLUME_CC}, pedal=55, value=38, max=90"
            ],
        )

    @patch.object(midiOutput, "sleep", return_value=None)
    def test_send_pedal_volume_scales_full_range_below_current_preset_maximum(self, _sleep):
        midiOutput.sendPedalVolumeCC(config.DEV2_KEYBOARD_CHANNEL, config.DEV2_KEYBOARD_VOLUME_IDX, 61)

        self.assertEqual(
            self.fakeOutput.messages,
            [(0xB0 + config.DEV2_KEYBOARD_CHANNEL - 1, config.VOLUME_CC, 28)],
        )
        self.assertEqual(
            self.debugMessages,
            [
                f">>> MIDI OUT EXPRESSION VOLUME channel={config.DEV2_KEYBOARD_CHANNEL}, "
                f"idx={config.DEV2_KEYBOARD_VOLUME_IDX}, cc={config.VOLUME_CC}, pedal=61, value=28, max=60"
            ],
        )

    @patch.object(midiOutput, "sleep", return_value=None)
    def test_send_pedal_volume_cancels_pending_reassert_for_channel(self, _sleep):
        midiOutput.gPendingVolumeReassertDict[config.DEV2_GUITAR_CHANNEL] = {
            "volume": 80,
            "dueTime": 1.0,
        }

        midiOutput.sendPedalVolumeCC(config.DEV2_GUITAR_CHANNEL, config.DEV2_GUITAR_VOLUME_IDX, 40)

        self.assertNotIn(config.DEV2_GUITAR_CHANNEL, midiOutput.gPendingVolumeReassertDict)
        self.assertEqual(
            self.fakeOutput.messages,
            [(0xB0 + config.DEV2_GUITAR_CHANNEL - 1, config.VOLUME_CC, 22)],
        )
        self.assertEqual(
            self.debugMessages,
            [
                f">>> MIDI OUT CANCEL VOLUME REASSERT channel={config.DEV2_GUITAR_CHANNEL}",
                f">>> MIDI OUT EXPRESSION VOLUME channel={config.DEV2_GUITAR_CHANNEL}, "
                f"idx={config.DEV2_GUITAR_VOLUME_IDX}, cc={config.VOLUME_CC}, pedal=40, value=22, max=70",
            ],
        )

    @patch.object(midiOutput, "sleep", return_value=None)
    def test_send_pedal_volume_is_safe_when_output_is_disconnected(self, sleepMock):
        midiOutput.setMidiOutput(None)

        self.assertFalse(midiOutput.sendPedalVolumeCC(
            config.DEV1_GUITAR_CHANNEL,
            config.DEV1_GUITAR_VOLUME_IDX,
            75,
        ))

        sleepMock.assert_not_called()
        self.assertEqual(self.debugMessages, ["MIDI output is not connected"])

    def test_schedule_volume_reassert_keeps_latest_per_channel(self):
        with patch.object(midiOutput, "monotonic", return_value=10.0):
            midiOutput.scheduleVolumeReassert(config.DEV1_GUITAR_CHANNEL, 44)
            midiOutput.scheduleVolumeReassert(config.DEV1_GUITAR_CHANNEL, 88)

        self.assertEqual(
            midiOutput.gPendingVolumeReassertDict[config.DEV1_GUITAR_CHANNEL],
            {
                "volume": 88,
                "dueTime": 10.0 + config.MIDI_PRESET_VOLUME_REASSERT_DELAY,
            },
        )
        self.assertEqual(
            self.debugMessages,
            [
                f">>> MIDI OUT SCHEDULE VOLUME REASSERT channel={config.DEV1_GUITAR_CHANNEL}, "
                f"cc={config.VOLUME_CC}, value=44, delay={config.MIDI_PRESET_VOLUME_REASSERT_DELAY}",
                f">>> MIDI OUT SCHEDULE VOLUME REASSERT channel={config.DEV1_GUITAR_CHANNEL}, "
                f"cc={config.VOLUME_CC}, value=88, delay={config.MIDI_PRESET_VOLUME_REASSERT_DELAY}",
            ],
        )

    def test_schedule_volume_reassert_allows_multiple_channels(self):
        with patch.object(midiOutput, "monotonic", return_value=20.0):
            midiOutput.scheduleVolumeReassert(config.DEV1_GUITAR_CHANNEL, 44)
            midiOutput.scheduleVolumeReassert(config.DEV2_GUITAR_CHANNEL, 55)

        self.assertEqual(
            set(midiOutput.gPendingVolumeReassertDict.keys()),
            {config.DEV1_GUITAR_CHANNEL, config.DEV2_GUITAR_CHANNEL},
        )

    @patch.object(midiOutput, "MIDI_PRESET_VOLUME_REASSERT_ENABLED", False)
    def test_schedule_volume_reassert_respects_disabled_flag(self):
        midiOutput.scheduleVolumeReassert(config.DEV1_GUITAR_CHANNEL, 44)

        self.assertEqual(midiOutput.gPendingVolumeReassertDict, {})

    def test_cancel_pending_volume_reassert_removes_channel_only(self):
        midiOutput.gPendingVolumeReassertDict[config.DEV1_GUITAR_CHANNEL] = {
            "volume": 44,
            "dueTime": 9.0,
        }
        midiOutput.gPendingVolumeReassertDict[config.DEV2_GUITAR_CHANNEL] = {
            "volume": 55,
            "dueTime": 9.0,
        }

        midiOutput.cancelPendingVolumeReassert(config.DEV1_GUITAR_CHANNEL)

        self.assertNotIn(config.DEV1_GUITAR_CHANNEL, midiOutput.gPendingVolumeReassertDict)
        self.assertIn(config.DEV2_GUITAR_CHANNEL, midiOutput.gPendingVolumeReassertDict)

    @patch.object(midiOutput, "sleep", return_value=None)
    def test_process_pending_volume_reasserts_sends_due_messages_only(self, _sleep):
        midiOutput.gPendingVolumeReassertDict[config.DEV1_GUITAR_CHANNEL] = {
            "volume": 44,
            "dueTime": 9.0,
        }
        midiOutput.gPendingVolumeReassertDict[config.DEV2_GUITAR_CHANNEL] = {
            "volume": 55,
            "dueTime": 11.0,
        }

        with patch.object(midiOutput, "monotonic", return_value=10.0):
            midiOutput.processPendingVolumeReasserts()

        self.assertEqual(
            self.fakeOutput.messages,
            [(0xB0 + config.DEV1_GUITAR_CHANNEL - 1, config.VOLUME_CC, 44)],
        )
        self.assertEqual(
            self.debugMessages,
            [
                f">>> MIDI OUT REASSERT VOLUME channel={config.DEV1_GUITAR_CHANNEL}, cc={config.VOLUME_CC}, value=44",
                f">>> MIDI OUT CC channel={config.DEV1_GUITAR_CHANNEL}, cc={config.VOLUME_CC}, value=44",
            ],
        )
        self.assertNotIn(config.DEV1_GUITAR_CHANNEL, midiOutput.gPendingVolumeReassertDict)
        self.assertIn(config.DEV2_GUITAR_CHANNEL, midiOutput.gPendingVolumeReassertDict)


if __name__ == "__main__":
    unittest.main()
