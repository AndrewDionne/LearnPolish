import SwiftUI

/// Replaces the single existing Polish prompt when the optional exact-source
/// blend response exists. No second word, coloured boxes, syllable numbers,
/// diagnostic legend or fictitious syllable percentages.
struct NativeSpeechWord: View {
    let polish: String
    let feedback: NativeSpeechFeedback?

    var body: some View {
        formatted
            .accessibilityLabel(polish)
            .textSelection(.enabled)
    }

    private var formatted: Text {
        guard case .blend(_, let parts) = feedback,
              parts.map(\.polish).joined() == polish else {
            return Text(polish)
        }
        var word = Text("")
        for (index, part) in parts.enumerated() {
            let tint: Color
            switch part.hint {
            case .close: tint = .green
            case .review: tint = .orange
            case .focus: tint = .red
            case .uncertain: tint = .secondary
            }
            if index > 0 { word = word + Text("\u{2009}") }
            word = word + Text(part.polish).foregroundColor(tint)
        }
        return word
    }
}
