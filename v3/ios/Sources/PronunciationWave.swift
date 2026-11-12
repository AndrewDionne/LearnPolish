import Foundation
import AVFoundation

enum PronunciationAudioError: LocalizedError {
    case unavailable, invalidLength, silence, clipping, invalidFormat

    var errorDescription: String? {
        switch self {
        case .unavailable: return "The recording could not be prepared. You can replay or record again."
        case .invalidLength: return "Record between 0.6 and 10 seconds to check pronunciation."
        case .silence: return "Very little sound was detected. Try again nearer the microphone."
        case .clipping: return "The recording is distorted. Try again farther from the microphone."
        case .invalidFormat: return "This recording could not be converted for pronunciation checking."
        }
    }
}

/// Exact V2 interchange: 16-kHz mono little-endian PCM16 in a 44-byte RIFF/WAVE.
/// All conversion and quality checks are local; audio is never uploaded here.
enum PronunciationWave {
    static let sampleRate = 16_000
    static let maxWAVBytes = 360_000

    static func make(fromRecording url: URL) throws -> Data {
        let source: AVAudioFile
        do {
            source = try AVAudioFile(forReading: url, commonFormat: .pcmFormatFloat32,
                                     interleaved: false)
        } catch {
            throw PronunciationAudioError.unavailable
        }
        let rate = source.processingFormat.sampleRate
        let frames = source.length
        guard rate.isFinite, rate > 0, rate <= 192_000,
              frames > 0, Double(frames) / rate <= 10.1,
              frames <= AVAudioFramePosition(UInt32.max),
              source.processingFormat.channelCount > 0,
              source.processingFormat.channelCount <= 8 else {
            throw PronunciationAudioError.invalidLength
        }
        let buffer = AVAudioPCMBuffer(pcmFormat: source.processingFormat,
                                      frameCapacity: AVAudioFrameCount(frames))
        guard let buffer else { throw PronunciationAudioError.invalidFormat }
        do { try source.read(into: buffer) }
        catch { throw PronunciationAudioError.unavailable }
        guard let channels = buffer.floatChannelData, buffer.frameLength > 0 else {
            throw PronunciationAudioError.invalidFormat
        }
        let inputCount = Int(buffer.frameLength)
        let count = Int((Double(inputCount) * Double(sampleRate) / rate).rounded())
        guard count >= 9_600, count <= 160_000 else {
            throw PronunciationAudioError.invalidLength
        }
        let channelCount = Int(source.processingFormat.channelCount)
        var samples = [Int16](repeating: 0, count: count)
        for i in 0..<count {
            let position = Double(i) * rate / Double(sampleRate)
            let left = min(Int(position), inputCount - 1)
            let right = min(left + 1, inputCount - 1)
            let fraction = Float(position - Double(left))
            var mixed: Float = 0
            for c in 0..<channelCount {
                mixed += channels[c][left] * (1 - fraction) + channels[c][right] * fraction
            }
            let value = min(Float(1), max(Float(-1), mixed / Float(channelCount)))
            let scaled = value < 0 ? (value * 32768).rounded() : (value * 32767).rounded()
            samples[i] = Int16(clamping: Int(scaled))
        }
        return try encode(samples: samples)
    }

    static func encode(samples: [Int16]) throws -> Data {
        let count = samples.count
        guard count >= 9_600 && count <= 160_000 else {
            throw PronunciationAudioError.invalidLength
        }
        var power = 0.0
        var clipped = 0
        for sample in samples {
            let value = Double(sample) / 32768.0
            power += value * value
            if abs(Int(sample)) >= 32_500 { clipped += 1 }
        }
        if sqrt(power / Double(count)) < 0.008 {
            throw PronunciationAudioError.silence
        }
        if Double(clipped) / Double(count) > 0.02 {
            throw PronunciationAudioError.clipping
        }
        var bytes = Data(capacity: 44 + count * 2)
        func text(_ label: String) { bytes.append(contentsOf: label.utf8) }
        func short(_ value: UInt16) {
            bytes.append(UInt8(truncatingIfNeeded: value))
            bytes.append(UInt8(truncatingIfNeeded: value >> 8))
        }
        func word(_ value: UInt32) {
            for shift in [0, 8, 16, 24] {
                bytes.append(UInt8(truncatingIfNeeded: value >> shift))
            }
        }
        text("RIFF")
        word(UInt32(36 + count * 2))
        text("WAVE")
        text("fmt ")
        word(16)       // linear PCM header size
        short(1)       // PCM (not MP3/AAC or float)
        short(1)       // mono
        word(UInt32(sampleRate))
        word(UInt32(sampleRate * 2))
        short(2)
        short(16)
        text("data")
        word(UInt32(count * 2))
        for sample in samples {
            short(UInt16(bitPattern: sample))
        }
        guard bytes.count <= maxWAVBytes else {
            throw PronunciationAudioError.invalidLength
        }
        return bytes
    }

    static func verify(_ wav: Data) throws {
        guard wav.count >= 44, wav.count <= maxWAVBytes,
              String(decoding: wav[0..<4], as: UTF8.self) == "RIFF",
              String(decoding: wav[8..<12], as: UTF8.self) == "WAVE",
              String(decoding: wav[12..<16], as: UTF8.self) == "fmt ",
              String(decoding: wav[36..<40], as: UTF8.self) == "data" else {
            throw PronunciationAudioError.invalidFormat
        }
        func short(_ offset: Int) -> UInt16 {
            UInt16(wav[offset]) | (UInt16(wav[offset+1]) << 8)
        }
        func word(_ offset: Int) -> UInt32 {
            UInt32(wav[offset]) | (UInt32(wav[offset+1]) << 8) |
            (UInt32(wav[offset+2]) << 16) | (UInt32(wav[offset+3]) << 24)
        }
        let count = wav.count - 44
        guard word(4) == UInt32(wav.count - 8), word(16) == 16,
              short(20) == 1, short(22) == 1, word(24) == UInt32(sampleRate),
              word(28) == 32_000, short(32) == 2, short(34) == 16,
              word(40) == UInt32(count), count % 2 == 0 else {
            throw PronunciationAudioError.invalidFormat
        }
        var samples = [Int16]()
        samples.reserveCapacity(count / 2)
        for position in stride(from: 44, to: wav.count, by: 2) {
            let bits = UInt16(wav[position]) | (UInt16(wav[position+1]) << 8)
            samples.append(Int16(bitPattern: bits))
        }
        _ = try encode(samples: samples)
    }
}
