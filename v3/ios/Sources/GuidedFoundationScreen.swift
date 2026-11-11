import SwiftUI

/// Actual V2 C-13 recorded teaching path, not a new set of generated Polish.
/// Each activity writes progress against the ORIGINAL source item ID.
struct GuidedFoundationsScreen: View {
    @EnvironmentObject private var learner: LocalLearningStore
    @EnvironmentObject private var navigation: LearningNavigation

    private let stages = [
        "First words",
        "Basic vocabulary",
        "First sentences / basic grammar"
    ]

    var body: some View {
        List {
            ForEach(stages, id: \.self) { stage in
                Section(stage) {
                    ForEach(learner.guidedFoundations.filter { $0.stage == stage }) { step in
                        Button {
                            navigation.openPractice(.guided(step.id))
                        } label: {
                            HStack(spacing: 12) {
                                Image(systemName: step.isGrammar ? "textformat.abc" : "character.book.closed")
                                    .frame(width: 26)
                                    .foregroundStyle(.indigo)
                                VStack(alignment: .leading, spacing: 3) {
                                    Text(step.title).font(.body.weight(.medium))
                                    Text("\(learner.guidedPractisedCount(step)) of \(step.items.count) practised")
                                        .font(.caption)
                                        .foregroundStyle(.secondary)
                                }
                            }
                            .padding(.vertical, 4)
                        }
                    }
                }
            }
        }
        .navigationTitle("Guided learning")
    }
}

/// A learner hears and understands the real full source before trying recall.
/// A reveal, audio play or skip never issues XP or records a completed attempt.
struct GuidedPracticeScreen: View {
    let step: GuidedFoundationStep

    @EnvironmentObject private var learner: LocalLearningStore
    @StateObject private var audio = NativeAudio()
    @State private var itemIndex = 0
    @State private var tryingRecall = false
    @State private var revealed = false
    @State private var finished = false
    @State private var speed: Float = 1

    private var current: GuidedRecordedItem { step.items[itemIndex] }

    private var earlierPractice: [GuidedFoundationStep] {
        GuidedFoundationPath.prerequisitesToReview(
            for: step, in: learner.guidedFoundations,
            records: learner.profile.records)
    }

    private var following: GuidedFoundationStep? {
        guard let position = learner.guidedFoundations.firstIndex(where: { $0.id == step.id }),
              learner.guidedFoundations.indices.contains(position + 1) else { return nil }
        return learner.guidedFoundations[position + 1]
    }

    var body: some View {
        VStack(spacing: 14) {
            if finished {
                Spacer()
                ContentUnavailableView("End of activity", systemImage: "checkmark.circle",
                                       description: Text("\(learner.guidedPractisedCount(step)) of \(step.items.count) phrases practised. Unpractised phrases remain available."))
                if let following {
                    NavigationLink {
                        GuidedPracticeScreen(step: following)
                    } label: {
                        Label("Next: \(following.title)", systemImage: "arrow.right")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.borderedProminent)
                }
                if let missed = learner.firstUnpractisedGuidedIndex(step) {
                    Button("Revisit unpractised") {
                        itemIndex = missed
                        finished = false
                        resetPresentation()
                        rememberPosition()
                    }
                    .buttonStyle(.bordered)
                }
                Button("Practice again") {
                    itemIndex = 0
                    finished = false
                    resetPresentation()
                    rememberPosition()
                }
                .buttonStyle(.bordered)
                if let error = learner.saveError {
                    Label(error, systemImage: "exclamationmark.triangle")
                        .font(.footnote)
                        .foregroundStyle(.red)
                }
                Spacer()
            } else {
                HStack {
                    Text(step.stage)
                        .foregroundStyle(.secondary)
                    Spacer()
                    Text("\(itemIndex + 1) / \(step.items.count)")
                        .monospacedDigit()
                        .foregroundStyle(.secondary)
                }
                .font(.footnote)
                ProgressView(value: Double(itemIndex + 1), total: Double(step.items.count))

                ScrollView {
                    VStack(alignment: .leading, spacing: 20) {
                        if !earlierPractice.isEmpty {
                            DisclosureGroup("Earlier learning to revisit (\(earlierPractice.count))") {
                                ForEach(earlierPractice) { earlier in
                                    NavigationLink {
                                        GuidedPracticeScreen(step: earlier)
                                    } label: {
                                        Label(earlier.title, systemImage: "arrow.uturn.backward")
                                    }
                                    .padding(.vertical, 4)
                                }
                            }
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                        }
                        if step.isGrammar {
                            Text(step.cue ?? "")
                                .font(.headline)
                                .foregroundStyle(.indigo)
                            Text(step.explanation ?? "")
                                .font(.body)
                                .foregroundStyle(.secondary)
                        }

                        VStack(alignment: .leading, spacing: 14) {
                            focusedPolish(current)
                                .font(.largeTitle.weight(.semibold))
                                .textSelection(.enabled)
                            if !tryingRecall || revealed {
                                Text(current.english)
                                    .font(.title3)
                            }
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(18)
                        .background(.quaternary.opacity(0.35),
                                    in: RoundedRectangle(cornerRadius: 16))

                        HStack {
                            Button {
                                if let item = learner.sourceItem(for: current) {
                                    audio.playReference(item, rate: speed)
                                }
                            } label: {
                                Label("Hear Polish", systemImage: "play.circle.fill")
                            }
                            .buttonStyle(.bordered)
                            Picker("Speed", selection: $speed) {
                                Text("0.75×").tag(Float(0.75))
                                Text("1×").tag(Float(1))
                            }
                            .pickerStyle(.segmented)
                            .frame(maxWidth: 145)
                        }

                        if !tryingRecall {
                            Button("Practice this phrase") {
                                tryingRecall = true
                                revealed = false
                            }
                            .buttonStyle(.borderedProminent)
                        } else if !revealed {
                            Button("Show meaning") { revealed = true }
                                .buttonStyle(.borderedProminent)
                        } else {
                            HStack(spacing: 12) {
                                Button("Needs practice") { submit(false) }
                                    .buttonStyle(.bordered)
                                Button("Got it") { submit(true) }
                                    .buttonStyle(.borderedProminent)
                            }
                        }

                        if let message = audio.message {
                            Label(message, systemImage: "info.circle")
                                .font(.footnote)
                                .foregroundStyle(.secondary)
                        }
                        if let error = learner.saveError {
                            Label(error, systemImage: "exclamationmark.triangle")
                                .font(.footnote)
                                .foregroundStyle(.red)
                        }
                    }
                    .padding(.vertical, 20)
                    .frame(maxWidth: .infinity, alignment: .leading)
                }

                HStack {
                    Button {
                        itemIndex -= 1
                    } label: {
                        Label("Back", systemImage: "chevron.left")
                    }
                    .disabled(itemIndex == 0)
                    Spacer()
                    Button {
                        advance()
                    } label: {
                        Text("Skip")
                    }
                    .buttonStyle(.bordered)
                    .accessibilityHint("Move on without recording a response or earning XP")
                }
                .padding(.bottom, 8)
            }
        }
        .padding(.horizontal)
        .navigationTitle(step.title)
        .navigationBarTitleDisplayMode(.inline)
        .onAppear {
            if let savedID = learner.guidedResumeItemID(for: step.id),
               let index = step.items.firstIndex(where: { $0.id == savedID }) {
                itemIndex = index
            }
            rememberPosition()
        }
        .onChange(of: itemIndex) { _, _ in
            resetPresentation()
            rememberPosition()
        }
        .onDisappear { audio.discard() }
    }

    private func focusedPolish(_ item: GuidedRecordedItem) -> Text {
        guard let focus = item.focus, let range = item.polish.range(of: focus) else {
            return Text(item.polish)
        }
        return Text(String(item.polish[..<range.lowerBound]))
          + Text(focus).bold().foregroundColor(.indigo)
          + Text(String(item.polish[range.upperBound...]))
    }

    private func submit(_ remembered: Bool) {
        guard let original = learner.sourceItem(for: current) else { return }
        NativePracticeSubmission.commit(
            store: learner, item: original, mode: .learn, understood: remembered) {
                advance()
            }
    }

    private func advance() {
        if itemIndex + 1 < step.items.count {
            itemIndex += 1
        } else if learner.finishedGuidedStep(step.id) {
            audio.discard()
            finished = true
        }
    }

    private func resetPresentation() {
        audio.discard()
        tryingRecall = false
        revealed = false
    }

    private func rememberPosition() {
        guard !finished else { return }
        learner.rememberGuidedPosition(stepID: step.id, itemID: current.id)
    }
}
