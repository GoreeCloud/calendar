package com.goreecloud.calendar

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
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
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            GlazeCalendarTheme {
                CalendarRoot(CalendarCapabilitySnapshot.developmentShell())
            }
        }
    }
}

@Composable
private fun CalendarRoot(capabilities: CalendarCapabilitySnapshot) {
    val applicationContext = LocalContext.current.applicationContext
    val repository = remember(applicationContext) {
        CalendarGuidanceRepository(SharedPreferencesCalendarGuidanceStore(applicationContext))
    }
    var guidanceState by remember(repository) { mutableStateOf(repository.load()) }

    if (!guidanceState.setupCompleted) {
        CalendarFirstUseWizard(
            state = guidanceState,
            onPrevious = {
                guidanceState = repository.previousSetupStep(guidanceState)
            },
            onNext = {
                guidanceState = repository.nextSetupStep(guidanceState)
            },
            onHintsEnabledChanged = { enabled ->
                guidanceState = repository.setHintsEnabled(guidanceState, enabled)
            },
            onComplete = {
                guidanceState = repository.completeSetup(guidanceState)
            },
        )
    } else {
        CalendarDevelopmentShell(
            capabilities = capabilities,
            guidanceState = guidanceState,
            onDismissGuidanceHint = {
                guidanceState = repository.dismissHint(
                    guidanceState,
                    CALENDAR_AUTHORITY_HINT_ID,
                )
            },
            onHintsEnabledChanged = { enabled ->
                guidanceState = repository.setHintsEnabled(guidanceState, enabled)
            },
            onResetDismissedHints = {
                guidanceState = repository.resetDismissedHints(guidanceState)
            },
            onReplaySetup = {
                guidanceState = repository.replaySetup(guidanceState)
            },
        )
    }
}

@Composable
private fun CalendarDevelopmentShell(
    capabilities: CalendarCapabilitySnapshot,
    guidanceState: CalendarGuidanceState,
    onDismissGuidanceHint: () -> Unit,
    onHintsEnabledChanged: (Boolean) -> Unit,
    onResetDismissedHints: () -> Unit,
    onReplaySetup: () -> Unit,
) {
    val acceptedCount = listOf(
        capabilities.identitySession,
        capabilities.calDavRead,
        capabilities.calDavWrite,
        capabilities.offlineCache,
        capabilities.backgroundSync,
        capabilities.androidCalendarBridge,
    ).count { it.state == CalendarCapabilityState.AVAILABLE }

    Surface(modifier = Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .statusBarsPadding()
                .navigationBarsPadding()
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 20.dp, vertical = 16.dp),
        ) {
            Text(
                text = "GoreeCloud Calendar",
                style = MaterialTheme.typography.headlineMedium,
                fontWeight = FontWeight.Bold,
            )
            Spacer(Modifier.height(6.dp))
            Text(
                text = "Native Android Development client",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Text(
                text = "GLAZE UI ${GlazeCalendarContract.VERSION} · ${GlazeCalendarContract.ADOPTION_STATE.replace('_', ' ')}",
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )

            Spacer(Modifier.height(18.dp))
            if (guidanceState.isHintVisible(CALENDAR_AUTHORITY_HINT_ID)) {
                CalendarAuthorityHint(onDismiss = onDismissGuidanceHint)
                Spacer(Modifier.height(18.dp))
            }

            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(20.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Text(
                            text = "Runtime capability status",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.SemiBold,
                        )
                        Text(
                            text = "$acceptedCount/6 accepted",
                            style = MaterialTheme.typography.labelLarge,
                        )
                    }
                    Spacer(Modifier.height(8.dp))
                    Text(
                        text = "Identity, CalDAV read/write, offline cache, background sync, and the Android Calendar Provider bridge remain fail-closed in this shell.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }

            Spacer(Modifier.height(18.dp))
            Text(
                text = "No calendars loaded",
                style = MaterialTheme.typography.titleLarge,
                fontWeight = FontWeight.SemiBold,
            )
            Spacer(Modifier.height(6.dp))
            Text(
                text = "Radicale/CalDAV remains the authoritative calendar service. This Development shell intentionally requests no network or Calendar Provider permissions until synchronization and identity boundaries are implemented and independently accepted.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )

            Spacer(Modifier.height(22.dp))
            CalendarGuidanceControls(
                state = guidanceState,
                onHintsEnabledChanged = onHintsEnabledChanged,
                onResetDismissedHints = onResetDismissedHints,
                onReplaySetup = onReplaySetup,
            )
        }
    }
}
