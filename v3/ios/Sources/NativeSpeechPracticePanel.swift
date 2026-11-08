import SwiftUI

/// Added to BOTH native Speak entry points. No service or check button is
/// shown without an optional connected, verified server session.
/// Consent is per take, initially OFF, and reset on re-recording/navigation.
struct NativeSpeechPracticePanel: View {
    let item: LessonItem
    @ObservedObject var audio: NativeAudio
    @Binding var feedback: NativeSpeechFeedback?
    @EnvironmentObject private var speech: NativeSpeechSession

    @State private var allowAzure = false
    @State private var allowGroq = false
    @State private var busy = false
    @State private var submittedGeneration: UUID?
    @State private var message: String?
    @State private var request: Task<Void, Never>?

    var body: some View {
        Group {
            if speech.isConnected && audio.usableRecording && !audio.isRecording {
                VStack(alignment: .leading, spacing: 12) {
                    Toggle("Send this take to Azure Speech", isOn: $allowAzure)
                    Toggle("Send this take to Groq Whisper", isOn: $allowGroq)
                    Text("Only this recording is sent, after you approve both providers. No audio, transcript or score is saved to your account.")
                        .font(.footnote).foregroundStyle(.secondary)

                    if submittedGeneration == nil {
                        Button {
                            checkPronunciation()
                        } label: {
                            Label(busy ? "Checking pronunciation…" : "Check my pronunciation",
                                  systemImage: "waveform")
                        }
                        .buttonStyle(.bordered)
                        .disabled(!allowAzure || !allowGroq || busy)
                    } else if busy {
                        ProgressView("Checking pronunciation…")
                    }

                    if let feedback {
                        switch feedback {
                        case .blend(let score, _):
                            Text("\(score)/100")
                                .font(.title3.monospacedDigit())
                                .accessibilityLabel("Experimental pronunciation estimate \(score) out of 100")
                        case .inconclusive(let reason):
                            Text(reason)
                                .font(.footnote).foregroundStyle(.secondary)
                        }
                    }
                    if let message {
                        Text(message).font(.footnote).foregroundStyle(.secondary)
                    }
                }
                .onChange(of: audio.takeGeneration) { _, _ in
                    clearForNewTake()
                }
                .onDisappear { clearForNewTake() }
            }
        }
    }

    private func checkPronunciation() {
        guard !busy, submittedGeneration == nil, allowAzure && allowGroq,
              speech.isConnected, let url = audio.recordingURL else { return }
        let generation = audio.takeGeneration
        let azure = allowAzure
        let groq = allowGroq
        submittedGeneration = generation
        busy = true
        feedback = nil
        message = nil
        request = Task { @MainActor in
            do {
                // No serialized microphone buffer leaves the app until the
                // user pressed Check with both consents. Conversion is local.
                let wav = try await Task.detached(priority: .userInitiated) {
                    try PronunciationWave.make(fromRecording: url)
                }.value
                guard !Task.isCancelled && audio.takeGeneration == generation else { return }
                let result = try await speech.assess(item: item, wav: wav,
                                                     approveAzure: azure,
                                                     approveGroq: groq)
                guard !Task.isCancelled && audio.takeGeneration == generation else { return }
                feedback = result
            } catch {
                guard !Task.isCancelled && audio.takeGeneration == generation else { return }
                message = (error as? LocalizedError)?.errorDescription ??
                    NativeSpeechError.unavailable.errorDescription
            }
            if audio.takeGeneration == generation {
                busy = false
                request = nil
            }
        }
    }

    private func clearForNewTake() {
        request?.cancel()
        request = nil
        busy = false
        allowAzure = false
        allowGroq = false
        submittedGeneration = nil
        feedback = nil
        message = nil
    }
}
