import SwiftUI
import AVFoundation

enum AudioFiles {
    /// Generated folder is a blue Xcode folder reference. Reject malformed,
    /// absolute or remote paths; never fetch or synthesize missing audio.
    static func referenceURL(for path: String, bundle: Bundle = .main) -> URL? {
        guard path.hasPrefix("generated/audio/"), !path.contains(".."),
              let clean = path.removingPercentEncoding,
              !clean.split(separator: "/").contains(where: { $0 == ".." }) else {
            return nil
        }
        let relative = String(clean.dropFirst("generated/".count))
        let resource = bundle.bundleURL.appendingPathComponent("generated", isDirectory: true)
            .appendingPathComponent(relative)
        guard FileManager.default.fileExists(atPath: resource.path) else { return nil }
        return resource
    }
}

/// MainActor owns UI state only; blocking AVAudioSession and audio hardware
/// calls live exclusively in NativeAudioEngine's private serial queue.
@MainActor final class NativeAudio: ObservableObject {
    @Published private(set) var isRecording = false
    @Published private(set) var isStarting = false
    @Published private(set) var hasRecording = false
    @Published private(set) var usableRecording = false
    @Published private(set) var takeGeneration = UUID()
    @Published var message: String?

    var recordingURL: URL? {
        hasRecording && usableRecording && !isRecording && !isStarting ? takeURL : nil
    }

    private let engine = NativeAudioEngine()
    private var qualityTask: Task<Void, Never>?
    private var playbackGeneration = UUID()
    // Every screen owns its own private take: leaving one lesson cannot
    // silently delete or replay another lesson's microphone file.
    private let takeURL = FileManager.default.temporaryDirectory
        .appendingPathComponent("path-to-polish-\(UUID().uuidString).m4a")

    deinit {
        engine.discard(file: takeURL)
    }

    func playFile(_ path: String, rate: Float = 1) {
        guard let file = AudioFiles.referenceURL(for: path) else {
            message = "The original Polish recording is unavailable."
            return
        }
        play(file, rate: rate)
    }

    func playReference(_ item: LessonItem) {
        playReference(item, rate: 1)
    }

    func playReference(_ item: LessonItem, rate: Float) {
        guard let path = item.audio, let file = AudioFiles.referenceURL(for: path) else {
            message = "This lesson has no reference recording."
            return
        }
        play(file, rate: rate)
    }

    func playRecording() {
        guard hasRecording && !isRecording && !isStarting else { return }
        play(takeURL, rate: 1)
    }

    private func play(_ file: URL, rate: Float) {
        guard !isRecording && !isStarting else { return }
        playbackGeneration = UUID()
        let expected = playbackGeneration
        message = nil
        engine.play(file, rate: rate) { [weak self] success in
            guard let self, self.playbackGeneration == expected else { return }
            self.message = success ? nil :
                "Audio could not play. Check your output device and try again."
        }
    }

    func requestRecord() {
        guard !isRecording && !isStarting else { return }
        // Cancel old playback feedback and prevent a double-tap while iOS
        // presents the microphone permission dialog or prepares hardware.
        playbackGeneration = UUID()
        isStarting = true
        isRecording = false
        hasRecording = false
        usableRecording = false
        message = nil
        qualityTask?.cancel()
        qualityTask = nil
        takeGeneration = UUID()
        let expected = takeGeneration
        engine.discard(file: takeURL)

        AVAudioApplication.requestRecordPermission { [weak self] granted in
            Task { @MainActor [weak self] in
                guard let self, self.takeGeneration == expected else { return }
                guard granted else {
                    self.isStarting = false
                    self.message = "Microphone access is off. Enable it in Settings to practise speaking."
                    return
                }
                self.engine.startRecording(to: self.takeURL,
                    started: { [weak self] success in
                        guard let self, self.takeGeneration == expected else { return }
                        self.isStarting = false
                        self.isRecording = success
                        self.message = success ? nil :
                            "Recording could not start. Check microphone access and try again."
                    },
                    stoppedAutomatically: { [weak self] success in
                        guard let self, self.takeGeneration == expected else { return }
                        self.recordingFinished(success)
                    })
            }
        }
    }

    func stopRecording() {
        guard isRecording else { return }
        isRecording = false
        let expected = takeGeneration
        engine.stopRecording(file: takeURL) { [weak self] success in
            guard let self, self.takeGeneration == expected else { return }
            self.recordingFinished(success)
        }
    }

    private func recordingFinished(_ success: Bool) {
        isStarting = false
        isRecording = false
        hasRecording = success
        if success {
            inspectRecording()
        } else {
            message = "No usable recording was captured. Please try again."
        }
    }

    private func inspectRecording() {
        qualityTask?.cancel()
        usableRecording = false
        let expectedGeneration = takeGeneration
        let file = takeURL
        qualityTask = Task { @MainActor [weak self] in
            let failure = await Task.detached(priority: .userInitiated) { () -> String? in
                do {
                    _ = try PronunciationWave.make(fromRecording: file)
                    return nil
                } catch {
                    return (error as? LocalizedError)?.errorDescription
                        ?? PronunciationAudioError.unavailable.errorDescription
                }
            }.value
            guard let self, !Task.isCancelled,
                  self.takeGeneration == expectedGeneration else { return }
            self.usableRecording = failure == nil
            self.message = failure
            self.qualityTask = nil
        }
    }

    func discard() {
        playbackGeneration = UUID()
        takeGeneration = UUID()
        qualityTask?.cancel()
        qualityTask = nil
        isRecording = false
        isStarting = false
        hasRecording = false
        usableRecording = false
        message = nil
        engine.discard(file: takeURL)
    }
}
