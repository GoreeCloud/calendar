package com.goreecloud.calendar

enum class CalendarCapabilityState {
    NOT_IMPLEMENTED,
    UNAVAILABLE,
    AVAILABLE,
}

data class CalendarCapability(
    val state: CalendarCapabilityState,
    val explanation: String,
)

data class CalendarCapabilitySnapshot(
    val identitySession: CalendarCapability,
    val calDavRead: CalendarCapability,
    val calDavWrite: CalendarCapability,
    val offlineCache: CalendarCapability,
    val backgroundSync: CalendarCapability,
    val androidCalendarBridge: CalendarCapability,
) {
    companion object {
        fun developmentShell(): CalendarCapabilitySnapshot {
            val pending = CalendarCapability(
                state = CalendarCapabilityState.NOT_IMPLEMENTED,
                explanation = "Not connected in the native Android Development shell",
            )
            return CalendarCapabilitySnapshot(
                identitySession = pending,
                calDavRead = pending,
                calDavWrite = pending,
                offlineCache = pending,
                backgroundSync = pending,
                androidCalendarBridge = pending,
            )
        }
    }
}
