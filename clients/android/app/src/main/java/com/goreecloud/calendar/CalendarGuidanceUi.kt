package com.goreecloud.calendar

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp

internal const val CALENDAR_AUTHORITY_HINT_ID = "calendar-authority-boundary"

@Composable
internal fun CalendarFirstUseWizard(
    state: CalendarGuidanceState,
    onPrevious: () -> Unit,
    onNext: () -> Unit,
    onHintsEnabledChanged: (Boolean) -> Unit,
    onComplete: () -> Unit,
) {
    val step = state.setupStep
    Surface(
        modifier = Modifier.fillMaxSize(),
        color = MaterialTheme.colorScheme.background,
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .statusBarsPadding()
                .navigationBarsPadding()
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 24.dp, vertical = 28.dp),
            verticalArrangement = Arrangement.spacedBy(18.dp),
        ) {
            Text(
                "GoreeCloud Calendar",
                style = MaterialTheme.typography.labelLarge,
                color = MaterialTheme.colorScheme.primary,
            )
            Text(
                "Step " + (step + 1) + " of " + (CalendarGuidanceState.LAST_SETUP_STEP + 1),
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Surface(
                modifier = Modifier.fillMaxWidth(),
                shape = MaterialTheme.shapes.large,
                tonalElevation = 2.dp,
            ) {
                Column(
                    modifier = Modifier.padding(24.dp),
                    verticalArrangement = Arrangement.spacedBy(14.dp),
                ) {
                    when (step) {
                        0 -> {
                            Text(
                                "A calendar client built around authoritative sync",
                                style = MaterialTheme.typography.headlineMedium,
                                fontWeight = FontWeight.Bold,
                            )
                            Text(
                                "GoreeCloud Calendar is the native client surface. Radicale/CalDAV remains the authoritative calendar service, and local state may only become a bounded offline representation.",
                                style = MaterialTheme.typography.bodyLarge,
                            )
                            Text(
                                "This Development build currently presents capability state and validated source contracts; it does not yet hold network, Calendar Provider, or production Identity authority.",
                                style = MaterialTheme.typography.bodyMedium,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                            )
                        }

                        1 -> {
                            Text(
                                "Identity, network, and device access stay explicit",
                                style = MaterialTheme.typography.headlineMedium,
                                fontWeight = FontWeight.Bold,
                            )
                            Text(
                                "Future sign-in, CalDAV transport, event mutation, offline sync, and Android Calendar Provider access must each be enabled only after their own governed capability and consent paths are connected.",
                                style = MaterialTheme.typography.bodyLarge,
                            )
                            Text(
                                "The client must show unavailable, blocked, offline, stale, or conflict states truthfully instead of implying that a source-ready contract is live service authority.",
                                style = MaterialTheme.typography.bodyMedium,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                            )
                        }

                        else -> {
                            Text(
                                "Choose contextual guidance",
                                style = MaterialTheme.typography.headlineMedium,
                                fontWeight = FontWeight.Bold,
                            )
                            Text(
                                "Contextual tips can explain capability and authority boundaries while Calendar evolves. You can disable all ordinary tips, turn them back on, reset dismissed tips, or replay this setup later.",
                                style = MaterialTheme.typography.bodyLarge,
                            )
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.spacedBy(12.dp),
                            ) {
                                Column(
                                    modifier = Modifier.weight(1f),
                                    verticalArrangement = Arrangement.spacedBy(2.dp),
                                ) {
                                    Text(
                                        "Contextual tips",
                                        style = MaterialTheme.typography.titleMedium,
                                        fontWeight = FontWeight.SemiBold,
                                    )
                                    Text(
                                        if (state.hintsEnabled) "On" else "Off",
                                        style = MaterialTheme.typography.bodySmall,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                                    )
                                }
                                Switch(
                                    checked = state.hintsEnabled,
                                    onCheckedChange = onHintsEnabledChanged,
                                )
                            }
                        }
                    }
                }
            }
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                TextButton(
                    onClick = onPrevious,
                    enabled = step > 0,
                ) {
                    Text("Back")
                }
                Spacer(Modifier.weight(1f))
                Button(
                    onClick = if (step == CalendarGuidanceState.LAST_SETUP_STEP) onComplete else onNext,
                ) {
                    Text(if (step == CalendarGuidanceState.LAST_SETUP_STEP) "Finish setup" else "Continue")
                }
            }
        }
    }
}

@Composable
internal fun CalendarAuthorityHint(onDismiss: () -> Unit) {
    Surface(
        modifier = Modifier.fillMaxWidth(),
        shape = MaterialTheme.shapes.medium,
        color = MaterialTheme.colorScheme.secondaryContainer,
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Text(
                "Authority tip",
                style = MaterialTheme.typography.titleSmall,
                fontWeight = FontWeight.SemiBold,
                color = MaterialTheme.colorScheme.onSecondaryContainer,
            )
            Text(
                "The capability card reports what this exact client revision has actually accepted. Source-ready contracts are not the same as a live Identity session, network transport, CalDAV authorization, or Android Calendar Provider permission.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSecondaryContainer,
            )
            TextButton(onClick = onDismiss) {
                Text("Dismiss")
            }
        }
    }
}

@Composable
internal fun CalendarGuidanceControls(
    state: CalendarGuidanceState,
    onHintsEnabledChanged: (Boolean) -> Unit,
    onResetDismissedHints: () -> Unit,
    onReplaySetup: () -> Unit,
) {
    Column(
        modifier = Modifier.fillMaxWidth(),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        HorizontalDivider()
        Text("Guidance & setup", style = MaterialTheme.typography.titleSmall)
        Text(
            "Guidance preferences never grant Identity, network, CalDAV, synchronization, mutation, or Android Calendar Provider authority.",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Column(
                modifier = Modifier.weight(1f),
                verticalArrangement = Arrangement.spacedBy(2.dp),
            ) {
                Text(
                    "Contextual tips",
                    style = MaterialTheme.typography.bodyLarge,
                    fontWeight = FontWeight.SemiBold,
                )
                Text(
                    if (state.hintsEnabled) "Enabled" else "Disabled",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            Switch(
                checked = state.hintsEnabled,
                onCheckedChange = onHintsEnabledChanged,
            )
        }
        TextButton(onClick = onResetDismissedHints) {
            Text("Reset dismissed tips")
        }
        TextButton(onClick = onReplaySetup) {
            Text("Replay startup guide")
        }
    }
}
