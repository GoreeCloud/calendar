package com.goreecloud.calendar

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class CalendarGuidanceRepositoryTest {
    @Test
    fun firstUseStartsIncompleteWithHintsEnabled() {
        val state = CalendarGuidanceRepository(FakeStore()).load()
        assertFalse(state.setupCompleted)
        assertEquals(0, state.setupStep)
        assertTrue(state.hintsEnabled)
    }

    @Test
    fun setupProgressResumesAndCompletionPersists() {
        val store = FakeStore()
        val first = CalendarGuidanceRepository(store)
        val stepOne = first.nextSetupStep(first.load())
        assertEquals(1, stepOne.setupStep)

        val recreated = CalendarGuidanceRepository(store)
        val resumed = recreated.load()
        assertEquals(1, resumed.setupStep)
        assertFalse(resumed.setupCompleted)

        val completed = recreated.completeSetup(resumed)
        assertTrue(completed.setupCompleted)
        assertTrue(CalendarGuidanceRepository(store).load().setupCompleted)
    }

    @Test
    fun hintsCanBeDismissedDisabledResetAndReenabled() {
        val repository = CalendarGuidanceRepository(FakeStore())
        var state = repository.load()

        state = repository.dismissHint(state, "authority")
        assertFalse(state.isHintVisible("authority"))

        state = repository.resetDismissedHints(state)
        assertTrue(state.isHintVisible("authority"))

        state = repository.setHintsEnabled(state, false)
        assertFalse(state.isHintVisible("authority"))

        state = repository.setHintsEnabled(state, true)
        assertTrue(state.isHintVisible("authority"))
    }

    @Test
    fun replayDoesNotOverrideGlobalHintPreference() {
        val repository = CalendarGuidanceRepository(FakeStore())
        var state = repository.load()
        state = repository.setHintsEnabled(state, false)
        state = repository.completeSetup(state)

        val replay = repository.replaySetup(state)

        assertFalse(replay.setupCompleted)
        assertEquals(0, replay.setupStep)
        assertFalse(replay.hintsEnabled)
    }

    @Test
    fun failedWriteDoesNotAdvancePresentedState() {
        val store = FakeStore(acceptWrites = false)
        val repository = CalendarGuidanceRepository(store)
        val initial = repository.load()

        assertEquals(initial, repository.nextSetupStep(initial))
        assertEquals(null, store.stored)
    }

    private class FakeStore(
        var stored: CalendarGuidanceState? = null,
        var acceptWrites: Boolean = true,
    ) : CalendarGuidanceStore {
        override fun read(): CalendarGuidanceState? = stored

        override fun write(state: CalendarGuidanceState): Boolean {
            if (!acceptWrites) return false
            stored = state
            return true
        }
    }
}
