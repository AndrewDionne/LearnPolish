import AVFoundation
import Foundation

/// Every AVAudioSession, player and recorder operation runs on one dedicated
/// serial queue. No caller on SwiftUI's MainActor waits for audio hardware.
/// The queue is process-wide because AVAudioSession is a process-wide singleton.
enum NativeAudioSessionMode {
    case playback
    case recording
}

enum NativeAudioSessionSetup {
    // Access only from NativeAudioEngine's serial queue.
    private static var selectedMode: NativeAudioSessionMode?

    static func prepare(_ mode: NativeAudioSessionMode) throws {
        let session = AVAudioSession.sharedInstance()
        if selectedMode != mode {
            switch mode {
            case .playback:
                // Reference words should play from the normal output route;
                // do not engage the microphone until the learner asks.
                try session.setCategory(.playback, mode: .default)
            case .recording:
                try session.setCategory(.playAndRecord, mode: .default,
                                        options: [.defaultToSpeaker, .allowBluetooth])
            }
            selectedMode = mode
        }
        // The OS may deactivate after an interruption, so reacquire on demand.
        // setActive and prepareToPlay can BOTH block; neither is on MainActor.
        try session.setActive(true)
    }
}

/// Queue-owned AVFoundation objects; never access player/recorder from UI.
/// Callbacks are delivered on main, with the caller responsible for checking
/// its take/playback generation before showing any result.
final class NativeAudioEngine {
    private static let queue = DispatchQueue(label: "com.pathtopolish.audio.hardware",
                                              qos: .userInitiated)

    private let sessionSetup: (NativeAudioSessionMode) throws -> Void
    private var player: AVAudioPlayer?
    private var recorder: AVAudioRecorder?
    private var recordingSerial: UInt64 = 0
    private var automaticFinish: ((Bool) -> Void)?

    init(sessionSetup: @escaping (NativeAudioSessionMode) throws -> Void =
            NativeAudioSessionSetup.prepare) {
        self.sessionSetup = sessionSetup
    }

    func play(_ file: URL, rate: Float, finishedPreparing: @escaping (Bool) -> Void) {
        Self.queue.async {
            self.player?.stop()
            self.player = nil
            guard self.recorder == nil else {
                DispatchQueue.main.async { finishedPreparing(false) }
                return
            }
            let success: Bool
            do {
                try self.sessionSetup(.playback)
                let candidate = try AVAudioPlayer(contentsOf: file)
                candidate.enableRate = true
                candidate.rate = min(1, max(0.75, rate))
                guard candidate.prepareToPlay(), candidate.play() else {
                    throw NSError(domain: "NativeAudio", code: 1)
                }
                self.player = candidate
                success = true
            } catch {
                success = false
            }
            DispatchQueue.main.async { finishedPreparing(success) }
        }
    }

    func stopPlayback() {
        Self.queue.async {
            self.player?.stop()
            self.player = nil
        }
    }

    func startRecording(to file: URL, started: @escaping (Bool) -> Void,
                        stoppedAutomatically: @escaping (Bool) -> Void) {
        Self.queue.async {
            self.player?.stop()
            self.player = nil
            self.recorder?.stop()
            self.recorder = nil
            self.automaticFinish = nil
            self.recordingSerial &+= 1
            let serial = self.recordingSerial
            let settings: [String: Any] = [
                AVFormatIDKey: Int(kAudioFormatMPEG4AAC),
                AVSampleRateKey: 44_100,
                AVNumberOfChannelsKey: 1,
                AVEncoderAudioQualityKey: AVAudioQuality.high.rawValue
            ]
            do {
                try self.sessionSetup(.recording)
                // A new take must never include a prior microphone recording.
                if FileManager.default.fileExists(atPath: file.path) {
                    try FileManager.default.removeItem(at: file)
                }
                let candidate = try AVAudioRecorder(url: file, settings: settings)
                guard candidate.prepareToRecord(), candidate.record() else {
                    throw NSError(domain: "NativeAudio", code: 2)
                }
                self.recorder = candidate
                self.automaticFinish = stoppedAutomatically
                DispatchQueue.main.async { started(true) }

                // The 10-second cap is enforced on the audio queue without
                // relying on an AVAudioRecorder delegate's run loop.
                Self.queue.asyncAfter(deadline: .now() + 10) {
                    guard self.recordingSerial == serial, let current = self.recorder else {
                        return
                    }
                    current.stop()
                    self.recorder = nil
                    self.recordingSerial &+= 1
                    let finish = self.automaticFinish
                    self.automaticFinish = nil
                    let exists = FileManager.default.fileExists(atPath: file.path)
                    if let finish {
                        DispatchQueue.main.async { finish(exists) }
                    }
                }
            } catch {
                self.recorder?.stop()
                self.recorder = nil
                self.automaticFinish = nil
                DispatchQueue.main.async { started(false) }
            }
        }
    }

    func stopRecording(file: URL, finished: @escaping (Bool) -> Void) {
        Self.queue.async {
            let hadRecorder = self.recorder != nil
            self.recorder?.stop()
            self.recorder = nil
            self.automaticFinish = nil
            self.recordingSerial &+= 1
            let exists = hadRecorder && FileManager.default.fileExists(atPath: file.path)
            DispatchQueue.main.async { finished(exists) }
        }
    }

    /// Invalidate pending auto-stop and tear down both devices in-order.
    /// No setActive(false) on a UI navigation path; the system may retain the
    /// session until the next explicit play/record request.
    func discard(file: URL) {
        Self.queue.async {
            self.recordingSerial &+= 1
            self.automaticFinish = nil
            self.recorder?.stop()
            self.recorder = nil
            self.player?.stop()
            self.player = nil
            try? FileManager.default.removeItem(at: file)
        }
    }
}
