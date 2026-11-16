import SwiftUI

/// Optional interleaved retrieval of previously introduced original Polish.
/// No new curriculum source or second progress record is created.
struct NativeJourneyReinforcementScreen: View {
    let cards: [NativeJourneyReinforcementCard]

    @EnvironmentObject private var learner: LocalLearningStore
    @Environment(\.dismiss) private var dismiss
    @StateObject private var audio = NativeAudio()
    @State private var index = 0
    @State private var selectedOption: String?
    @State private var speed: Float = 1
    @State private var answered = 0
    @State private var correct = 0

    private var current: NativeJourneyReinforcementCard? {
        cards.indices.contains(index) ? cards[index] : nil
    }

    var body: some View {
        VStack(spacing: 16) {
            if let card = current {
                HStack {
                    Label("Reinforce earlier learning", systemImage: "arrow.triangle.2.circlepath")
                        .font(.subheadline.weight(.semibold))
                    Spacer()
                    Text("\(index + 1) / \(cards.count)")
                        .font(.caption.monospacedDigit())
                        .foregroundStyle(.secondary)
                }
                ProgressView(value: Double(index + 1),
                             total: Double(max(cards.count, 1)))
                ScrollView {
                    VStack(alignment: .leading, spacing: 18) {
                        Text("Recall a word from an earlier chapter.")
                            .foregroundStyle(.secondary)
                        Text(card.item.polish)
                            .font(.largeTitle.weight(.semibold))
                            .textSelection(.enabled)
                        HStack {
                            Button {
                                audio.playReference(card.item, rate: speed)
                            } label: {
                                Label("Hear Polish", systemImage: "play.circle.fill")
                            }
                            .buttonStyle(.bordered)
                            Picker("Speed", selection: $speed) {
                                Text("0.75×").tag(Float(0.75))
                                Text("1×").tag(Float(1))
                            }
                            .pickerStyle(.segmented)
                            .frame(maxWidth: 140)
                        }
                        Text("Choose the English meaning").font(.headline)
                        ForEach(card.options, id: \.self) { option in
                            Button {
                                answer(option, for: card)
                            } label: {
                                HStack {
                                    Text(option).multilineTextAlignment(.leading)
                                    Spacer()
                                    if selectedOption == option {
                                        Image(systemName: option == card.item.english
                                              ? "checkmark.circle.fill" : "xmark.circle.fill")
                                    }
                                }
                                .frame(maxWidth: .infinity, alignment: .leading)
                            }
                            .buttonStyle(.bordered)
                            .disabled(selectedOption != nil)
                        }
                        if let selectedOption {
                            Label(selectedOption == card.item.english
                                  ? "Correct" : "Needs practice",
                                  systemImage: selectedOption == card.item.english
                                  ? "checkmark.circle" : "arrow.clockwise")
                            Text("Meaning: \(card.item.english)")
                                .foregroundStyle(.secondary)
                        }
                        if let message = audio.message {
                            Text(message).font(.footnote).foregroundStyle(.secondary)
                        }
                        if let error = learner.saveError {
                            Text(error).font(.footnote).foregroundStyle(.red)
                        }
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(.vertical, 20)
                }
                HStack {
                    Text("Original source · optional practice")
                        .font(.footnote).foregroundStyle(.secondary)
                    Spacer()
                    Button(selectedOption == nil ? "Skip" :
                           index + 1 == cards.count ? "Finish" : "Next") {
                        advance()
                    }
                    .buttonStyle(.borderedProminent)
                }
            } else {
                Spacer()
                ContentUnavailableView(
                    "Reinforcement finished",
                    systemImage: "checkmark.circle",
                    description: Text("\(answered) answers saved · \(correct) correct. Skipped words received no credit."))
                Text("Your answers also enter the existing source-word review schedule.")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
                Button("Done") { dismiss() }
                    .buttonStyle(.borderedProminent)
                Spacer()
            }
        }
        .padding(.horizontal)
        .navigationTitle("Reinforcement")
        .navigationBarTitleDisplayMode(.inline)
        .onDisappear { audio.discard() }
    }

    private func answer(_ option: String, for card: NativeJourneyReinforcementCard) {
        guard selectedOption == nil, card.options.contains(option) else { return }
        NativePracticeSubmission.commit(
            store: learner, item: card.item, mode: .learn,
            understood: option == card.item.english,
            evidence: .matching) {
                selectedOption = option
                answered += 1
                if option == card.item.english { correct += 1 }
            }
    }

    private func advance() {
        audio.discard()
        selectedOption = nil
        index += 1
    }
}
