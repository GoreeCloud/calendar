package com.goreecloud.calendar

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class CalendarCapabilitySnapshotTest {
    @Test
    fun developmentShellDoesNotClaimRuntimeCapabilities() {
        val snapshot = CalendarCapabilitySnapshot.developmentShell()
        val capabilities = listOf(
            snapshot.identitySession,
            snapshot.calDavRead,
            snapshot.calDavWrite,
            snapshot.offlineCache,
            snapshot.backgroundSync,
            snapshot.androidCalendarBridge,
        )

        assertEquals(6, capabilities.size)
        assertTrue(capabilities.all { it.state == CalendarCapabilityState.NOT_IMPLEMENTED })
        assertTrue(capabilities.none { it.state == CalendarCapabilityState.AVAILABLE })
    }

    @Test
    fun unavailableCapabilitiesExplainTheirState() {
        val snapshot = CalendarCapabilitySnapshot.developmentShell()

        assertTrue(snapshot.calDavRead.explanation.isNotBlank())
        assertTrue(snapshot.androidCalendarBridge.explanation.isNotBlank())
    }
}
