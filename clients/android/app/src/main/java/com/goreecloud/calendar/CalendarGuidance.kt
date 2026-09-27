package com.goreecloud.calendar

import android.content.Context

data class CalendarGuidanceState(
    val setupCompleted: Boolean = false,
    val setupStep: Int = 0,
    val hintsEnabled: Boolean = true,
    val dismissedHintIds: Set<String> = emptySet(),
) {
    init {
        require(setupStep in 0..LAST_SETUP_STEP) {
            "setupStep must be between 0 and $LAST_SETUP_STEP"
        }
    }

    fun isHintVisible(hintId: String): Boolean =
        hintsEnabled && hintId !in dismissedHintIds

    companion object {
        const val LAST_SETUP_STEP = 2
    }
}

interface CalendarGuidanceStore {
    fun read(): CalendarGuidanceState?
    fun write(state: CalendarGuidanceState): Boolean
}

class CalendarGuidanceRepository(
    private val store: CalendarGuidanceStore,
) {
    fun load(): CalendarGuidanceState =
        store.read() ?: CalendarGuidanceState()

    fun nextSetupStep(current: CalendarGuidanceState): CalendarGuidanceState {
        if (current.setupCompleted) return current
        return persist(
            current,
            current.copy(
                setupStep = (current.setupStep + 1).coerceAtMost(CalendarGuidanceState.LAST_SETUP_STEP),
            ),
        )
    }

    fun previousSetupStep(current: CalendarGuidanceState): CalendarGuidanceState {
        if (current.setupCompleted) return current
        return persist(
            current,
            current.copy(setupStep = (current.setupStep - 1).coerceAtLeast(0)),
        )
    }

    fun completeSetup(current: CalendarGuidanceState): CalendarGuidanceState =
        persist(
            current,
            current.copy(
                setupCompleted = true,
                setupStep = CalendarGuidanceState.LAST_SETUP_STEP,
            ),
        )

    fun replaySetup(current: CalendarGuidanceState): CalendarGuidanceState =
        persist(
            current,
            current.copy(
                setupCompleted = false,
                setupStep = 0,
            ),
        )

    fun setHintsEnabled(
        current: CalendarGuidanceState,
        enabled: Boolean,
    ): CalendarGuidanceState =
        persist(current, current.copy(hintsEnabled = enabled))

    fun dismissHint(
        current: CalendarGuidanceState,
        hintId: String,
    ): CalendarGuidanceState {
        if (hintId.isBlank()) return current
        return persist(
            current,
            current.copy(dismissedHintIds = current.dismissedHintIds + hintId),
        )
    }

    fun resetDismissedHints(current: CalendarGuidanceState): CalendarGuidanceState =
        persist(current, current.copy(dismissedHintIds = emptySet()))

    private fun persist(
        current: CalendarGuidanceState,
        next: CalendarGuidanceState,
    ): CalendarGuidanceState =
        if (store.write(next)) next else current
}

class SharedPreferencesCalendarGuidanceStore(
    context: Context,
) : CalendarGuidanceStore {
    private val preferences = context.applicationContext.getSharedPreferences(
        PREFERENCES_NAME,
        Context.MODE_PRIVATE,
    )

    override fun read(): CalendarGuidanceState? {
        if (!preferences.contains(KEY_SCHEMA_VERSION)) return null

        if (preferences.getInt(KEY_SCHEMA_VERSION, -1) != SCHEMA_VERSION) {
            // Unknown state must not silently complete onboarding or restore hint preferences.
            return CalendarGuidanceState(
                setupCompleted = false,
                setupStep = 0,
                hintsEnabled = false,
            )
        }

        return CalendarGuidanceState(
            setupCompleted = preferences.getBoolean(KEY_SETUP_COMPLETED, false),
            setupStep = preferences.getInt(KEY_SETUP_STEP, 0)
                .coerceIn(0, CalendarGuidanceState.LAST_SETUP_STEP),
            hintsEnabled = preferences.getBoolean(KEY_HINTS_ENABLED, true),
            dismissedHintIds = preferences.getStringSet(KEY_DISMISSED_HINT_IDS, emptySet())
                ?.toSet()
                .orEmpty(),
        )
    }

    override fun write(state: CalendarGuidanceState): Boolean =
        preferences.edit()
            .putInt(KEY_SCHEMA_VERSION, SCHEMA_VERSION)
            .putBoolean(KEY_SETUP_COMPLETED, state.setupCompleted)
            .putInt(KEY_SETUP_STEP, state.setupStep)
            .putBoolean(KEY_HINTS_ENABLED, state.hintsEnabled)
            .putStringSet(KEY_DISMISSED_HINT_IDS, state.dismissedHintIds.toSet())
            .commit()

    private companion object {
        const val PREFERENCES_NAME = "goreecloud_calendar_guidance"
        const val SCHEMA_VERSION = 1
        const val KEY_SCHEMA_VERSION = "schema_version"
        const val KEY_SETUP_COMPLETED = "setup_completed"
        const val KEY_SETUP_STEP = "setup_step"
        const val KEY_HINTS_ENABLED = "hints_enabled"
        const val KEY_DISMISSED_HINT_IDS = "dismissed_hint_ids"
    }
}
