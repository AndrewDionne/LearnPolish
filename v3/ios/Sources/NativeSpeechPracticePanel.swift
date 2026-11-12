import SwiftUI

/// Pronunciation review is a core part of both native Speak flows. A finished
/// microphone take is automatically evaluated on the iPhone, with no account,
/// private service, provider permissions or cloud audio upload.
struct NativeSpeechPracticePanel: View {
    let item: LessonItem
    @ObservedObject var audio: NativeAudio
    @Binding var feedback: NativeSpeechFeedback?
    @EnvironmentObject private var reviewer: NativeOnDevicePronunciation

    @State private var busy = false
    @State private var attemptedGeneration: UUID?
    @State private var message: String?
    @State private var request: Task<Void, Never>?

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            if audio.hasRecording && !audio.isRecording {
                if busy {
                    ProgressView("Reviewing your Polish pronunciation…")
                    Text("The first review installs a Polish model on this iPhone if needed. After the initial download, analysis runs offline.")
                        .font(.caption).foregroundStyle(.secondary)
                } else if let message {
                    Text(message).font(.footnote).foregroundStyle(.secondary)
                    Button("Try pronunciation review again") { reviewRecording() }
                        .buttonStyle(.bordered)
                        .disabled(!audio.usableRecording)
                } else if let feedback {
                    switch feedback {
                    case .onDeviceRecognition:
                        Text("Colour indicates how the original word matched local Polish speech recognition. The overall /100 is a recognition estimate, not calibrated syllable sound accuracy.")
                            .font(.caption).foregroundStyle(.secondary)
                    case .inconclusive(let reason):
                        Text(reason).font(.footnote).foregroundStyle(.secondary)
                        Button("Try review again") { reviewRecording() }
                            .buttonStyle(.bordered)
                    case .blend:
                        EmptyView()
                    }
                }
            }
        }
        .onAppear {
            if audio.usableRecording { reviewRecording() }
        }
        .onChange(of: audio.usableRecording) { _, ready in
            if ready { reviewRecording() }
        }
        .onChange(of: audio.takeGeneration) { _, _ in
            clear()
            if audio.usableRecording { reviewRecording() }
        }
        .onDisappear { clear() }
    }

    private func reviewRecording() {
        guard !busy, audio.usableRecording,
              let file = audio.recordingURL else { return }
        let generation = audio.takeGeneration
        guard attemptedGeneration != generation || message != nil ||
              feedback != nil else { return }
        attemptedGeneration = generation
        busy = true
        feedback = nil
        message = nil
        request = Task { @MainActor in
            do {
                let result = try await reviewer.assess(item: item, recording: file)
                guard !Task.isCancelled, audio.takeGeneration == generation else { return }
                feedback = result
            } catch {
                guard !Task.isCancelled, audio.takeGeneration == generation else { return }
                message = (error as? LocalizedError)?.errorDescription ??
                    "Polish recognition was unavailable for this take."
            }
            if audio.takeGeneration == generation {
                busy = false
                request = nil
            }
        }
    }

    private func clear() {
        request?.cancel()
        request = nil
        busy = false
        attemptedGeneration = nil
        feedback = nil
        message = nil
    }
}
