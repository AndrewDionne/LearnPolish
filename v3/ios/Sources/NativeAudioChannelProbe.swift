#if DEBUG
import AVFoundation
import SwiftUI

/// Developer-only pure PCM tone. A known signal in the left, right or both
/// channels goes through the SAME NativeAudioEngine as actual Polish MP3s.
/// Never substituted for a lesson source; no network or microphone involved.
enum NativeAudioProbeChannel: String, CaseIterable, Identifiable {
    case left = "Left only"
    case right = "Right only"
    case both = "Both"

    var id: String { rawValue }
}

enum NativeAudioProbeTone {
    static func wav(_ channel: NativeAudioProbeChannel,
                    rate: UInt32 = 44_100, seconds: Double = 0.8) -> Data {
        let frames = Int(Double(rate) * seconds)
        let payloadBytes = UInt32(frames * 4)
        var data = Data(capacity: 44 + Int(payloadBytes))
        func ascii(_ value: String) {
            data.append(contentsOf: value.utf8)
        }
        func word(_ value: UInt16) {
            data.append(UInt8(truncatingIfNeeded: value))
            data.append(UInt8(truncatingIfNeeded: value >> 8))
        }
        func dword(_ value: UInt32) {
            word(UInt16(truncatingIfNeeded: value))
            word(UInt16(truncatingIfNeeded: value >> 16))
        }
        ascii("RIFF")
        dword(36 + payloadBytes)
        ascii("WAVEfmt ")
        dword(16)
        word(1) // PCM, no compression
        word(2) // Explicit independent left and right channels
        dword(rate)
        dword(rate * 4)
        word(4)
        word(16)
        ascii("data")
        dword(payloadBytes)
        for index in 0..<frames {
            let phase = Double(index) * (2 * Double.pi * 523.25 / Double(rate))
            let ramp = min(1.0, min(Double(index), Double(frames - 1 - index)) / 180.0)
            let value = Int16((sin(phase) * ramp * 0.32 * Double(Int16.max)).rounded())
            word(UInt16(bitPattern: channel == .right ? 0 : value))
            word(UInt16(bitPattern: channel == .left ? 0 : value))
        }
        return data
    }
}

@MainActor final class NativeAudioChannelProbeModel: ObservableObject {
    @Published var route = "Select a tone to inspect the iPhone's active output."
    @Published var failure: String?
    private let engine = NativeAudioEngine()
    private let url = FileManager.default.temporaryDirectory
        .appendingPathComponent("ptp-audio-probe-\(UUID().uuidString).wav")

    func play(_ channel: NativeAudioProbeChannel) {
        do {
            try NativeAudioProbeTone.wav(channel).write(to: url, options: .atomic)
            failure = nil
            engine.play(url, rate: 1) { [weak self] success in
                guard let self else { return }
                let session = AVAudioSession.sharedInstance()
                let outputs = session.currentRoute.outputs
                    .map { $0.portType.rawValue }.joined(separator: ", ")
                self.route = "Output: \(outputs.isEmpty ? "none" : outputs)\n"
                    + "Hardware channels: \(session.outputNumberOfChannels)\n"
                    + "Session: \(session.category.rawValue)"
                self.failure = success ? nil : "The diagnostic tone could not play."
            }
        } catch {
            failure = "Unable to prepare the offline diagnostic tone."
        }
    }

    func stop() {
        engine.stopPlayback()
    }

    deinit {
        engine.discard(file: url)
    }
}

struct NativeAudioChannelProbeScreen: View {
    @StateObject private var probe = NativeAudioChannelProbeModel()

    var body: some View {
        VStack(alignment: .leading, spacing: 18) {
            Text("Audio channel test")
                .font(.title2.bold())
            Text("For this check, turn off iPhone Mono Audio in Accessibility. Use the same earphones that play other apps normally.")
                .foregroundStyle(.secondary)
            Text("Each short tone uses our normal lesson playback engine, but with a known left, right or identical two-channel signal.")
                .font(.footnote)
                .foregroundStyle(.secondary)
            ForEach(NativeAudioProbeChannel.allCases) { channel in
                Button {
                    probe.play(channel)
                } label: {
                    Label("Play \(channel.rawValue)", systemImage: "headphones")
                        .frame(maxWidth: .infinity, alignment: .leading)
                }
                .buttonStyle(.bordered)
            }
            Button("Stop") { probe.stop() }
                .buttonStyle(.bordered)
            Text(probe.route)
                .font(.footnote.monospaced())
                .textSelection(.enabled)
            if let failure = probe.failure {
                Text(failure).font(.footnote).foregroundStyle(.red)
            }
            Text("Expected: Left plays left, Right plays right, Both plays equally in both ears. No speech recordings or personal data are transmitted.")
                .font(.footnote)
                .foregroundStyle(.secondary)
            Spacer()
        }
        .padding()
        .navigationTitle("Audio check")
        .onDisappear { probe.stop() }
    }
}
#endif
