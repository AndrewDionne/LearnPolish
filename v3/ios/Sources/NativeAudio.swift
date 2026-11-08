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

@MainActor final class NativeAudio: NSObject, ObservableObject, AVAudioRecorderDelegate {
    @Published private(set) var isRecording = false
    @Published private(set) var hasRecording = false
    @Published var message: String?

    private var player: AVAudioPlayer?
    private var recorder: AVAudioRecorder?
    private let takeURL = FileManager.default.temporaryDirectory
        .appendingPathComponent("path-to-polish-private-take.m4a")

    override init() {
        super.init()
        // A previous interrupted session must not leave a take lying around.
        try? FileManager.default.removeItem(at: takeURL)
    }

    func playReference(_ item: LessonItem) {
        guard let path = item.audio, let file = AudioFiles.referenceURL(for: path) else {
            message = "This lesson has no reference recording."
            return
        }
        play(file, rate: 1)
    }

    func playReference(_ item: LessonItem, rate: Float) {
        guard let path = item.audio, let file = AudioFiles.referenceURL(for: path) else {
            message = "This lesson has no reference recording."
            return
        }
        play(file, rate: rate)
    }

    func playRecording() {
        guard hasRecording else { return }
        play(takeURL, rate: 1)
    }

    private func play(_ url: URL, rate: Float) {
        do {
            player?.stop()
            let session = AVAudioSession.sharedInstance()
            try session.setCategory(.playAndRecord, mode: .default,
                                    options: [.defaultToSpeaker, .allowBluetooth])
            try session.setActive(true)
            let playback = try AVAudioPlayer(contentsOf: url)
            playback.enableRate = true
            playback.rate = rate
            playback.prepareToPlay()
            if !playback.play() { throw NSError(domain: "Audio", code: 1) }
            player = playback
            message = nil
        } catch {
            message = "Audio could not play. Check output and audio permissions."
        }
    }

    func requestRecord() {
        player?.stop()
        AVAudioSession.sharedInstance().requestRecordPermission { [weak self] granted in
            DispatchQueue.main.async {
                guard let self else { return }
                if granted { self.startRecording() }
                else { self.message = "Microphone access is off. Enable it in Settings to practise speaking." }
            }
        }
    }

    private func startRecording() {
        do {
            discard()
            let session = AVAudioSession.sharedInstance()
            try session.setCategory(.playAndRecord, mode: .default,
                                    options: [.defaultToSpeaker, .allowBluetooth])
            try session.setActive(true)
            let settings: [String: Any] = [
                AVFormatIDKey: Int(kAudioFormatMPEG4AAC),
                AVSampleRateKey: 44_100,
                AVNumberOfChannelsKey: 1,
                AVEncoderAudioQualityKey: AVAudioQuality.high.rawValue
            ]
            let recording = try AVAudioRecorder(url: takeURL, settings: settings)
            recording.delegate = self
            recording.prepareToRecord()
            guard recording.record(forDuration: 10) else {
                throw NSError(domain: "Audio", code: 2)
            }
            recorder = recording
            isRecording = true
            message = nil
        } catch {
            isRecording = false
            message = "Recording could not start. Check microphone access and try again."
        }
    }

    func stopRecording() {
        guard isRecording else { return }
        recorder?.stop()
        isRecording = false
        hasRecording = FileManager.default.fileExists(atPath: takeURL.path)
        if !hasRecording { message = "No usable recording was captured. Please try again." }
    }

    nonisolated func audioRecorderDidFinishRecording(_ recorder: AVAudioRecorder,
                                                      successfully flag: Bool) {
        Task { @MainActor [weak self] in
            guard let self else { return }
            self.isRecording = false
            self.hasRecording = flag && FileManager.default.fileExists(atPath: self.takeURL.path)
            if !self.hasRecording { self.message = "Recording ended without a usable take." }
        }
    }

    func discard() {
        recorder?.stop()
        recorder = nil
        player?.stop()
        isRecording = false
        hasRecording = false
        try? FileManager.default.removeItem(at: takeURL)
    }
}
