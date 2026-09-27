package com.goreecloud.calendar

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Test

class GlazeCalendarContractTest {
    @Test
    fun currentStableGlazeReferenceIsPinned() {
        assertEquals("1.6.0", GlazeCalendarContract.VERSION)
        assertEquals(
            "a7180679ea851389e0f3004515f9a25f420e716d",
            GlazeCalendarContract.REFERENCE_REVISION,
        )
        assertEquals("1.5.1", GlazeCalendarContract.ROLLBACK_VERSION)
        assertEquals("ADOPTION_IN_PROGRESS", GlazeCalendarContract.ADOPTION_STATE)
    }

    @Test
    fun sharedStableQualificationDoesNotCreateCalendarAcceptance() {
        assertFalse(GlazeCalendarContract.OPTICAL_ENGINE_ACCEPTED)
        assertFalse(GlazeCalendarContract.REDUCED_TRANSPARENCY_ACCEPTED)
        assertFalse(GlazeCalendarContract.INCREASED_CONTRAST_ACCEPTED)
        assertFalse(GlazeCalendarContract.PHYSICAL_DEVICE_ACCEPTED)
        assertFalse(GlazeCalendarContract.HUMAN_VISUAL_ACCEPTED)
    }
}
