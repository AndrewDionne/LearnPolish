#!/usr/bin/env swift
import AVFoundation
import Foundation

// Read-only diagnostic on GENERATED copies of original V2 MP3 files.
// Does not change, normalize, export, or replace any source recording.
guard CommandLine.arguments.count == 2 else {
    fputs("Usage: swift audit-reference-channels.swift DIR_OF_MP3S\n", stderr)
    exit(2)
}

let root = URL(fileURLWithPath: CommandLine.arguments[1], isDirectory: true)
let fm = FileManager.default
guard let all = fm.enumerator(at: root, includingPropertiesForKeys: [.isRegularFileKey]) else {
    fatalError("No generated audio directory; prepare native assets first")
}
var files: [URL] = []
for case let candidate as URL in all {
    if candidate.pathExtension.lowercased() == "mp3" {
        files.append(candidate)
    }
}
files.sort { $0.path < $1.path }
guard files.count >= 400 else { fatalError("Unexpectedly small original audio corpus: \(files.count)") }

// A bounded representative sample: first 4 clips per original source folder,
// plus the known first guided "Tak"/"Nie" and opening greeting, if present.
var perFolder: [String: Int] = [:]
var samples: [URL] = []
for file in files {
    let folder = file.deletingLastPathComponent().lastPathComponent
    let count = perFolder[folder, default: 0]
    guard count < 4 else { continue }
    perFolder[folder] = count + 1
    samples.append(file)
}
for extra in ["Conversation_1/0.mp3", "Conversation_1/14.mp3",
              "Conversation_1/15.mp3", "numbers_1-20/0.mp3"] {
    let file = root.appendingPathComponent(extra)
    if fm.fileExists(atPath: file.path) && !samples.contains(file) {
        samples.append(file)
    }
}

struct Signal {
    let path: String
    let channels: Int
    let leftRMS: Double
    let rightRMS: Double
    var rightToLeftDB: Double {
        20 * log10((rightRMS + 1e-8) / (leftRMS + 1e-8))
    }
}

var results: [Signal] = []
var failures: [String] = []
for url in samples {
    let relative = String(url.path.dropFirst(root.path.count + 1))
    do {
        let file = try AVAudioFile(forReading: url)
        let format = file.processingFormat
        let channels = Int(format.channelCount)
        guard channels >= 1, format.commonFormat == .pcmFormatFloat32,
              !format.isInterleaved else {
            throw NSError(domain: "SourceChannelAudit", code: 1,
                          userInfo: [NSLocalizedDescriptionKey:
                                     "Unsupported decoded PCM layout"])
        }
        let count = AVAudioFrameCount(max(1, min(file.length,
                                                 Int64(format.sampleRate * 3))))
        guard let buffer = AVAudioPCMBuffer(pcmFormat: format, frameCapacity: count) else {
            throw NSError(domain: "SourceChannelAudit", code: 2)
        }
        try file.read(into: buffer, frameCount: count)
        guard buffer.frameLength > 0, let channelData = buffer.floatChannelData else {
            throw NSError(domain: "SourceChannelAudit", code: 3)
        }
        let length = Int(buffer.frameLength)
        func rms(_ channel: Int) -> Double {
            let values = channelData[channel]
            var sum = 0.0
            for i in 0..<length {
                let v = Double(values[i])
                sum += v * v
            }
            return sqrt(sum / Double(length))
        }
        results.append(Signal(path: relative, channels: channels,
                              leftRMS: rms(0), rightRMS: rms(channels > 1 ? 1 : 0)))
    } catch {
        failures.append("\(relative): \(error.localizedDescription)")
    }
}

let mono = results.filter { $0.channels == 1 }
let stereo = results.filter { $0.channels >= 2 }
let rightHeavy = stereo.filter { $0.rightToLeftDB > 12 && $0.rightRMS > 0.001 }
let leftHeavy = stereo.filter { $0.rightToLeftDB < -12 && $0.leftRMS > 0.001 }
print("Source reference MP3 channel audit — original media unchanged")
print("Available: \(files.count); sampled: \(samples.count); decoded: \(results.count); errors: \(failures.count)")
print("Mono: \(mono.count); stereo/multi-channel: \(stereo.count)")
print("Strong right-only bias (+12 dB): \(rightHeavy.count); strong left-only bias (-12 dB): \(leftHeavy.count)")
for signal in results.sorted(by: {
    abs($0.rightToLeftDB) > abs($1.rightToLeftDB)
}).prefix(14) {
    let imbalance = String(format: "%+.1f", signal.rightToLeftDB)
    print("  \(signal.path) | channels \(signal.channels) | R/L \(imbalance) dB | L \(String(format: "%.5f", signal.leftRMS)) R \(String(format: "%.5f", signal.rightRMS))")
}
for failure in failures.prefix(10) {
    print("  Unable to decode: \(failure)")
}
if results.isEmpty {
    fatalError("Audio audit could not inspect any original reference")
}
