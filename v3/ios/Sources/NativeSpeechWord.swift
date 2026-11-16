import SwiftUI

/// Shows genuine source-bound feedback. An on-device /100 number estimates
/// speech-to-text agreement, never calibrated acoustic syllable performance.
struct NativePronunciationPresentation {
    let score: Int
    let segments: [NativeColourPart]
    let onDevice: Bool

    init?(polish: String, feedback: NativeSpeechFeedback?) {
        let score: Int
        let segments: [NativeColourPart]
        let local: Bool
        guard let feedback else { return nil }
        switch feedback {
        case .blend(let value, let parts):
            score = value; segments = parts; local = false
        case .onDeviceRecognition(let value, let parts):
            score = value; segments = parts; local = true
        default:
            return nil
        }
        guard (0...100).contains(score), !segments.isEmpty,
              segments.map(\.polish).joined() == polish else { return nil }
        self.score = score
        self.segments = segments
        self.onDevice = local
    }
}

struct NativeSpeechWord: View {
    let polish: String
    let feedback: NativeSpeechFeedback?

    private var result: NativePronunciationPresentation? {
        NativePronunciationPresentation(polish: polish, feedback: feedback)
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 7) {
            formatted
                .accessibilityLabel(polish)
                .textSelection(.enabled)
            if let result {
                Text("\(result.score)/100")
                    .font(.title3.monospacedDigit().weight(.semibold))
                    .foregroundStyle(.primary)
                    .accessibilityLabel(result.onDevice
                        ? "On-device Polish speech recognition match \(result.score) out of 100"
                        : "Experimental overall pronunciation estimate \(result.score) out of 100")
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private var formatted: Text {
        guard let result else { return Text(polish) }
        var word = Text("")
        for (index, segment) in result.segments.enumerated() {
            let tint: Color
            switch segment.hint {
            case .close: tint = .green
            case .review: tint = .orange
            case .focus: tint = .red
            case .uncertain: tint = .secondary
            }
            if index > 0 { word = word + Text("\u{2009}") }
            word = word + Text(segment.polish).foregroundColor(tint)
        }
        return word
    }
}
