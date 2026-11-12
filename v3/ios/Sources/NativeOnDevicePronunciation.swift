import Foundation
import SwiftUI
import WhisperKit

/// Device-local multilingual Polish transcription. The model may need a
/// one-time public weights download. Speech stays on the iPhone, and the
/// model is shared between all Speak exercises in this app process.
@MainActor final class NativeOnDevicePronunciation: ObservableObject {
    private var model: WhisperKit?
    private var loading: Task<WhisperKit, Error>?

    private func readyModel() async throws -> WhisperKit {
        if let model { return model }
        if loading == nil {
            // Never use an English-only model for original Polish speech.
            loading = Task {
                try await WhisperKit(WhisperKitConfig(model: "base", verbose: false))
            }
        }
        guard let loading else { throw NativeOnDeviceSpeechError.unavailable }
        do {
            let prepared = try await loading.value
            model = prepared
            self.loading = nil
            return prepared
        } catch {
            self.loading = nil
            throw NativeOnDeviceSpeechError.modelSetup
        }
    }

    func assess(item: LessonItem, recording: URL) async throws -> NativeSpeechFeedback {
        guard item.referenceReview != "practice_only", !item.polish.isEmpty,
              FileManager.default.fileExists(atPath: recording.path) else {
            throw NativeOnDeviceSpeechError.unavailable
        }
        let engine = try await readyModel()
        try Task.checkCancellation()
        let options = DecodingOptions(language: "pl", temperatureFallbackCount: 0,
                                      detectLanguage: false)
        let result = try await engine.transcribe(audioPath: recording.path,
                                                 decodeOptions: options)
        try Task.checkCancellation()
        return NativePronunciationTextAlignment.assess(
            reference: item.polish,
            recognized: result.map(\.text).joined(separator: " "),
            sourceSegments: item.pronunciationSegments?.segments
        )
    }
}

enum NativeOnDeviceSpeechError: LocalizedError {
    case modelSetup, unavailable

    var errorDescription: String? {
        switch self {
        case .modelSetup:
            return "The Polish speech model could not be prepared. Connect to Wi-Fi once to install the on-device model, then try again. Recording still works."
        case .unavailable:
            return "This recording cannot be reviewed. Record another take."
        }
    }
}

/// A transcript-match estimate, NOT calibrated acoustic phoneme or syllable
/// grading. Only the actual output of local Polish speech recognition is
/// compared with the original source text. No response => no numeric score.
enum NativePronunciationTextAlignment {
    private static let polishLocale = Locale(identifier: "pl_PL")

    static func comparable(_ value: String) -> [Character] {
        let normalized = value.precomposedStringWithCanonicalMapping
            .lowercased(with: polishLocale)
        return normalized.filter { $0.isLetter || $0.isNumber }.map { $0 }
    }

    static func assess(reference: String, recognized: String,
                       sourceSegments: [String]?) -> NativeSpeechFeedback {
        let segments: [String]
        if let sourceSegments, !sourceSegments.isEmpty,
           sourceSegments.joined() == reference, sourceSegments.count <= 32 {
            segments = sourceSegments
        } else {
            // Original words only when there are no authored boundaries:
            // never manufacture phoneme/syllable boundaries to show a score.
            segments = splitWordsPreservingWhitespace(reference)
        }
        let expected = comparable(reference), heard = comparable(recognized)
        guard !expected.isEmpty, !heard.isEmpty else {
            return .inconclusive("Speech was not recognized clearly. Try another recording.")
        }
        guard expected.count <= 400, heard.count <= 400 else {
            return .inconclusive("This recording could not be matched reliably. Try again.")
        }
        var owners: [Int] = []
        for (index, segment) in segments.enumerated() {
            owners.append(contentsOf: Array(repeating: index, count: comparable(segment).count))
        }
        guard owners.count == expected.count else {
            return .inconclusive("The original Polish text could not be aligned.")
        }

        let rows = expected.count + 1, columns = heard.count + 1
        var distance = Array(repeating: Array(repeating: 0, count: columns), count: rows)
        for i in 0..<rows { distance[i][0] = i }
        for j in 0..<columns { distance[0][j] = j }
        for i in 1..<rows {
            for j in 1..<columns {
                let cost = expected[i-1] == heard[j-1] ? 0 : 1
                distance[i][j] = min(distance[i-1][j-1] + cost,
                                     distance[i-1][j] + 1,
                                     distance[i][j-1] + 1)
            }
        }

        var correct = Array(repeating: 0, count: segments.count)
        var errors = Array(repeating: 0, count: segments.count)
        var i = expected.count, j = heard.count
        while i > 0 || j > 0 {
            if i > 0 && j > 0 {
                let cost = expected[i-1] == heard[j-1] ? 0 : 1
                if distance[i][j] == distance[i-1][j-1] + cost {
                    if cost == 0 { correct[owners[i-1]] += 1 }
                    else { errors[owners[i-1]] += 1 }
                    i -= 1
                    j -= 1
                    continue
                }
            }
            if i > 0 && distance[i][j] == distance[i-1][j] + 1 {
                errors[owners[i-1]] += 1
                i -= 1
            } else if j > 0 {
                let nearest = owners[min(max(i - 1, 0), owners.count - 1)]
                errors[nearest] += 1
                j -= 1
            }
        }

        let difference = distance[expected.count][heard.count]
        let score = Int((100.0 * max(0.0, 1.0 -
            Double(difference) / Double(max(expected.count, heard.count)))).rounded())
        let parts: [NativeColourPart] = segments.enumerated().map { index, text in
            let weight = correct[index] + errors[index]
            let hint: NativeColourPart.Hint
            if weight == 0 {
                hint = .uncertain
            } else {
                let fraction = Double(correct[index]) / Double(weight)
                hint = fraction >= 0.85 ? .close : fraction >= 0.5 ? .review : .focus
            }
            return NativeColourPart(polish: text, hint: hint)
        }
        return .onDeviceRecognition(score: score, parts: parts)
    }

    private static func splitWordsPreservingWhitespace(_ text: String) -> [String] {
        var parts: [String] = []
        var current = ""
        var previousWasSpace: Bool?
        for char in text {
            let isSpace = char.isWhitespace
            if let previousWasSpace, previousWasSpace != isSpace {
                parts.append(current)
                current = ""
            }
            current.append(char)
            previousWasSpace = isSpace
        }
        if !current.isEmpty { parts.append(current) }
        return parts
    }
}
